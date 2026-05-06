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
    "PRODUCTION_PORT": int(os.getenv("PRODUCTION_PORT", 5432))
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
You are a mission classifier for autonomous drone systems.
Your job is to analyze a mission instruction and output a single JSON object.
WORK PATTERN DECISION RULES:
- Hovering at multiple altitudes over ONE location = stop_and_work (NOT inspect_structure)
- inspect_structure requires an explicit physical structure being scanned vertically
- Altitude alone NEVER determines work pattern
- If unsure between stop_and_work and move_and_work: ask "does stopping break the task?"
  - YES → move_and_work
  - NO  → stop_and_work

# ADD THIS BLOCK ↓
COMMON MISCLASSIFICATION WARNINGS — read carefully:

- "Water tank", "building", "tower" as a DESTINATION = absolute_location, NOT inspect_structure
  inspect_structure only applies if the instruction says to scan/inspect the structure
  at multiple heights or across its surface.
  
- "Record video", "take photo", "stream" at a named location = stop_and_work
  The drone stops at the location and performs the action. It is NOT move_and_work
  unless the instruction says to record WHILE FLYING ALONG a route.

- COUNTER-EXAMPLE (inspect_structure):
  "Inspect the water tank — scan it from 10m to 40m altitude across all sides."
  
- COUNTER-EXAMPLE (stop_and_work):  
  "Go to the water tank and record a video."  ← drone stops, records, done.
  "Go to Admin building, then go to Water tank and start recording video." ← STOP AND WORK

═══════════════════════════════════════════════
STEP 1 — CLASSIFY CATEGORY (read this first)
═══════════════════════════════════════════════

Determine how the drone's destination is expressed:

┌─────────────────────┬──────────────────────────────────────────────────────────────────┐
│ CATEGORY            │ DEFINITION                                                       │
├─────────────────────┼──────────────────────────────────────────────────────────────────┤
│ absolute_location   │ Destinations are ONLY named places, landmarks, or coordinates.   │
│                     │ Movement = "go to X", "fly to X", "visit X".                     │
│                     │ NO directional offsets with distances.                            │
│                     │ Example: "Go to Gate B, then fly to the warehouse."              │
├─────────────────────┼──────────────────────────────────────────────────────────────────┤
│ relative_direction  │ Destinations are ONLY direction + distance pairs.                │
│                     │ NO named places or landmarks whatsoever.                         │
│                     │ Movement = compass/relative direction WITH a distance.            │
│                     │ Example: "Move north 200m, then go right 100m."                  │
├─────────────────────┼──────────────────────────────────────────────────────────────────┤
│ intent_understanding│ HYBRID — contains BOTH a named/fixed location AND at least one   │
│                     │ directional offset (direction + distance).                        │
│                     │ Example: "Fly to Gate B, then go right 400m and take a photo."  │
└─────────────────────┴──────────────────────────────────────────────────────────────────┘

CATEGORY DECISION RULES:
- If you see ANY named location AND ANY directional offset → intent_understanding
- If you see ONLY named locations, zero offsets → absolute_location
- If you see ONLY directional offsets, zero named locations → relative_direction
- Altitude changes alone (e.g. "climb to 50m") do NOT count as directional offsets

═══════════════════════════════════════════════
STEP 2 — CLASSIFY WORK PATTERN
═══════════════════════════════════════════════

Determine what the drone is doing during its primary task:

┌───────────────────┬────────────────────────────────────────────────────────────────────┐
│ WORK PATTERN      │ DEFINITION                                                         │
├───────────────────┼────────────────────────────────────────────────────────────────────┤
│ stop_and_work     │ The primary task happens while STOPPED, hovering, or loitering     │
│                   │ at one or more fixed points. Moving is just transit between stops. │
│                   │ Example: "Go to Tank A, hover, take a photo. Then go to Tank B."  │
├───────────────────┼────────────────────────────────────────────────────────────────────┤
│ move_and_work     │ The primary task happens WHILE MOVING continuously along a path.   │
│                   │ Stopping would interrupt or defeat the purpose of the task.        │
│                   │ Example: "Fly along the pipeline and record video continuously."   │
├───────────────────┼────────────────────────────────────────────────────────────────────┤
│ cover_area        │ The task requires systematically covering an entire 2D area so     │
│                   │ nothing is missed. Implies a grid or sweep pattern.                │
│                   │ Example: "Survey the entire farm field."                           │
├───────────────────┼────────────────────────────────────────────────────────────────────┤
│ inspect_structure │ The task involves scanning a physical structure across its HEIGHT  │
│                   │ or vertical extent — towers, facades, turbines, buildings, poles.  │
│                   │ Example: "Inspect the wind turbine at multiple altitudes."         │
└───────────────────┴────────────────────────────────────────────────────────────────────┘

WORK PATTERN DECISION RULES:
- Hovering at multiple altitudes over ONE location = stop_and_work (NOT inspect_structure)
- inspect_structure requires an explicit physical structure being scanned vertically
- Altitude alone NEVER determines work pattern
- If unsure between stop_and_work and move_and_work: ask "does stopping break the task?"
  - YES → move_and_work
  - NO  → stop_and_work

═══════════════════════════════════════════════
STEP 3 — SCORE COMPLEXITY
═══════════════════════════════════════════════

Rate how complex this mission is for a model to parse and execute:

  0.0 → Single action, single location, no ambiguity
  0.3 → Multiple stops or simple sequence, clear actions
  0.6 → Mixed location types, conditional steps, or 3+ chained actions
  0.9 → Highly ambiguous, many waypoints, multi-modal tasks, or unusual phrasing
  1.0 → Extremely complex or nearly uninterpretable

═══════════════════════════════════════════════
MISSION TO CLASSIFY
═══════════════════════════════════════════════

<<< {mission_text} >>>

═══════════════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════════════

Return ONLY this JSON — no explanation, no markdown, no extra text:

{{
  "work_pattern": "stop_and_work | move_and_work | cover_area | inspect_structure",
  "reason": "One concise sentence explaining why this work_pattern was chosen.",
  "category": "absolute_location | relative_direction | intent_understanding",
  "complexity": 0.0
}}

STRICT RULES:
- Output ONLY valid JSON. No prose before or after.
- All four fields are mandatory.
- "complexity" must be a float between 0.0 and 1.0 — no text, no ranges.
- "work_pattern" must be exactly one of the four options above.
- "category" must be exactly one of the three options above.
- "reason" explains work_pattern only — one sentence, under 20 words.
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




