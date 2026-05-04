from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from typing import Dict
from app.config import OPENAI_API_KEY, TEMPERATURE_FOR_JSON_EXTRACTION, JSON_EXTRACTION_PROMPT
from mission_classifier_layer.model_selection import Selection
from jsons import (TEMPLATE)
from validation_layer import (
    EnterDataToJSON,Template)
from dataclasses import dataclass
from intent_understanding.location_resolver import LocationResolver
import copy
# data ={
#         "user_id":1,
#         "site_id":1,
#         "org_id":1,
#         "prompt" :"Fly to Pathardi Phata at 30 meters, tilt camera down 45 degrees, start video recording, hover for 10 seconds and land."
#     }
# validated={
#         "db_record_id":int,
#         "user_id":data["user_id"],
#         "site_id":data["site_id"],
#         "org_id":data["org_id"],
#         "prompt":data["prompt"],
#         "class":"",
#         "reason":"",
#         "model_for_extraction":"",
#         "model_for_extraction_json_output": Dict
#     }
# validate=Selection(validated,data)
# validated=validate.select_model()
output_from_json=EnterDataToJSON()
@dataclass
class PromptToJsonConvert:

    validated: dict

    def __post_init__(self):

        self.llm = ChatOpenAI(
            model=self.validated["model_for_extraction"],
            temperature=TEMPERATURE_FOR_JSON_EXTRACTION,
            api_key=OPENAI_API_KEY,
            # model_kwargs={
            #     "reasoning":{
            #         "effort":"low"
            #     }
            # }
        )

        self.parser = JsonOutputParser()

    def convert(self) -> Dict:
        org_id=self.validated["org_id"]
        site_id=self.validated["site_id"]
        user_id=self.validated["user_id"]
        resolver = LocationResolver()
        data = resolver.resolve(site_id, user_id,org_id)
        print("data_from_db:",data)
        messages = [
    SystemMessage(content=f"""
You are a strict drone-mission intent extraction engine.
Your ONLY job is to convert natural language drone instructions into structured JSON.

════════════════════════════════════════
OUTPUT SCHEMA
════════════════════════════════════════

{{
  "finish": {{
    "type": null,        // See FINISH TYPES below
    "duration": null     // seconds, only for HOVER finish
  }},
  "takeoff": {{
    "altitude": null,    // meters
    "mode": null,
    "speed": null        // m/s
  }},
  "camera": {{
    "pitch": null,       // degrees
    "yaw_mode": null,
    "poi": null          // place name only if explicitly mentioned
  }},
  "waypoints": []
}}

────────────────────────────────────────
WAYPOINT SCHEMA (each item in waypoints[])
────────────────────────────────────────
{{
  "name": null,           // place name only if user explicitly mentions it
  "altitude": null,       // meters
  "altitude_mode": null,  // "AGL" or "ASL" only
  "speed": null,          // m/s
  "radius": null,         // meters
  "actions": []
}}

────────────────────────────────────────
ACTION SCHEMA (each item in actions[])
────────────────────────────────────────
{{
  "type": null,
  "pitch": null,      // degrees  — GIMBAL_CONTROL only
  "yaw": null,        // degrees  — GIMBAL_CONTROL only
  "duration": null,   // seconds  — HOVER only
  "interval": null,   // seconds  — IMAGE_INTERVAL only
  "count": null,      // integer  — IMAGE_INTERVAL / IMAGE_DISTANCE only
  "zoom": null,       // 0–100    — CAMERA_ZOOM only
  "distance": null    // meters   — IMAGE_DISTANCE only
}}

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
═══════════════════════════════════════
                  ════════════════════════════════════════
LOCATION INTELLIGENCE & WAYPOINT RULES
════════════════════════════════════════
- Valid location names are restricted to this list: {data},If the user gives the location explicitly ,try considering from this locations or using intent try finding the location on its basis.

────────────────────────────────────────
STEP 1 — UNDERSTAND THE QUANTITY INTENT
────────────────────────────────────────

Before extracting waypoints, first determine HOW MANY locations the user wants:

- "fly to every location" / "visit all locations" / "cover all points" / "go to each location"
  → Use ALL locations from the list as waypoints, in the exact order they appear in the list.

- "fly to any 3 locations" / "pick 3 waypoints" / "choose 3 places" / "random 3 stops"
  → Pick exactly 3 locations from the list. If the user gives context clues (e.g., "near the pump"),
    prefer locations whose names best match that context. If no context, pick the first N from the list.

- "first 3 locations" / "top 3 waypoints"
  → Pick the first 3 from the list in order.

- "last 3 locations"
  → Pick the last 3 from the list in order.

- "fly to Tower A and the pump area and the gate"
  → Specific named locations — match each one individually (see STEP 2).

- No quantity mentioned, just a destination
  → Extract only the locations the user explicitly mentioned.

────────────────────────────────────────
STEP 2 — MATCH EACH LOCATION INTELLIGENTLY
────────────────────────────────────────

When the user refers to a location, match it to the best entry in the available list using this priority:

PRIORITY 1 — EXACT MATCH:
  User says "Pump House" → match "Pump House" exactly.

PRIORITY 2 — PARTIAL / ABBREVIATED MATCH:
  User says "pump" or "pump area" or "the pump" → match "Pump House Area" or "Pump Station" from the list.
  User says "Area 3" → match "Sector Area 3" if it exists in the list.
  Casing and spacing differences are ignored.

PRIORITY 3 — KEYWORD / INTENT MATCH:
  User says "the tall structure" → match "Tower" or "Antenna" from the list based on semantic meaning.
  User says "entry point" → match "Main Gate" or "Entry Gate" from the list.
  User says "water storage" → match "Water Tank" or "Reservoir" from the list.

PRIORITY 4 — MULTIPLE CANDIDATES:
  If the user's description matches more than one location in the list
  (e.g., "fly to all areas" and the list has "Area 1", "Area 2", "Area 3"),
  create a waypoint for EVERY matching candidate in list order.

PRIORITY 5 — NO MATCH:
  If no location in the list matches even loosely, set "name": null.
  NEVER fabricate, guess, or use a location not in the available list.

────────────────────────────────────────
STEP 3 — WAYPOINT INCLUSION RULES
────────────────────────────────────────

RULE 1 — STARTING POINT IS NEVER A WAYPOINT:
  "from X", "start at X", "launch from X", "begin at X" → X is the drone's current position.
  Do NOT create a waypoint for it under any circumstances.

RULE 2 — HOME / RETURN LOCATIONS ARE NEVER WAYPOINTS:
  "return to home", "go back", "return to base", "go to docking station"
  → These describe finish behavior. Set finish.type only. Never create a waypoint for them.

RULE 3 — ONLY REAL INTERMEDIATE STOPS BECOME WAYPOINTS:
  A waypoint is a location the drone must physically fly to and stop at (even briefly).
  Passing references, origin points, and return destinations are never waypoints.

RULE 4 — PRESERVE ORDER:
  When multiple waypoints are extracted, their order in the output must match
  the order the user mentioned them (or list order for "all/every" cases).

RULE 5 — NO WAYPOINTS IF NONE MENTIONED:
  If the user gives no destination at all, waypoints = []. 


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
"""),
            HumanMessage(content=self.validated["prompt"])
        ]
        category=self.validated.get("category","")
        for attempt in range(1):
            result = self.llm.invoke(messages)
            chain = self.parser.invoke(result)
            extracted_json = copy.deepcopy(TEMPLATE)
            # Extract raw JSON text
            raw_output = result.content
            json_output=output_from_json.parse_json(chain, extracted_json)

            try:
                # Validate directly with Pydantic
                if Template.model_validate(json_output):
                    self.validated["model_for_extraction_json_output"] = \
                    output_from_json.parse_json(chain, extracted_json)

                    return self.validated

            except Exception as e:
                # Ask model to fix its own output
                messages.append(
                    HumanMessage(
                        content=f"""
    Fix this into valid JSON only.
    Do not add explanations.

    {raw_output}
    """
                    )
                )

                raise ValueError("LLM failed to produce valid structured output after 3 attempts.")





        
        


# mission_json = PromptToJsonConvert.convert(
#     validated["prompt"]
# )

# print(mission_json)
# mission_json=PromptToJsonConvert(validated)
# print(mission_json.convert())