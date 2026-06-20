import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError("CRITICAL ERROR: API Key not found. Check your .env file!")

genai.configure(api_key=GOOGLE_API_KEY)
gemini_model = genai.GenerativeModel('gemini-2.5-flash')

def parse_traffic_description(description_text: str) -> dict:
    """
    Sends incident description to Gemini and returns structured severity data.
    Handles both English and Kannada text.
    
    Returns:
        {
            "severity_multiplier": float (1.0 - 3.0),
            "hazards_present": list[str],
            "special_assets_needed": list[str]
        }
    """
    # Return safe defaults for empty/null descriptions
    if not description_text or str(description_text).strip() == "" or str(description_text).lower() == "nan":
        return {
            "severity_multiplier": 1.0,
            "hazards_present": ["none"],
            "special_assets_needed": ["standard_patrol"]
        }

    prompt = f"""
    You are an elite Traffic Command AI for the Bengaluru Traffic Police.
    Read the following field officer incident report (it may contain English or Kannada).
    
    Incident Report: "{description_text}"
    
    Your task is to extract operational intelligence and return it strictly as a JSON object.
    Do not include any markdown formatting, backticks, or extra text. ONLY return valid JSON.
    
    JSON Schema Requirements:
    - "severity_multiplier": A float from 1.0 to 3.0.
      (1.0 = minor/standard, 1.5 = heavy vehicle/bus/tree fall,
       2.0 = major blockage/accident, 3.0 = fire/flooding/complete road closure)
    - "hazards_present": A list of strings describing hazards
      (e.g., "waterlogging", "debris", "blocked_lane", "fire", "injured_persons")
    - "special_assets_needed": A list of strings for required equipment
      (e.g., "heavy_crane", "fire_engine", "chainsaw", "ambulance").
      Default to ["standard_patrol"] if nothing special is needed.
    """

    try:
        response = gemini_model.generate_content(prompt)
        cleaned_text = response.text.replace('```json', '').replace('```', '').strip()
        result = json.loads(cleaned_text)

        # Validate and clamp severity_multiplier to safe range
        result["severity_multiplier"] = max(1.0, min(3.0, float(result.get("severity_multiplier", 1.0))))
        result.setdefault("hazards_present", ["unknown"])
        result.setdefault("special_assets_needed", ["standard_patrol"])

        return result

    except json.JSONDecodeError:
        print(f"[LLM] JSON parse error for input: {description_text[:50]}...")
        return {
            "severity_multiplier": 1.0,
            "hazards_present": ["parse_error"],
            "special_assets_needed": ["standard_patrol"]
        }
    except Exception as e:
        print(f"[LLM] Gemini API error: {e}")
        return {
            "severity_multiplier": 1.0,
            "hazards_present": ["api_error"],
            "special_assets_needed": ["standard_patrol"]
        }