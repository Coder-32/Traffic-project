import math
import urllib.request
import urllib.error
import json
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from db_models import Incident

router = APIRouter()


class RoutingAlternateRequest(BaseModel):
    origin_lat: float
    origin_lng: float
    destination_lat: float
    destination_lng: float
    avoid_incident_ids: Optional[List[str]] = None


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees) in meters.
    """
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def call_osrm_route(waypoints_str: str) -> dict:
    """
    Helper function to query OSRM driving service.
    """
    url = f"https://router.project-osrm.org/route/v1/driving/{waypoints_str}?overview=full&geometries=geojson"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "TrafficProjectSmartRouting/1.0"}
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


@router.post("/alternate", summary="Find alternate route avoiding active traffic jams")
def get_alternate_route(payload: RoutingAlternateRequest, db: Session = Depends(get_db)):
    # 1. Fetch active incidents to potentially avoid
    query = db.query(Incident).filter(Incident.status == "active")
    if payload.avoid_incident_ids is not None and len(payload.avoid_incident_ids) > 0:
        query = query.filter(Incident.id.in_(payload.avoid_incident_ids))
    active_incidents = query.all()

    # 2. Get direct route from OSRM
    origin_coords = f"{payload.origin_lng},{payload.origin_lat}"
    dest_coords = f"{payload.destination_lng},{payload.destination_lat}"

    try:
        data1 = call_osrm_route(f"{origin_coords};{dest_coords}")
    except urllib.error.URLError as e:
        raise HTTPException(status_code=502, detail=f"OSRM API call failed: {e.reason}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to contact OSRM API: {str(e)}")

    if "routes" not in data1 or not data1["routes"]:
        raise HTTPException(status_code=400, detail="No driving route found between origin and destination")

    route1 = data1["routes"][0]
    direct_geojson = route1["geometry"]
    direct_distance_km = float(route1["distance"]) / 1000.0
    direct_duration_mins = float(route1["duration"]) / 60.0

    # 3. Detect incidents on or near the direct route and compute detour waypoints
    passed_incidents = []
    detour_waypoints = []

    coords = direct_geojson.get("coordinates", [])

    for inc in active_incidents:
        # Avoidance radius in meters (incident.jam_length_km * 1000). Clamp to min of 100m.
        radius = max(100.0, inc.jam_length_km * 1000.0)

        is_near = False
        min_dist = float("inf")
        closest_idx = -1

        for idx, coord in enumerate(coords):
            if len(coord) >= 2:
                d = haversine_distance(coord[1], coord[0], inc.latitude, inc.longitude)
                if d <= radius:
                    is_near = True
                if d < min_dist:
                    min_dist = d
                    closest_idx = idx

        # If direct route passes through this incident's jam zone, calculate waypoint
        if is_near and closest_idx != -1:
            passed_incidents.append(inc)

            # Estimate travel direction vector at closest point
            A = coords[max(0, closest_idx - 1)]
            B = coords[min(len(coords) - 1, closest_idx + 1)]

            dx = B[0] - A[0]  # longitude change
            dy = B[1] - A[1]  # latitude change

            length = math.sqrt(dx * dx + dy * dy)
            if length > 0:
                perp_dx = -dy / length
                perp_dy = dx / length
            else:
                perp_dx = 0.0
                perp_dy = 1.0

            # Detour waypoint: offset by 0.02 degrees away from incident center perpendicular to direction of travel
            wp_lng = inc.longitude + perp_dx * 0.02
            wp_lat = inc.latitude + perp_dy * 0.02

            detour_waypoints.append({
                "idx": closest_idx,
                "lng": wp_lng,
                "lat": wp_lat,
                "incident_id": inc.id
            })

    passes_through_jams = [inc.id for inc in passed_incidents]
    blocked = len(passes_through_jams) > 0

    direct_route_res = {
        "geojson": direct_geojson,
        "distance_km": round(direct_distance_km, 3),
        "duration_mins": round(direct_duration_mins, 2),
        "passes_through_jams": passes_through_jams,
        "blocked": blocked
    }

    # 4. Generate alternate route
    if not blocked:
        # If no incidents intersected, alternate is the same as direct
        alternate_route_res = {
            "geojson": direct_geojson,
            "distance_km": round(direct_distance_km, 3),
            "duration_mins": round(direct_duration_mins, 2),
            "extra_distance_km": 0.0,
            "time_saved_mins": 0.0,
            "avoids_incidents": []
        }
    else:
        # Sort detour waypoints chronologically by their closest_idx along the direct route to avoid looping
        sorted_wps = sorted(detour_waypoints, key=lambda w: w["idx"])

        # Construct coordinate sequence for OSRM request
        wp_list = [origin_coords]
        for wp in sorted_wps:
            wp_list.append(f"{wp['lng']},{wp['lat']}")
        wp_list.append(dest_coords)
        waypoints_str = ";".join(wp_list)

        try:
            data2 = call_osrm_route(waypoints_str)
        except Exception:
            data2 = None

        if data2 and "routes" in data2 and data2["routes"]:
            route2 = data2["routes"][0]
            alt_geojson = route2["geometry"]
            alt_distance_km = float(route2["distance"]) / 1000.0
            alt_duration_mins = float(route2["duration"]) / 60.0

            extra_distance_km = max(0.0, alt_distance_km - direct_distance_km)

            # Net time saved = sum of avoided jam predicted durations - detour travel time penalty
            total_jam_duration = sum(inc.predicted_duration_mins for inc in passed_incidents)
            detour_penalty = alt_duration_mins - direct_duration_mins
            time_saved_mins = max(0.0, total_jam_duration - detour_penalty)

            alternate_route_res = {
                "geojson": alt_geojson,
                "distance_km": round(alt_distance_km, 3),
                "duration_mins": round(alt_duration_mins, 2),
                "extra_distance_km": round(extra_distance_km, 3),
                "time_saved_mins": round(time_saved_mins, 2),
                "avoids_incidents": passes_through_jams
            }
        else:
            # Fallback if alternate routing OSRM query failed or found no path
            alternate_route_res = {
                "geojson": direct_geojson,
                "distance_km": round(direct_distance_km, 3),
                "duration_mins": round(direct_duration_mins, 2),
                "extra_distance_km": 0.0,
                "time_saved_mins": 0.0,
                "avoids_incidents": []
            }

    return {
        "direct_route": direct_route_res,
        "alternate_route": alternate_route_res
    }
