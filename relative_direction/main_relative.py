import json
from .graph import build_app
from .gps_calculator import GpsCalculationRelative
from validation_layer import (
    EnterDataToJSON,Template)
from jsons import (TEMPLATE)
from correction_layer import (ConnectToDb, GeofenceValidator, CheckThreshold)
import copy
from graphdb import Neo4jMissionDB
from mission_classifier_layer.model_selection import Selection
def run_pipeline_relative(user_input: str):
    app = build_app()

    result = app.invoke({
        "input": user_input,
        "retries": 0,
        "result": None,
        "error": None
    })

    if result["result"] is not None:
        
        return result["result"].dict()
    else:
        return {
            "waypoints": [],
            "finish": None
        }


# if __name__ == "__main__":

#     prompt = "Move in 25 degrees 200 meters then north south 20 meters and take a photo"
#     validated=dict()
#     validated["user_id"]=1
#     validated["org_id"]=1
#     validated["site_id"]=1
#     validated["prompt"]=prompt
#     validated["dock_coordinates"] = {
#         "lat": 19.95868,
#         "lon": 73.75717
#     }
#     data=dict()
#     data["user_id"]=1
#     data["org_id"]=1
#     data["site_id"]=1
#     data["prompt"]=prompt
#     model_select = Selection(validated, data)
#     validated = model_select.select_model()
#     pipeline_output = run_pipeline_relative(prompt)
#     print("pipeline_ouput",pipeline_output)
#     validated["model_for_extraction_json_output"] = pipeline_output.copy()
#     print("validated_first:",validated)
#     validated["category"]="relative_direction"
#     gps = GpsCalculation()
#     validated = gps.indivisual_waypoint_gps_fetch(validated)
#     print("validated_geofence:",validated)
#     output_from_json=EnterDataToJSON()
#     extracted_json = copy.deepcopy(TEMPLATE)
#     validated["model_for_extraction_json_output"] =output_from_json.parse_json(validated, extracted_json)
#     validator = GeofenceValidator()
#     validated = validator.validate(validated)
#     # threshold = CheckThreshold(validated)
#     # validated = threshold.check_waypoints()
#     # graphdb = Neo4jMissionDB()
#     # graphdb.initialize()
#     # graphdb.insert_mission(validated)
#     print(json.dumps(validated, indent=2))