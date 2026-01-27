import os
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
}}
"""





