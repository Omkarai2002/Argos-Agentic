import os
import json
import dotenv
dotenv.load_dotenv()

PROMPT_COMPLETION_DATABASE_CONFIG = {
    "DB_NAME": os.getenv("DB_NAME"),
    "DB_USER": os.getenv("DB_USER"),
    "DB_PASSWORD": os.getenv("DB_PASSWORD"),
    "DB_HOST": os.getenv("DB_HOST"),
    "DB_PORT": int(os.getenv("DB_PORT"))
}
MAX_TOKEN_LIMIT_FOR_PROMPT_COMPLETION = 8192
MIN_TOKEN_LIMIT_FOR_PROMPT_COMPLETION = 10
MODEL_NAME_FOR_PROMPT_COMPLETION = "gpt-4o-mini"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TEMPERATURE_FOR_PROMPT_COMPLETION = 0.3
MODEL_FOR_EMBEDDING = "text-embedding-3-large"
MODEL_FOR_CLASSIFICATION ="gpt-5-nano"
TEMPERATURE_FOR_CLASSIFICATION=0
SMALL_MODEL="gpt-5-nano"
MEDIUM_MODEL="gpt-4o-mini"
LARGE_MODEL="gpt-4o"
XLARGE_MODEL="gpt-4.1"
COMPLEXITY_THRESHOLD_FOR_POINT_MISSION=0.8
COMPLEXITY_THRESHOLD_FOR_PATH_MISSION=0.8
COMPLEXITY_THRESHOLD_FOR_GRID_MISSION=0.8
COMPLEXITY_THRESHOLD_FOR_3D_MISSION=0.8
TEMPERATURE_FOR_JSON_EXTRACTION=0
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

Rules:
- Altitude alone does NOT imply inspect_structure.
- Hovering at one or more altitudes is still stop_and_work unless a structure
  is being inspected.
- Do NOT infer execution type (point/path/grid/3d).
- Return ONLY valid JSON.

Mission:
<<< {mission_text} >>>

JSON:
{{
  "work_pattern": "stop_and_work | move_and_work | cover_area | inspect_structure",
  "reason": "one short sentence"
  "complexity":"enter the complexity score between 0 to 1 over here ,the more complex or more action based the prompt--> {mission_text} is like long heavy to understand by the model more should be the confidence threshold "
}}
"""

JSON_EXTRACTION_PROMPT = JSON_EXTRACTION_PROMPT = """
You are a deterministic drone-mission JSON compiler.

Your task:
Convert the user’s natural language request into the EXACT mission JSON schema provided below.

You MUST always output the FULL JSON object.

You MUST ONLY populate fields that are EXPLICITLY mentioned by the user.
ALL other fields MUST be null (or empty arrays where applicable).

You are NOT allowed to:
- Guess values
- Infer defaults
- Invent coordinates
- Add actions not explicitly requested
- Assume behaviors

STRICT RULES:

1. Output VALID JSON ONLY.
2. Response MUST start with '{' and end with '}'.
3. Do NOT include explanations, markdown, or comments.
4. Do NOT hallucinate values.
5. If a value is not directly stated by the user, set it to null.
6. Arrays must always be present (even if empty).
7. Numbers must be numeric, not strings.
8. Never infer GPS coordinates.
9. Never invent waypoints.
10. Never invent actions.
11. Never invent finish_action.
12. If grid / area coverage is explicitly mentioned, set:
    mission_config.mode = "grid"
13. If dimensions are explicitly mentioned, set:
    mission_config.field_size = [width, height]
14. If overlaps are explicitly mentioned, set:
    mission_config.front_overlap
    mission_config.side_overlap
15. If altitude is explicitly mentioned (and not tied to waypoint), set:
    mission_config.altitude
16. If multispectral is mentioned, keep camera_profile but leave values null unless explicitly stated.
17. If gimbal / video / capture is mentioned, create ONLY those actions.
18. If something is unclear, set it to null.
19. Never remove keys.
20. Never add extra keys.

WAYPOINT RULES:

- If the user does NOT explicitly specify waypoints, return "waypoints": [].
- Do NOT invent waypoint coordinates.
- Each waypoint must contain:
  sequence, location, altitude, altitude_mode, speed, radius, actions
- Each action must contain:
  sequence, type, params { pitch, yaw, duration }

MISSION JSON SCHEMA (ALWAYS RETURN THIS EXACT STRUCTURE):

{
  "finish_action": {
    "type": null,
    "duration": null
  },

  "waypoints": [],

  "takeoff_config": {
    "altitude": null,
    "altitude_mode": null,
    "speed": null
  },

  "route_config": {
    "altitude": null,
    "altitude_mode": null,
    "speed": null,
    "radius": null
  },

  "mission_config": {
    "mode": null,
    "field_size": null,
    "front_overlap": null,
    "side_overlap": null,
    "altitude": null,

    "camera_profile": {
      "pitch": null,
      "yaw_mode": null,
      "poi": null
    },

    "limits": {
      "max_vertical_speed": null,
      "layer_spacing": null
    }
  },

  "dock_id": null,
  "can_select_dock": true,
  "is_hidden": false,
  "is_private": false
}

Remember:
Populate ONLY what the user explicitly provides.
Everything else stays null or empty.

Return ONLY the JSON.
"""







