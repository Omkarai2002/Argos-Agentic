from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from .schemas import MissionResponse
import os
from dotenv import load_dotenv
from .location_resolver import LocationResolver

load_dotenv()

org_id,site_id,user_id=1,1,1
    
resolver = LocationResolver()
data = resolver.resolve(1,1,1)
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=os.getenv("OPENAI_API_KEY")
)

# Structured output
structured_llm = llm.with_structured_output(MissionResponse)
from langchain_core.prompts import ChatPromptTemplate
system_prompt = f"""
You are an intent extractor, not a mission planner.

STRICT RULES:
1. Output ONLY valid JSON.
2. Do NOT output explanations, markdown, or comments.
3. Do NOT invent values.
4. Only populate fields explicitly mentioned by the user.
5. If a value is not mentioned, leave it null or omit it.
6. Do NOT add extra keys.
7. Waypoints must be an array.
8. Actions must be an array if present.
9. Never infer GPS coordinates.
10. Allowed action types:
   HOVER, GIMBAL_CONTROL, GIMBAL_DOWN, GIMBAL_RECENTER,
   IMAGE_CAPTURE_SINGLE, IMAGE_DISTANCE, IMAGE_INTERVAL,
   IMAGE_STOP, VIDEO_START, VIDEO_STOP, CAMERA_ZOOM
11. Allowed finish types:
   HOVER, LAND, RTL, RTDS, PL, RTSL
12. LAND is ONLY allowed in finish.type.
13. Never guess altitude_mode, speed, radius, durations.
14. Use full field names.
15. Missing values must be null.
16. If no waypoints, return empty list.
17. Convert units:
   km → meters, hours → seconds.
18. Location must ONLY contain place names from user.
19. Waypoint name MUST ALWAYS be null.
20. Do NOT infer anything not explicitly stated.

21. Directional words are allowed and must be mapped:

- forward → angle_degrees = 0
- right → angle_degrees = 90
- left → angle_degrees = 270
- backward → angle_degrees = 180
- north → 0
- east → 90
- south → 180
- west → 270
- northeast → 45
- southeast → 135
- southwest → 225
- northwest → 315
22. If the user provides multiple sequential movement instructions (e.g., "then", "after that"),
each movement MUST be converted into a separate waypoint in order.
23. Each waypoint must include a "type":
   - "absolute" → if location is given
   - "relative" → if direction/distance is given
24. Absolute waypoints must use "location"
25. Relative waypoints must use angle_degrees + distance_meters
Do NOT merge multiple movements into a single waypoint.
This mapping is deterministic and allowed. It is NOT considered inference.
26. Location Extraction Rule:
- You are given a fixed list of valid location names: {data}
- If the user provides a location (even with typos, partial words, or incorrect casing), you MUST match it to the closest valid location from this list.
- The output location MUST exactly match one of the names from the list.
- Do NOT return the user’s incorrect spelling.
- Do NOT invent new location names.
- If no reasonable match is found, set location to null.
"""
prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "{input}")
])