"""
Predictions router  –  /api/predict
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

import llm_agent
import model
from schemas import PredictionRequest, PredictionResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/predict", response_model=PredictionResponse, summary="Predict traffic incident")
async def predict_incident(req: PredictionRequest) -> PredictionResponse:
    """
    Accepts location + contextual features and returns:
    - NGBoost severity score with probabilistic bounds
    - Decoded cause & priority labels
    - Optional Gemini LLM enrichment (summary + recommendation)
    """
    try:
        # ── Step 1: NGBoost prediction ──────────────────────────────────────
        model_output = model.predict(req)

        # ── Step 2: LLM enrichment (non-blocking on failure) ────────────────
        llm_output = llm_agent.score(
            location      = req.location,
            description   = req.description,
            hour          = req.hour,
            weather       = req.weather.value,
            severity_score= model_output["severity_score"],
        )

        # ── Step 3: Compose response ────────────────────────────────────────
        return PredictionResponse(
            location          = req.location,
            **model_output,
            **llm_output,
        )

    except Exception as exc:
        logger.exception("Prediction failed for location=%s", req.location)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/locations", summary="List known Bengaluru hotspot locations")
async def list_locations() -> dict:
    """
    Returns a curated list of Bengaluru traffic hotspot locations
    that the frontend can use to pre-populate the location dropdown.
    """
    hotspots = [
        {"name": "Silk Board Junction",         "lat": 12.9176, "lng": 77.6237},
        {"name": "KR Puram Bridge",             "lat": 13.0047, "lng": 77.6938},
        {"name": "Hebbal Flyover",              "lat": 13.0358, "lng": 77.5970},
        {"name": "Marathahalli Bridge",         "lat": 12.9591, "lng": 77.6974},
        {"name": "Tin Factory Junction",        "lat": 12.9942, "lng": 77.6599},
        {"name": "Electronic City",             "lat": 12.8455, "lng": 77.6603},
        {"name": "Bannerghatta Road",           "lat": 12.8891, "lng": 77.5946},
        {"name": "Whitefield",                  "lat": 12.9698, "lng": 77.7499},
        {"name": "Yeshwanthpur",                "lat": 13.0270, "lng": 77.5388},
        {"name": "Nagawara Junction",           "lat": 13.0427, "lng": 77.6173},
        {"name": "Koramangala",                 "lat": 12.9352, "lng": 77.6245},
        {"name": "Indiranagar 100 Feet Road",   "lat": 12.9784, "lng": 77.6408},
        {"name": "Outer Ring Road (ORR)",       "lat": 12.9352, "lng": 77.6869},
        {"name": "Mekhri Circle",               "lat": 13.0053, "lng": 77.5696},
        {"name": "Madiwala Checkpost",          "lat": 12.9206, "lng": 77.6195},
    ]
    return {"locations": hotspots, "count": len(hotspots)}
