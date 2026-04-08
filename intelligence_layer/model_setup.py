from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from .intelligence_schema import Waypoint,MissionPlan
import os
from dotenv import load_dotenv
from intent_understanding.location_resolver import LocationResolver
from .graphdb_validator import GraphValidator
from .parameter_model_setup import optimize_parameters
load_dotenv()
org_id,site_id,user_id=1,1,1
validated=dict()
validated["org_id"]=1
validated["site_id"]=1
validated["user_id"]=1
resolver = LocationResolver()
data = resolver.resolve(1,1,1)
# ------------------ Model ------------------

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=os.getenv("OPENAI_API_KEY")
)

structured_llm = llm.with_structured_output(MissionPlan)

# ------------------ Prompt ------------------

prompt = ChatPromptTemplate.from_messages([
    ("system", f"""
You are an intent extraction engine for drone missions.

STRICT RULES:
1. Extract waypoints in order.
2.Location Extraction Rule:
- You are given a fixed list of valid location names: {data}
- If the user provides a location (even with typos, partial words, or incorrect casing), you MUST match it to the closest valid location from this list.
- The output location MUST exactly match one of the names from the list.
- Do NOT return the user’s incorrect spelling.
- Do NOT invent new location names.
- If no reasonable match is found, set location to null.
3. Each waypoint must have:
   - location
4.Allowed action types:
    HOVER, GIMBAL_CONTROL,GIMBAL_DOWN,GIMBAL_RECENTER,IMAGE_CAPTURE_SINGLE,IMAGE_DISTANCE,IMAGE_INTERVAL,IMAGE_STOP,VIDEO_START,VIDEO_STOP
5. Output must strictly follow JSON schema.
"""),
    ("user", "{input}")
])

# ------------------ Chain ------------------

chain = prompt | structured_llm

# ------------------ Function ------------------

def extract_intent(user_prompt: str):
    return chain.invoke({"input": user_prompt})

# ------------------ Test ------------------
def add_to_json(validated):
    result = extract_intent(validated["prompt"])
    waypoints_array = [
        {
            "location": wp.location,
            "action": wp.action
        }
        for wp in result.waypoints
    ]
    validated["result"]=waypoints_array
    
    
    validator = GraphValidator(uri="bolt://localhost:7687",
        user="neo4j",
        password=os.getenv("NEO4J_PASSWORD"))
    validated["graphdb_data"] = [{} for _ in range(len(validated["result"]))]
    for i in range(len(validated["result"])):

         validated["graphdb_data"][i]["location"]= validated["result"][i]
         validated["graphdb_data"][i]["value"]=validator.validate_location(user_id=validated["user_id"], location=validated["result"][i]["location"])
    return validated


# if __name__ == "__main__":
#     user_input = "fly to pallet, take photo, then go to dock"
#     validated["prompt"]=user_input

#     validated = add_to_json(validated)
#     validated = optimize_parameters(validated)
#     print(validated)