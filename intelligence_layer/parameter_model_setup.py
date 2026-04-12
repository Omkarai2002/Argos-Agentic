from openai import OpenAI
import os
import json
from dotenv import load_dotenv
from .actions_schema import ACTION_SCHEMA
from app.config import ALLOWED_ACTIONS
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def extract_actions(user_prompt, location, all_locations):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": f"""You are a drone action extractor.
Extract ONLY actions explicitly mentioned AT the target location from the user prompt.

Allowed actions: {ALLOWED_ACTIONS}

Mapping:
- "take photo" / "capture"    → IMAGE_CAPTURE_SINGLE
- "hover" / "wait" / "stay"   → HOVER
- "record video"              → VIDEO_START
- "stop video"                → VIDEO_STOP
- "gimbal down" / "look down" → GIMBAL_DOWN
- "zoom"                      → CAMERA_ZOOM

Rules:
- "hover THERE then go to X" → HOVER is at current location, NOT at X
- "go to X" / "fly to X"     → transit only, no actions unless explicitly stated
- DO NOT infer. Only assign if explicitly stated for that location.
- Return ONLY a raw JSON array. e.g. ["HOVER"] or []"""
                },
                {
                    "role": "user",
                    "content": f"""PROMPT: {user_prompt}
ALL WAYPOINTS IN ORDER: {all_locations}
TARGET LOCATION: {location}

Return JSON array of actions for "{location}" only."""
                }
            ]
        )
        raw = response.choices[0].message.content.strip()
        actions = json.loads(raw)
        return [a.strip().upper() for a in actions if a.strip().upper() in ACTION_SCHEMA]
    except Exception as e:
        print(f"⚠️ Action extraction failed for '{location}': {e}")
        return []

def get_params(user_prompt, location, action, candidates):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": f"""You are a drone mission optimizer.
Analyze the situation and select the MOST SUITABLE flight parameters for the scenario.

Guidelines:
- Image capture → slow speed (1-3 m/s), low-medium altitude for clear shots
- Hover         → speed = 0, maintain current altitude
- Inspection    → very slow speed, low altitude for detail
- Transit only  → higher speed (5-8 m/s), standard altitude
- Fast transit  → maximum safe speed, standard altitude

You are NOT required to copy candidate values.
Candidates are historical reference only — use your judgment to pick the best values for THIS scenario.

Allowed actions: {ALLOWED_ACTIONS}
Return ONLY a raw JSON object, no markdown, no explanation."""
                },
                {
                    "role": "user",
                    "content": f"""USER REQUEST: {user_prompt}
LOCATION: {location}
ACTIONS AT THIS LOCATION: {action or "None (transit only)"}
HISTORICAL CANDIDATES (reference only): {candidates}

Based on the user request and actions, choose the most suitable values.
Return: {{"speed": number, "altitude": number, "altitude_mode": string, "reason": string}}"""
                }
            ]
        )
        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
    except Exception as e:
        print(f"⚠️ Param LLM failed for '{location}': {e}")
        fallback = candidates[0] if candidates else {}
        return {
            "speed":         fallback.get("speed", 4),
            "altitude":      fallback.get("altitude", 40),
            "altitude_mode": fallback.get("altitude_mode", "AGL"),
            "reason":        "LLM unavailable — fallback to first candidate."
        }
def extract_action_and_params(user_prompt, location, all_locations, candidates):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": f"""
You are a drone mission planner.

For a given location, extract:
1. Actions explicitly mentioned
2. Best flight parameters

Rules:
- Only assign actions explicitly mentioned
- try understanding the actions mentioned below in allowed actions and plot it accordingly.

Allowed actions: {ALLOWED_ACTIONS}

Return ONLY JSON:
{{
  "actions": [],
  "speed": number,
  "altitude": number,
  "altitude_mode": string,
  "reason": string
}}
"""
                },
                {
                    "role": "user",
                    "content": f"""
PROMPT: {user_prompt}
ALL LOCATIONS: {all_locations}
TARGET LOCATION: {location}
CANDIDATES: {candidates}
"""
                }
            ]
        )

        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)

    except Exception as e:
        print(f"⚠️ Combined LLM failed for '{location}': {e}")
        fallback = candidates[0] if candidates else {}
        return {
            "actions": [],
            "speed": fallback.get("speed", 4),
            "altitude": fallback.get("altitude", 40),
            "altitude_mode": fallback.get("altitude_mode", "AGL"),
            "reason": "Fallback"
        }
def build_actions(action_list):
    return [
        {"type": schema.get("type", name), "params": schema.get("params")}
        for name in action_list
        if (schema := ACTION_SCHEMA.get(name.strip().upper()))
    ]

from collections import defaultdict

def optimize_parameters(validated: dict) -> dict:

    # STEP 1: GROUP by location
    grouped = {}

    for item in validated["graphdb_data"]:
        loc = item["location"]["location"]
        action = item["location"]["action"]
        candidates = item["value"]

        if loc not in grouped:
            grouped[loc] = {
                "location": loc,
                "actions": set(),
                "value": candidates
            }

        # merge actions safely
        if isinstance(action, list):
            grouped[loc]["actions"].update(action)
        elif action:
            grouped[loc]["actions"].add(action)

    # STEP 2: Convert grouped data back
    unique_data = [
        {
            "location": {
                "location": v["location"],
                "action": list(v["actions"])
            },
            "value": v["value"]
        }
        for v in grouped.values()
    ]


    # STEP 3: Prepare all locations list
    all_locations = [item["location"]["location"] for item in unique_data]

    final_plan = []

    # STEP 4: Loop over UNIQUE locations only
    for item in unique_data:
        location   = item["location"]["location"]
        candidates = item["value"]

        result = extract_action_and_params(
            validated["prompt"],
            location,
            all_locations,
            candidates
        )

        action = result["actions"]
        best = result

        print(f"📍 {location} | 🎬 {action}")

        final_plan.append({
            "location":      location,
            "action":        build_actions(action),
            "speed":         best["speed"],
            "altitude":      best["altitude"],
            "altitude_mode": best["altitude_mode"],
            "reason":        best["reason"]
        })

    validated["final_result"] = final_plan

    print("🚀 optimization complete")

    return validated


# if __name__ == "__main__":
#     validated = {
#         'org_id': 1, 'site_id': 1, 'user_id': 1,
#         'prompt': 'fly to pallet move fast, hover there for a min then go to dock',
#         'graphdb_data': [
#             {
#                 'location': {'location': 'Pallet Sorting Zone', 'action': 'IMAGE_CAPTURE_SINGLE'},
#                 'value': [
#                     {'mission_id': '425', 'speed': 4, 'altitude': 40, 'altitude_mode': 'AGL', 'actions': []},
#                     {'mission_id': '419', 'speed': 4, 'altitude': 40, 'altitude_mode': 'AGL', 'actions': []},
#                 ]
#             },
#             {
#                 'location': {'location': 'Receiving Dock Apron', 'action': 'null'},
#                 'value': [
#                     {'mission_id': '416', 'speed': 4, 'altitude': 40, 'altitude_mode': 'AGL', 'actions': []},
#                     {'mission_id': '412', 'speed': 4, 'altitude': 40, 'altitude_mode': 'AGL', 'actions': []},
#                 ]
#             }
#         ]
#     }

#     result = optimize_parameters(validated)
#     print("\n🚁 Optimized Plan:\n")
#     for wp in result:
#         print(f"📍 Location : {wp['location']}")
#         print(f"⚡ Speed    : {wp['speed']} m/s")
#         print(f"🏔️  Altitude : {wp['altitude']} ({wp['altitude_mode']})")
#         print(f"🎬 Actions  : {wp['action']}")
#         print(f"💬 Reason   : {wp['reason']}")
#         print("-" * 60)