from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from .intelligence_schema import Waypoint,MissionPlan
import os
from dotenv import load_dotenv
from intent_understanding.location_resolver import LocationResolver
from .graphdb_validator import GraphValidator
from .parameter_model_setup import optimize_parameters
load_dotenv()
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=os.getenv("OPENAI_API_KEY")
)

structured_llm = llm.with_structured_output(MissionPlan)
def extract_intent(user_prompt: str, org_id, site_id, user_id):
    
    resolver = LocationResolver()
    data = resolver.resolve(org_id, site_id, user_id)

    prompt = ChatPromptTemplate.from_messages([
        ("system", f"""
You are an intent extraction engine for drone missions.

STRICT RULES:
1. Extract waypoints in order.
2. Location Extraction Rule:
- Valid locations: {data}
- Always map user input to closest valid location
- Do not invent names
- Return null if no match
3. Each waypoint must have:
   - location
4. Allowed action types:
   HOVER, GIMBAL_CONTROL, GIMBAL_DOWN, GIMBAL_RECENTER,
   IMAGE_CAPTURE_SINGLE, IMAGE_DISTANCE, IMAGE_INTERVAL,
   IMAGE_STOP, VIDEO_START, VIDEO_STOP
5. Output must strictly follow JSON schema.
"""),
        ("user", "{input}")
    ])

    chain = prompt | structured_llm
    return chain.invoke({"input": user_prompt})

# ------------------ Test ------------------
def add_to_json(validated):
    result = extract_intent(
        validated["prompt"],
        validated["org_id"],
        validated["site_id"],
        validated["user_id"]
    )
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