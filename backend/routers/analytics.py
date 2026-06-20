import os
import json
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from database import get_db
from db_models import Incident

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOTSPOTS_PATH = os.path.join(BASE_DIR, "data", "hotspots.json")
RISK_TABLE_PATH = os.path.join(BASE_DIR, "data", "risk_table.json")


# ── GET /analytics/summary ────────────────────────────────────────────────────
@router.get("/summary", summary="Get incidents summary statistics")
def get_summary(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    start_of_month = datetime(now.year, now.month, 1)

    # 1. Total incidents in current month
    total_incidents_month = db.query(func.count(Incident.id)).filter(
        Incident.reported_at >= start_of_month
    ).scalar() or 0

    # 2. Average predicted duration
    avg_dur = db.query(func.avg(Incident.predicted_duration_mins)).scalar() or 0.0

    # 3. Most affected junction
    junction_res = db.query(
        Incident.junction,
        func.count(Incident.id).label("cnt")
    ).group_by(
        Incident.junction
    ).order_by(
        desc("cnt")
    ).first()
    most_affected_junction = junction_res[0] if junction_res else ""

    # 4. Peak hour (0-23)
    hour_res = db.query(
        Incident.hour_of_day,
        func.count(Incident.id).label("cnt")
    ).group_by(
        Incident.hour_of_day
    ).order_by(
        desc("cnt")
    ).first()
    peak_hour = hour_res[0] if hour_res else 0

    # 5. Total resolved
    total_resolved = db.query(func.count(Incident.id)).filter(
        Incident.status == "resolved"
    ).scalar() or 0

    # 6. Total active
    total_active = db.query(func.count(Incident.id)).filter(
        Incident.status == "active"
    ).scalar() or 0

    # 7. Average severity multiplier
    avg_severity = db.query(func.avg(Incident.severity_multiplier)).scalar() or 0.0

    # 8. Total officers deployed (sum of officers_needed for active incidents)
    total_officers = db.query(func.sum(Incident.officers_needed)).filter(
        Incident.status == "active"
    ).scalar() or 0

    return {
        "total_incidents_month": int(total_incidents_month),
        "avg_predicted_duration": float(avg_dur),
        "most_affected_junction": str(most_affected_junction),
        "peak_hour": int(peak_hour),
        "total_resolved": int(total_resolved),
        "total_active": int(total_active),
        "avg_severity_multiplier": float(avg_severity),
        "total_officers_deployed": int(total_officers)
    }


# ── GET /analytics/by_cause ───────────────────────────────────────────────────
@router.get("/by_cause", summary="Get incident counts and averages grouped by cause")
def get_by_cause(db: Session = Depends(get_db)):
    results = db.query(
        Incident.event_cause,
        func.count(Incident.id).label("cnt"),
        func.avg(Incident.predicted_duration_mins).label("avg_dur"),
        func.avg(Incident.jam_length_km).label("avg_jam"),
        func.avg(Incident.officers_needed).label("avg_off")
    ).group_by(
        Incident.event_cause
    ).order_by(
        desc("cnt")
    ).all()

    out = []
    for cause, cnt, avg_dur, avg_jam, avg_off in results:
        out.append({
            "cause": str(cause),
            "count": int(cnt),
            "avg_duration_mins": float(avg_dur) if avg_dur is not None else 0.0,
            "avg_jam_length_km": float(avg_jam) if avg_jam is not None else 0.0,
            "avg_officers_needed": float(avg_off) if avg_off is not None else 0.0
        })
    return out


# ── GET /analytics/by_hour ────────────────────────────────────────────────────
@router.get("/by_hour", summary="Get incident counts and average durations grouped by hour")
def get_by_hour(db: Session = Depends(get_db)):
    hours_data = {h: {"hour": h, "count": 0, "avg_duration_mins": 0.0} for h in range(24)}

    results = db.query(
        Incident.hour_of_day,
        func.count(Incident.id).label("cnt"),
        func.avg(Incident.predicted_duration_mins).label("avg_dur")
    ).group_by(
        Incident.hour_of_day
    ).all()

    for hr, cnt, avg_dur in results:
        if 0 <= hr < 24:
            hours_data[hr] = {
                "hour": hr,
                "count": int(cnt),
                "avg_duration_mins": float(avg_dur) if avg_dur is not None else 0.0
            }

    return [hours_data[h] for h in range(24)]


# ── GET /analytics/hotspots ───────────────────────────────────────────────────
@router.get("/hotspots", summary="Get GeoJSON hotspots from clusters data")
def get_hotspots():
    if not os.path.exists(HOTSPOTS_PATH):
        return {"type": "FeatureCollection", "features": []}

    try:
        with open(HOTSPOTS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {"type": "FeatureCollection", "features": []}

    features = []
    for item in data:
        hull_points = item.get("hull_points", [])
        coordinates = []
        for pt in hull_points:
            if len(pt) >= 2:
                # hull_points are [lat, lng], GeoJSON requires [lng, lat]
                coordinates.append([float(pt[1]), float(pt[0])])

        if coordinates:
            # GeoJSON Polygons must be closed rings
            if coordinates[0] != coordinates[-1]:
                coordinates.append(coordinates[0])
            while len(coordinates) < 4:
                coordinates.append(coordinates[0])

            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [coordinates]
                },
                "properties": {
                    "cluster_id": item.get("cluster_id"),
                    "incident_count": item.get("incident_count"),
                    "risk_level": item.get("risk_level"),
                    "avg_duration": item.get("avg_duration")
                }
            })

    return {"type": "FeatureCollection", "features": features}


# ── GET /analytics/risk_timeline ──────────────────────────────────────────────
@router.get("/risk_timeline", summary="Get risk timeline mapping cause and hour to risk scores")
def get_risk_timeline(db: Session = Depends(get_db)):
    if os.path.exists(RISK_TABLE_PATH):
        try:
            with open(RISK_TABLE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    # Fallback: compute from incidents table
    results = db.query(
        Incident.event_cause,
        Incident.hour_of_day,
        func.count(Incident.id).label("cnt"),
        func.avg(Incident.predicted_duration_mins).label("avg_dur")
    ).group_by(
        Incident.event_cause,
        Incident.hour_of_day
    ).all()

    risk_data = {}
    for cause, hour, cnt, avg_dur in results:
        avg_dur_val = float(avg_dur) if avg_dur is not None else 0.0
        if avg_dur_val < 30.0:
            risk = "low"
        elif avg_dur_val < 90.0:
            risk = "medium"
        else:
            risk = "high"

        key = f"{cause}_{hour}"
        risk_data[key] = {
            "risk": risk,
            "avg_duration": round(avg_dur_val, 1),
            "count": int(cnt)
        }

    return risk_data


# ── GET /analytics/incidents_timeline ─────────────────────────────────────────
@router.get("/incidents_timeline", summary="Get incident counts for the last 30 days")
def get_incidents_timeline(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    # List of dates in YYYY-MM-DD from 29 days ago to today
    dates = [(now - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(29, -1, -1)]

    start_date = now - timedelta(days=29)
    start_date_only = datetime(start_date.year, start_date.month, start_date.day)

    results = db.query(
        func.date(Incident.reported_at).label("date_str"),
        func.count(Incident.id).label("cnt")
    ).filter(
        Incident.reported_at >= start_date_only
    ).group_by(
        func.date(Incident.reported_at)
    ).all()

    counts_map = {row.date_str: int(row.cnt) for row in results if row.date_str is not None}
    counts = [counts_map.get(d, 0) for d in dates]

    return {
        "dates": dates,
        "counts": counts
    }
