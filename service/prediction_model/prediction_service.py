"""
Traffic Prediction and Dispatch Service
Provides high-level API for traffic prediction and emergency dispatch
"""

import os
import sys
import requests
import polyline
import numpy as np
import pandas as pd
from datetime import datetime
from .model_loader import TrafficModelLoader
from .llm_agent import parse_traffic_description

import logging
logger = logging.getLogger(__name__)

class DispatchPlanner:
    """Handles traffic event analysis and dispatch planning"""
    
    CITY_INVENTORY = {
        "total_constables": 150,
        "available_constables": 150,
        "total_barricades": 40,
        "available_barricades": 40
    }
    
    @staticmethod
    def calculate_detour(incident_lat, incident_lon):
        """
        Calculate alternative route around incident using routing APIs.
        Attempts Mappls first, falls back to OSRM.
        
        Args:
            incident_lat: Latitude of incident
            incident_lon: Longitude of incident
            
        Returns:
            dict: Route information with coordinates, distance, duration
        """
        try:
            mappls_key = os.getenv("MAPPLS_API_KEY")
            
            # Simulate a route bypassing the incident
            start_lon, start_lat = incident_lon - 0.015, incident_lat - 0.015
            end_lon, end_lat = incident_lon + 0.015, incident_lat + 0.015
            
            if mappls_key:
                print("[Routing] Using Mappls Enterprise Routing...")
                url = f"https://apis.mappls.com/advancedmaps/v1/{mappls_key}/route_adv/driving/{start_lon},{start_lat};{end_lon},{end_lat}?overview=full"
            else:
                print("[Routing] Using OSRM fallback...")
                url = f"http://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}?overview=full"

            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                encoded_polyline = data['routes'][0]['geometry']
                detour_coords = polyline.decode(encoded_polyline)
                
                return {
                    "status": "success",
                    "detour_distance_km": round(data['routes'][0]['distance'] / 1000, 2),
                    "detour_duration_mins": round(data['routes'][0]['duration'] / 60, 1),
                    "route_coordinates": detour_coords 
                }
            return {
                "status": f"route_api_error_{response.status_code}",
                "route_coordinates": []
            }
        except Exception as e:
            print(f"[Routing] Error: {e}")
            return {
                "status": f"routing_failed",
                "error": str(e),
                "route_coordinates": []
            }
    
    @staticmethod
    def dispatch_plan(latitude, longitude, event_cause, priority, description):
        """
        Generate comprehensive dispatch plan for traffic event.
        
        Args:
            latitude: Event latitude
            longitude: Event longitude
            event_cause: Type of incident (accident, construction, etc.)
            priority: Priority level (low, medium, high, critical)
            description: Event description for LLM parsing
            
        Returns:
            dict: Complete dispatch plan with predictions and recommendations
        """
        loader = TrafficModelLoader.get_models()
        
        if not loader.is_ready():
            return {
                "status": "error",
                "message": "Models not loaded. Call TrafficModelLoader.load_models() first."
            }
        
        # Phase 1: Find nearest node in graph
        try:
            distance_degrees, index = loader.spatial_tree.query(
                [latitude, longitude], k=1
            )
            distance_meters = distance_degrees * 111000
            closest_node = loader.df_nodes.iloc[index]
        except Exception as e:
            logger.error(f"Spatial query failed: {e}")
            return {
                "status": "error",
                "message": f"Spatial query failed: {e}"
            }
        
        # Phase 2: Parse description with LLM for enriched context
        try:
            llm_insights = parse_traffic_description(description)
        except Exception as e:
            logger.error(f"LLM parsing failed: {e}")
            llm_insights = {"severity_multiplier": 1.0, "hazards_present": ["unknown"], "special_assets_needed": ["standard_patrol"]}
        
        # Phase 3: Prepare features for ML model prediction
        try:
            severity_multiplier = llm_insights.get("severity_multiplier", 1.0)
            
            # Resolve spatial embeddings and historical parameters exactly matching backend/model.py
            # Compute distances using vectorized haversine formula
            lat_arr = loader.df_nodes['latitude'].values
            lng_arr = loader.df_nodes['longitude'].values
            
            dlat = np.radians(lat_arr - latitude)
            dlon = np.radians(lng_arr - longitude)
            a = np.sin(dlat/2)**2 + np.cos(np.radians(latitude)) * np.cos(np.radians(lat_arr)) * np.sin(dlon/2)**2
            distances = 6371000.0 * 2.0 * np.arcsin(np.sqrt(a))
            
            nearest_idx = np.argmin(distances)
            nearest_distance = float(distances[nearest_idx])
            
            spatial_cols = [f"spatial_emb_{i}" for i in range(16)]
            global_avg_emb = np.array([loader.avg_embeddings.get(col, 0.0) for col in spatial_cols])
            
            avg_hist_count = float(loader.df_nodes['historical_incident_count'].mean()) if 'historical_incident_count' in loader.df_nodes.columns else 0.0
            avg_hist_duration = float(loader.df_nodes['historical_median_duration'].mean()) if 'historical_median_duration' in loader.df_nodes.columns else 0.0
            
            if nearest_distance <= 500.0:
                nearest_row = loader.df_nodes.iloc[nearest_idx]
                emb = nearest_row[spatial_cols].values.astype(float)
                hist_count = float(nearest_row['historical_incident_count']) if 'historical_incident_count' in nearest_row and not pd.isna(nearest_row['historical_incident_count']) else avg_hist_count
                hist_duration = float(nearest_row['historical_median_duration']) if 'historical_median_duration' in nearest_row and not pd.isna(nearest_row['historical_median_duration']) else avg_hist_duration
                
                # If NaN, fallback
                if np.isnan(emb).any():
                    emb = np.where(np.isnan(emb), global_avg_emb, emb)
                if np.isnan(hist_count):
                    hist_count = avg_hist_count
                if np.isnan(hist_duration):
                    hist_duration = avg_hist_duration
            else:
                # Proximity average
                nearby_mask = distances <= 1000.0
                nearby = loader.df_nodes[nearby_mask]
                
                if len(nearby) >= 1:
                    emb = nearby[spatial_cols].mean().values.astype(float)
                    hist_count = float(nearby['historical_incident_count'].mean()) if 'historical_incident_count' in nearby.columns and not pd.isna(nearby['historical_incident_count'].mean()) else avg_hist_count
                    hist_duration = float(nearby['historical_median_duration'].mean()) if 'historical_median_duration' in nearby.columns and not pd.isna(nearby['historical_median_duration'].mean()) else avg_hist_duration
                    
                    if np.isnan(emb).any():
                        emb = np.where(np.isnan(emb), global_avg_emb, emb)
                    if np.isnan(hist_count):
                        hist_count = avg_hist_count
                    if np.isnan(hist_duration):
                        hist_duration = avg_hist_duration
                else:
                    emb = global_avg_emb
                    hist_count = avg_hist_count
                    hist_duration = avg_hist_duration

            # Categorical encoding matching model.py
            if event_cause in loader.encoder_cause.classes_:
                cause_encoded = loader.encoder_cause.transform([event_cause])[0]
            elif 'others' in loader.encoder_cause.classes_:
                cause_encoded = loader.encoder_cause.transform(['others'])[0]
            else:
                cause_encoded = 0

            if priority in loader.encoder_priority.classes_:
                priority_encoded = loader.encoder_priority.transform([priority])[0]
            elif 'Low' in loader.encoder_priority.classes_:
                priority_encoded = loader.encoder_priority.transform(['Low'])[0]
            elif 'LOW' in loader.encoder_priority.classes_:
                priority_encoded = loader.encoder_priority.transform(['LOW'])[0]
            else:
                priority_encoded = 1
                
            hour = datetime.now().hour
            
            # 21-element feature vector in exact order:
            # [cause_enc, priority_enc, hour_of_day, spatial_embeddings (16 elements), historical_incident_count, historical_median_duration]
            features = np.array([
                cause_encoded,
                priority_encoded,
                hour,
                emb[0], emb[1], emb[2], emb[3], emb[4], emb[5], emb[6], emb[7],
                emb[8], emb[9], emb[10], emb[11], emb[12], emb[13], emb[14], emb[15],
                hist_count,
                hist_duration
            ], dtype=float).reshape(1, 21)
            
            # Phase 3.5: Get model prediction
            try:
                traffic_pred = loader.ai_model.predict(features)[0]
                traffic_pred = max(10.0, float(traffic_pred))  # Clamp to min 10 mins
            except Exception as e:
                logger.warning(f"Model prediction failed: {e}, using default")
                traffic_pred = 30.0 + severity_multiplier * 15.0
                
        except Exception as e:
            logger.error(f"Feature preparation failed: {e}")
            traffic_pred = 30.0
            severity_multiplier = 1.0
        
        # Phase 4: Calculate routing and detour
        detour_info = DispatchPlanner.calculate_detour(latitude, longitude)
        
        # Calculate resources dynamically based on predicted jam duration
        jam_length_km = round(traffic_pred * severity_multiplier * 0.05, 2)
        constables = max(1, min(int(np.ceil(jam_length_km * 3)), 20))
        barricades = max(0, min(int(np.ceil(jam_length_km * 2)), 10))
        
        # Phase 5: Compile dispatch plan
        dispatch_plan = {
            "status": "success",
            "event_id": f"EVT_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "location": {
                "latitude": latitude,
                "longitude": longitude,
                "closest_node": {
                    "distance_meters": round(distance_meters, 1),
                    "node_id": str(closest_node.name) if hasattr(closest_node, 'name') else 'unknown'
                }
            },
            "event_details": {
                "cause": event_cause,
                "priority": priority,
                "description": description,
                "llm_analysis": llm_insights
            },
            "traffic_prediction": {
                "predicted_congestion_level": round(traffic_pred, 2),
                "predicted_clearance_time_minutes": round(traffic_pred, 1),
                "congestion_category": DispatchPlanner._categorize_congestion(traffic_pred),
                "severity_multiplier": severity_multiplier
            },
            "routing": detour_info,
            "resource_allocation": {
                "constables": constables,
                "barricades": barricades,
                "constables_needed": constables,
                "barricades_needed": barricades,
                "available_resources": DispatchPlanner.CITY_INVENTORY
            }
        }
        
        return dispatch_plan
    
    @staticmethod
    def _categorize_congestion(pred_value):
        """Categorize traffic congestion level"""
        if pred_value < 20:
            return "light"
        elif pred_value < 40:
            return "moderate"
        elif pred_value < 70:
            return "heavy"
        else:
            return "critical"


_prediction_cache = {}

def predict_traffic_impact(latitude, longitude, event_cause, priority, description):
    """
    Main prediction function - simplified interface for traffic impact analysis.
    Includes in-memory cache to prevent slow API/LLM calls on every reload.
    
    Args:
        latitude: Event latitude
        longitude: Event longitude  
        event_cause: Type of incident
        priority: Priority level
        description: Event description
        
    Returns:
        dict: Dispatch plan with predictions
    """
    from datetime import datetime
    current_hour = datetime.now().hour
    cache_key = (
        float(latitude) if latitude else 0.0,
        float(longitude) if longitude else 0.0,
        str(event_cause).lower(),
        str(priority).lower(),
        str(description).strip(),
        current_hour
    )
    
    if cache_key in _prediction_cache:
        return _prediction_cache[cache_key]
        
    try:
        res = DispatchPlanner.dispatch_plan(latitude, longitude, event_cause, priority, description)
        _prediction_cache[cache_key] = res
        return res
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
