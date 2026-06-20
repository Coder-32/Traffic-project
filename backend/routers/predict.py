import asyncio
import logging
from math import ceil
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from model import predict_duration
from llm_agent import parse_traffic_description
from schemas import (IncidentInput, PredictionOutput, 
                     BatchIncidentInput, BatchPredictionOutput, SuggestedResource)
from database import get_db
from db_models import Resource


logger = logging.getLogger(__name__)

router = APIRouter()

# ── Startup & DB Lock ─────────────────────────────────────────────────────────
db_lock = asyncio.Lock()

async def suggest_resources(
    special_assets_needed: list[str],
    officers_needed: int,
    barricade_points: int,
    db: Session
) -> list[SuggestedResource]:
    async with db_lock:
        resources = db.query(Resource).all()
        
    resource_map = {r.name: r for r in resources}
    suggested = []
    
    # 1. Traffic Officers
    officer_res = resource_map.get("Traffic Officer")
    if officer_res:
        avail = officer_res.available_count
        status_val = "sufficient" if avail >= officers_needed else f"shortage: only {avail} available"
        suggested.append(SuggestedResource(
            resource_name="Traffic Officer",
            resource_id=officer_res.id,
            quantity_suggested=officers_needed,
            quantity_available=avail,
            status=status_val
        ))
        
    # 2. Barricade Sets
    barricade_needed = ceil(barricade_points / 10)
    barricade_res = resource_map.get("Barricade Set (10 units)")
    if barricade_res:
        avail = barricade_res.available_count
        status_val = "sufficient" if avail >= barricade_needed else f"shortage: only {avail} available"
        suggested.append(SuggestedResource(
            resource_name="Barricade Set (10 units)",
            resource_id=barricade_res.id,
            quantity_suggested=barricade_needed,
            quantity_available=avail,
            status=status_val
        ))
        
    # 3. Special Assets Needed
    special_mapping = {
        "heavy_crane": "Heavy Crane",
        "fire_engine": "Fire Engine",
        "chainsaw": "Chainsaw",
        "ambulance": "Ambulance",
        "tow_truck": "Tow Truck",
        "water_tanker": "Water Tanker"
    }
    
    # Use sorted and set to keep items unique and output deterministic
    for asset in sorted(list(set(special_assets_needed))):
        if asset == "standard_patrol":
            continue
        db_name = special_mapping.get(asset)
        if db_name:
            res_item = resource_map.get(db_name)
            if res_item:
                avail = res_item.available_count
                status_val = "sufficient" if avail >= 1 else f"shortage: only {avail} available"
                suggested.append(SuggestedResource(
                    resource_name=db_name,
                    resource_id=res_item.id,
                    quantity_suggested=1,
                    quantity_available=avail,
                    status=status_val
                ))
                
    return suggested

# ── Shared Core Prediction Logic ──────────────────────────────────────────────
async def run_prediction(incident: IncidentInput, db: Session) -> PredictionOutput:
    # Step 1: Call model.py
    result = predict_duration(incident)
    predicted_duration_mins = max(10.0, result["predicted_duration_mins"])
    spatial_resolution_method = result["spatial_resolution_method"]
    nearest_junction = result["nearest_junction"]
    distance_to_nearest_m = result["distance_to_nearest_m"]

    
    # Step 2: Call llm_agent.py
    llm_result = parse_traffic_description(incident.description)
    severity_multiplier = llm_result["severity_multiplier"]
    hazards_present = llm_result["hazards_present"]
    special_assets_needed = llm_result["special_assets_needed"]
    
    # Step 3: Calculate derived outputs
    jam_length_km = round(predicted_duration_mins * severity_multiplier * 0.05, 2)
    officers_needed = max(0, min(ceil(jam_length_km * 3), 20))
    barricade_points = max(0, min(ceil(jam_length_km * 2), 10))
    
    # Step 4: Build suggested_resources list
    suggested_resources = await suggest_resources(
        special_assets_needed=special_assets_needed,
        officers_needed=officers_needed,
        barricade_points=barricade_points,
        db=db
    )
    
    resource_shortage = any("shortage" in res.status for res in suggested_resources)
    
    # Step 5: Return PredictionOutput
    return PredictionOutput(
        predicted_duration_mins=predicted_duration_mins,
        severity_multiplier=severity_multiplier,
        jam_length_km=jam_length_km,
        officers_needed=officers_needed,
        barricade_points=barricade_points,
        hazards_present=hazards_present,
        special_assets_needed=special_assets_needed,
        latitude=incident.latitude,
        longitude=incident.longitude,
        address=incident.address,
        junction=incident.junction,
        zone=incident.zone,
        corridor=incident.corridor,
        priority=incident.priority,
        event_cause=incident.event_cause,
        spatial_resolution_method=spatial_resolution_method,
        nearest_junction=nearest_junction,
        distance_to_nearest_m=distance_to_nearest_m,
        suggested_resources=suggested_resources,
        resource_shortage=resource_shortage
    )

# ── POST /predict/single ──────────────────────────────────────────────────────
@router.post("/single", response_model=PredictionOutput, summary="Run single prediction")
async def predict_single(incident: IncidentInput, db: Session = Depends(get_db)) -> PredictionOutput:
    try:
        return await run_prediction(incident, db)
    except Exception as exc:
        logger.exception("Single prediction failed")
        raise HTTPException(status_code=500, detail=str(exc))

# ── POST /predict/batch ───────────────────────────────────────────────────────
@router.post("/batch", response_model=BatchPredictionOutput, summary="Run batch prediction")
async def predict_batch(batch: BatchIncidentInput, db: Session = Depends(get_db)) -> BatchPredictionOutput:
    try:
        # Run run_prediction() for each incident concurrently using asyncio.gather
        tasks = [run_prediction(inc, db) for inc in batch.incidents]
        results = await asyncio.gather(*tasks)
        
        total_officers_needed = sum(res.officers_needed for res in results)
        high_priority_count = sum(1 for inc in batch.incidents if inc.priority == "High")
        
        return BatchPredictionOutput(
            results=results,
            total_officers_needed=total_officers_needed,
            high_priority_count=high_priority_count
        )
    except Exception as exc:
        logger.exception("Batch prediction failed")
        raise HTTPException(status_code=500, detail=str(exc))


# ── GET /incidents/sample ─────────────────────────────────────────────────────
@router.get("/sample", summary="Get sample pre-filled incidents")
async def get_sample_incidents():
    # Returns the 8 hardcoded sample incidents from index.html (pre-filled fields)
    sample_incidents = [
      {
        "id": "FKID000000",
        "lat": 13.0400041, "lng": 77.5180991,
        "address": "Mumbai Bengaluru Highway, Jalahalli Cross Junction, Peenya",
        "junction": "Jalahalli Cross",
        "event_cause": "vehicle_breakdown",
        "priority": "High",
        "corridor": "Tumkur Road",
        "zone": "North Zone",
        "duration_mins": 40.0,
        "jam_length_km": 2.1,
        "severity_score": 0.78,
        "officers_needed": 6,
        "description": "LCV broken down at SM Circle incoming man track",
        "status": "open",
        "spatial_embeddings": [0.25, -0.42, 0.68, 0.12, -0.85, 0.33, 0.51, -0.19, 0.08, -0.63, 0.77, -0.05, 0.39, -0.71, 0.18, 0.44],
        "historical_count": 34.0,
        "historical_median_mins": 35.0,
        "barricades_needed": 4,
        "suggested_diversions": ["Bypass Peenya Industrial Area", "ORR Outer Loop Connection"],
        "timeline": { "start": "14:10", "modified": "14:22", "resolved": "Pending" },
        "llm_analysis": "High severity score (0.78) is assigned because Peenya / Jalahalli Cross is a major arterial junction connecting Tumkur Road to outer logistics zones. An LCV breakdown blocking a central lane directly results in immediate cascade gridlock during peak shipping hours."
      },
      {
        "id": "FKID000002",
        "lat": 12.955622, "lng": 77.5857083,
        "address": "Lalbagh Main Road, Dr Sri Shantaveera Swami Circle, Mavalli",
        "junction": "Urvashi Junction",
        "event_cause": "others",
        "priority": "Low",
        "corridor": "Non-corridor",
        "zone": "Central Zone 2",
        "duration_mins": 25.0,
        "jam_length_km": 0.8,
        "severity_score": 0.31,
        "officers_needed": 2,
        "description": "New cement laid at drainage chamber causing slow movement",
        "status": "open",
        "spatial_embeddings": [-0.15, 0.52, -0.38, 0.62, 0.15, -0.43, 0.21, -0.59, 0.78, 0.13, -0.27, 0.45, -0.69, 0.01, 0.58, -0.34],
        "historical_count": 12.0,
        "historical_median_mins": 20.0,
        "barricades_needed": 1,
        "suggested_diversions": ["Dr Sri Shantaveera Swami detour", "JC Road Divert"],
        "timeline": { "start": "14:25", "modified": "14:38", "resolved": "Pending" },
        "llm_analysis": "Low severity score (0.31) due to localized construction at a drainage chamber. The construction zone is restricted to a minor road segment, causing slow flow but not complete corridor gridlock."
      },
      {
        "id": "FKID000003",
        "lat": 13.0061469, "lng": 77.5794348,
        "address": "Sankey Road, Bashyam Circle, Sadashiva Nagar",
        "junction": "Bashyam Circle",
        "event_cause": "tree_fall",
        "priority": "High",
        "corridor": "Non-corridor",
        "zone": "Central Zone",
        "duration_mins": 90.0,
        "jam_length_km": 3.2,
        "severity_score": 0.85,
        "officers_needed": 8,
        "description": "Tree fall blocking road",
        "status": "open",
        "spatial_embeddings": [0.65, 0.12, -0.58, 0.32, -0.15, 0.73, -0.11, 0.49, -0.38, 0.53, 0.17, -0.65, 0.29, -0.41, 0.78, 0.04],
        "historical_count": 8.0,
        "historical_median_mins": 75.0,
        "barricades_needed": 5,
        "suggested_diversions": ["Sankey Tank Road East bypass", "Sadashiva Nagar Ring detour"],
        "timeline": { "start": "13:50", "modified": "14:15", "resolved": "Pending" },
        "llm_analysis": "Severe rating (0.85) is driven by complete lane blockage from a fallen mature tree on Sankey Road. Requires municipal forest department dispatch. Traffic is backing up towards Sadashiva Nagar."
      },
      {
        "id": "FKID000004",
        "lat": 12.95398, "lng": 77.5852333,
        "address": "Lalbagh Fort Road, Lalbagh Main Gate Junction, Wilson Garden",
        "junction": "Lalbagh Main Gate",
        "event_cause": "vehicle_breakdown",
        "priority": "Low",
        "corridor": "Non-corridor",
        "zone": "Central Zone",
        "duration_mins": 38.0,
        "jam_length_km": 1.1,
        "severity_score": 0.42,
        "officers_needed": 3,
        "description": "Private bus broken down",
        "status": "open",
        "spatial_embeddings": [-0.45, -0.12, 0.28, -0.52, 0.65, -0.23, -0.51, 0.09, 0.18, -0.33, 0.47, -0.15, -0.09, 0.51, -0.28, 0.64],
        "historical_count": 22.0,
        "historical_median_mins": 30.0,
        "barricades_needed": 2,
        "suggested_diversions": ["Fort Road alternate arc", "Khosla Garden bypass"],
        "timeline": { "start": "14:05", "modified": "14:10", "resolved": "Pending" },
        "llm_analysis": "Moderate/Low score (0.42) as the broken down private bus has pulled over partially onto the side shoulder. One lane is restricted, but general traffic maintains flow with officer guidance."
      },
      {
        "id": "FKID000005",
        "lat": 13.0664854, "lng": 77.5998755,
        "address": "Jakkur Layout, Amrutahalli",
        "junction": "Amrutahalli Junction",
        "event_cause": "accident",
        "priority": "High",
        "corridor": "Non-corridor",
        "zone": "North Zone 1",
        "duration_mins": 55.0,
        "jam_length_km": 2.8,
        "severity_score": 0.91,
        "officers_needed": 10,
        "description": "Road accident blocking lanes",
        "status": "open",
        "spatial_embeddings": [0.75, -0.62, 0.18, 0.42, -0.35, 0.13, 0.61, -0.29, 0.58, -0.43, 0.17, -0.25, 0.59, -0.11, 0.38, 0.14],
        "historical_count": 15.0,
        "historical_median_mins": 45.0,
        "barricades_needed": 6,
        "suggested_diversions": ["Jakkur flyover bypass", "Hebbal Outer connector"],
        "timeline": { "start": "14:30", "modified": "14:35", "resolved": "Pending" },
        "llm_analysis": "Critical severity score (0.91) due to a multi-vehicle collision blocking two primary lanes. Medical and clearing assistance dispatched. Severe tailback extending toward Jakkur."
      },
      {
        "id": "FKID000006",
        "lat": 12.9328703, "lng": 77.4879814,
        "address": "Kengeri Main Road, Ambedkar Circle, Kengeri Satellite Town",
        "junction": "Ambedkar Circle Kengeri",
        "event_cause": "vehicle_breakdown",
        "priority": "Low",
        "corridor": "Non-corridor",
        "zone": "South Zone",
        "duration_mins": 22.0,
        "jam_length_km": 0.6,
        "severity_score": 0.28,
        "officers_needed": 2,
        "description": "BMTC bus broken down",
        "status": "open",
        "spatial_embeddings": [-0.65, 0.32, -0.18, 0.22, 0.45, -0.53, -0.11, 0.39, -0.28, 0.63, -0.57, 0.15, -0.19, 0.31, -0.48, 0.14],
        "historical_count": 19.0,
        "historical_median_mins": 25.0,
        "barricades_needed": 1,
        "suggested_diversions": ["Satellite Town Inner Ring", "Mysore Road detour"],
        "timeline": { "start": "14:38", "modified": "14:40", "resolved": "Pending" },
        "llm_analysis": "Low priority score (0.28) assigned because the BMTC bus breakdown occurred near a designated wide bus bay, allowing traffic to merge easily with minimal friction."
      },
      {
        "id": "FKID000008",
        "lat": 12.97883573, "lng": 77.59953728,
        "address": "Link Road, Ashoknagar, Bengaluru Central",
        "junction": "Queens Statue Circle",
        "event_cause": "public_event",
        "priority": "High",
        "corridor": "CBD 2",
        "zone": "Central",
        "duration_mins": 120.0,
        "jam_length_km": 4.1,
        "severity_score": 0.88,
        "officers_needed": 14,
        "description": "Cricket Match at M Chinnaswamy Stadium",
        "status": "open",
        "spatial_embeddings": [0.15, 0.82, -0.48, 0.12, -0.55, 0.63, -0.31, 0.79, -0.18, 0.43, -0.07, 0.85, -0.29, 0.61, -0.18, 0.74],
        "historical_count": 45.0,
        "historical_median_mins": 110.0,
        "barricades_needed": 8,
        "suggested_diversions": ["M Chinnaswamy outer detour", "MG Road bypass"],
        "timeline": { "start": "13:30", "modified": "14:00", "resolved": "Pending" },
        "llm_analysis": "High severity score (0.88) due to extreme pedestrian and vehicle volume exiting Chinnaswamy Stadium. Multiple central corridors are locked; alternate transit route is highly recommended."
      },
      {
        "id": "FKID000007",
        "lat": 12.973175, "lng": 77.6003961,
        "address": "State Bank of India Road, Saint Marks Circle, Shanthala Nagar",
        "junction": "Saint Marks Circle",
        "event_cause": "others",
        "priority": "Low",
        "corridor": "Non-corridor",
        "zone": "Central",
        "duration_mins": 60.0,
        "jam_length_km": 0.5,
        "severity_score": 0.22,
        "officers_needed": 1,
        "description": "BWSSB water pipe work from Coffee Day to Rotary Circle",
        "status": "open",
        "spatial_embeddings": [-0.25, 0.12, -0.08, 0.52, 0.15, -0.23, 0.01, -0.49, 0.68, 0.03, -0.17, 0.35, -0.59, -0.11, 0.48, -0.24],
        "historical_count": 28.0,
        "historical_median_mins": 50.0,
        "barricades_needed": 1,
        "suggested_diversions": ["St Marks loop path", "Residency Road bypass"],
        "timeline": { "start": "14:00", "modified": "14:15", "resolved": "Pending" },
        "llm_analysis": "Low score (0.22) because the BWSSB construction work is confined to a safety trench off the main lane. Vehicles slow down slightly on approach but road capacity is mostly preserved."
      }
    ]
    return sample_incidents

# ── GET /predict/causes ───────────────────────────────────────────────────────
@router.get("/causes", summary="Get valid event causes")
async def get_valid_causes():
    return [
        "vehicle_breakdown", "accident", "tree_fall", "water_logging",
        "public_event", "procession", "protest", "construction",
        "others", "congestion", "vip_movement", "pot_holes",
        "road_conditions", "debris"
    ]
