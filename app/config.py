import os
import json
import dotenv
dotenv.load_dotenv()

PROMPT_COMPLETION_DATABASE_CONFIG = {
    "DB_NAME": os.getenv("DB_NAME"),
    "DB_USER": os.getenv("DB_USER"),
    "DB_PASSWORD": os.getenv("DB_PASSWORD"),
    "DB_HOST": os.getenv("DB_HOST"),
    "DB_PORT": int(os.getenv("DB_PORT", 5432))
}
PRODUCTION_DB_CONFIG={
    "PRODUCTION_DB_NAME": os.getenv("PRODUCTION_DB_NAME"),
    "PRODUCTION_DB_USER": os.getenv("PRODUCTION_DB_USER"),
    "PRODUCTION_DB_PASSWORD": os.getenv("PRODUCTION_DB_PASSWORD"),
    "PRODUCTION_HOST": os.getenv("PRODUCTION_HOST"),
    "PRODUCTION_PORT": int(os.getenv("PRODUCTION_PORT"))
}
MAX_TOKEN_LIMIT_FOR_PROMPT_COMPLETION = 8192
MIN_TOKEN_LIMIT_FOR_PROMPT_COMPLETION = 2
MODEL_NAME_FOR_PROMPT_COMPLETION = "gpt-4o-mini"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TEMPERATURE_FOR_PROMPT_COMPLETION = 0
MODEL_FOR_EMBEDDING = "text-embedding-3-large"
MODEL_FOR_CLASSIFICATION ="gpt-5-nano"
TEMPERATURE_FOR_CLASSIFICATION=0
SMALL_MODEL="gpt-4o"
MEDIUM_MODEL="gpt-4o"
LARGE_MODEL="gpt-4o"
XLARGE_MODEL="gpt-4.1"
COMPLEXITY_THRESHOLD_FOR_POINT_MISSION=0.8
COMPLEXITY_THRESHOLD_FOR_PATH_MISSION=0.8
COMPLEXITY_THRESHOLD_FOR_GRID_MISSION=0.8
COMPLEXITY_THRESHOLD_FOR_3D_MISSION=0.8
TEMPERATURE_FOR_JSON_EXTRACTION=0
import os

ARGOS_SOCKET_URL = os.getenv("ARGOS_SOCKET_URL", "http://localhost:3000")
P2F_TOKEN = os.getenv("P2F_SECRET_TOKEN", "your-secret-token-here")
WORK_PATTERN_PROMPT = """
You are a mission intent analyzer for autonomous drones.
Classify the following mission into exactly ONE work pattern:

1. stop_and_work
   - The main task happens while the drone is stopped, hovering, loitering,
     or holding position at one or more locations.

2. move_and_work
   - The main task happens while the drone is continuously moving along a route.
     Stopping would interrupt the task.

3. cover_area
   - The main task is to systematically cover an entire area so nothing is missed.

4. inspect_structure
   - The main task involves inspecting or scanning a structure or volume across
     height or vertical extent (towers, turbines, buildings, facades).

CATEGORIES:

1) absolute_location
   - The instruction refers ONLY to named places, landmarks, coordinates, or fixed destinations.
   - Movement is expressed purely as "go to X", "fly to X", "visit X", "go straight to X".
   - Contains NO relative directional offsets (left, right, north 200 m, east 100 m, etc.)
   - Example: "Go to Location A, then go straight to Location B and take a photo."

2) relative_direction
   - The instruction refers ONLY to movement defined by direction, bearing, or distance offset.
   - Contains NO named locations, landmarks, place names, or coordinates.
   - Movement is expressed as compass directions (north, south, east, west),
     relative offsets (left, right, forward, backward) WITH a distance,
     or explicit distance-based moves.
   - Example: "Go right 200 metres, then move north 100 metres."

3) intent_understanding
   - The instruction is a HYBRID that contains BOTH a named/fixed location
     AND at least one directional OFFSET (a direction paired with a distance or displacement).
   - Example: "Fly to Location A, then go right 400 metres and take a photo."

---
---

### Instructions:
- Carefully analyze the full input.
- Identify whether it contains:
  - Named locations (e.g., "Location A", "Building 3", GPS coordinates)
  - Relative movements (e.g., "left", "right", "north", "forward", "200 meters")

---
Rules:
- Altitude alone does NOT imply inspect_structure.
- Hovering at one or more altitudes is still stop_and_work unless a structure
  is being inspected.
- Do NOT infer execution type (point/path/grid/3d).
- Return ONLY valid JSON.
- Remember all the fields should be present as mentioned in the json below strictly 
-remember json should compulsory consist of 4 fields -->work_pattern,reason,category,complexity
Mission:
<<< {mission_text} >>>

JSON:
{{
  "work_pattern": "stop_and_work | move_and_work | cover_area | inspect_structure",
  "reason": "one short sentence",
  "category":absolute_location | relative_direction | intent_understanding
  "complexity":"enter the complexity score between 0 to 1 over here ,the more complex or more action based the prompt--> {mission_text} is like long heavy to understand by the model more should be the confidence threshold it should only be a floating value between 0 to 1 and no text or any value other than that "
}}
"""
JSON_EXTRACTION_PROMPT = """
You are a strict drone-mission intent extraction engine.
Your ONLY job is to convert natural language drone instructions into structured JSON.

════════════════════════════════════════
OUTPUT SCHEMA
════════════════════════════════════════

{
  "finish": {
    "type": null,        // See FINISH TYPES below
    "duration": null     // seconds, only for HOVER finish
  },
  "takeoff": {
    "altitude": null,    // meters
    "mode": null,
    "speed": null        // m/s
  },
  "camera": {
    "pitch": null,       // degrees
    "yaw_mode": null,
    "poi": null          // place name only if explicitly mentioned
  },
  "waypoints": []
}

────────────────────────────────────────
WAYPOINT SCHEMA (each item in waypoints[])
────────────────────────────────────────
{
  "name": null,           // place name only if user explicitly mentions it
  "altitude": null,       // meters
  "altitude_mode": null,  // "AGL" or "ASL" only
  "speed": null,          // m/s
  "radius": null,         // meters
  "actions": []
}

────────────────────────────────────────
ACTION SCHEMA (each item in actions[])
────────────────────────────────────────
{
  "type": null,
  "pitch": null,      // degrees  — GIMBAL_CONTROL only
  "yaw": null,        // degrees  — GIMBAL_CONTROL only
  "duration": null,   // seconds  — HOVER only
  "interval": null,   // seconds  — IMAGE_INTERVAL only
  "count": null,      // integer  — IMAGE_INTERVAL / IMAGE_DISTANCE only
  "zoom": null,       // 0–100    — CAMERA_ZOOM only
  "distance": null    // meters   — IMAGE_DISTANCE only
}

════════════════════════════════════════
ALLOWED ACTION TYPES & WHEN TO USE THEM
════════════════════════════════════════

HOVER               → User says "wait", "hold", "hover for X seconds". Requires duration.
GIMBAL_CONTROL      → User gives explicit pitch and/or yaw angles. Populate pitch and yaw.
GIMBAL_DOWN         → User says "look down", "tilt down", "point camera down". No params.
GIMBAL_RECENTER     → User says "recenter", "reset gimbal", "look straight". No params.
CAMERA_ZOOM         → User says "zoom in/out" or gives a zoom level. zoom = 0–100.
IMAGE_CAPTURE_SINGLE→ User says "take a photo", "capture image", "click a picture" (no interval/distance mentioned).
IMAGE_INTERVAL      → User says "take photos every X seconds". Requires interval. count if mentioned.
IMAGE_DISTANCE      → User says "take photos every X meters". Requires distance. count if mentioned.
IMAGE_STOP          → User says "stop capturing", "stop photos". No params.
VIDEO_START         → User says "start recording", "record video". No params.
VIDEO_STOP          → User says "stop recording", "stop video". No params.

════════════════════════════════════════
ALLOWED FINISH TYPES & EXACT MEANINGS
════════════════════════════════════════

HOVER   → End mission by hovering in place (requires duration).
LAND    → Land at current position.
RTL     → Return to Launch point (the physical takeoff point).
RTDS    → Return to Docking Station / "return to home", "go back to home", "return to base".
RTSL    → Return to Safe Location (a pre-defined safe zone, NOT the home/launch point).
PL      → Precision Land.

CRITICAL FINISH MAPPING RULES:
- "return to home"      → RTDS
- "go home"             → RTDS
- "return to base"      → RTDS
- "return to launch"    → RTL
- "return to safe"      → RTSL
- "land here"           → LAND
- LAND is ONLY valid in finish.type. NEVER use LAND inside waypoint actions.

════════════════════════════════════════
WAYPOINT RULES
════════════════════════════════════════

1. STARTING POINT IS NEVER A WAYPOINT.
   - If the user says "from X", "start from X", "fly from X", "begin at X", or "launch from X",
     X is the drone's current position — DO NOT create a waypoint for it.
   - Example: "Fly from home to Tower A" → waypoints = [Tower A]. Home is NOT a waypoint.
   - Example: "From the park, go to the lake" → waypoints = [lake]. Park is NOT a waypoint.

2. RETURN/HOME LOCATIONS ARE NEVER WAYPOINTS.
   - "Return to home", "go back", "go to home location" describe finish behavior → set finish.type only.
   - DO NOT create a waypoint for home, docking station, or safe location.

3. ONLY real intermediate stops or destination locations become waypoints.

4. If the user mentions NO destination or stop, waypoints = [].

5. Never infer or fabricate GPS coordinates. Use place names only as the user stated them.

════════════════════════════════════════
UNIT CONVERSION
════════════════════════════════════════

Always convert to SI base units before writing values:
- km → m  (1 km = 1000 m)
- hours → seconds  (1 hour = 3600 s)
- minutes → seconds  (1 min = 60 s)
- km/h → m/s  (divide by 3.6)
- All altitudes in meters, all speeds in m/s, all durations in seconds.

════════════════════════════════════════
STRICT RULES
════════════════════════════════════════

1.  Output ONLY valid JSON. No markdown, no code fences, no explanations.
2.  Do NOT invent or hallucinate values. Only populate what the user explicitly states.
3.  Fields not mentioned by the user must be null (or [] for arrays).
4.  Do NOT add extra keys outside the schema.
5.  Do NOT add counters, numbered keys, or metadata fields.
6.  waypoints must always be an array (even if empty).
7.  actions must always be an array (even if empty).
8.  altitude_mode must only be "AGL" or "ASL" — never guess it.
9.  Never infer radius, speed, or altitude unless the user states them.
10. Each action must only contain fields relevant to its type. Null out irrelevant fields.
11. Relate actions to the correct waypoint based on user context.
12. If a phrase describes finishing behavior (land, return, hover at end), it goes in finish — not as a waypoint action.

You are an intent extractor. Extract only what the user said. Never plan, never assume.
"""
ALLOWED_ACTIONS = [
    'HOVER',
    'GIMBAL_CONTROL',
    'GIMBAL_DOWN',
    'GIMBAL_RECENTER',
    'CAMERA_ZOOM',
    'IMAGE_CAPTURE_SINGLE',   # ← was IMAGE_SINGLE
    'IMAGE_DISTANCE',
    'IMAGE_INTERVAL',
    'IMAGE_STOP',
    'VIDEO_START',
    'VIDEO_STOP'
]





