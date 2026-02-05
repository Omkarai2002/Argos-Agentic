from dataclasses import dataclass
from mission_classifier_layer.classifier import Classifier,FillJson
from typing import Dict
from app.config import (SMALL_MODEL,
                        MEDIUM_MODEL,
                        LARGE_MODEL,
                        XLARGE_MODEL,
                        COMPLEXITY_THRESHOLD_FOR_POINT_MISSION,
                        COMPLEXITY_THRESHOLD_FOR_PATH_MISSION,
                        COMPLEXITY_THRESHOLD_FOR_GRID_MISSION,
                        COMPLEXITY_THRESHOLD_FOR_3D_MISSION)
@dataclass
class Selection:
    validated :Dict
    data :Dict


    def select_model(self)->Dict:
        json_data=FillJson(self.validated)
        validated=json_data.append_data_to_json()
        complexity=validated["complexity"]
        if validated["class"]=="point":
            if complexity<=COMPLEXITY_THRESHOLD_FOR_POINT_MISSION:
                validated["model_for_extraction"]=SMALL_MODEL
            else:
                validated["model_for_extraction"]=MEDIUM_MODEL

        if validated["class"]=="path":
            if complexity<=COMPLEXITY_THRESHOLD_FOR_PATH_MISSION:
                validated["model_for_extraction"]=SMALL_MODEL
            else:
                validated["model_for_extraction"]=MEDIUM_MODEL

        if validated["class"]=="grid":
            if complexity<=COMPLEXITY_THRESHOLD_FOR_GRID_MISSION:
                validated["model_for_extraction"]=SMALL_MODEL
            else:
                validated["model_for_extraction"]=MEDIUM_MODEL

        if validated["class"]=="3d":
            if complexity<=COMPLEXITY_THRESHOLD_FOR_3D_MISSION:
                validated["model_for_extraction"]=SMALL_MODEL
            else:
                validated["model_for_extraction"]=MEDIUM_MODEL
        return validated
# data ={
#         "user_id":1,
#         "site_id":1,
#         "org_id":1,
#         "prompt" :"Plan a grid-based area coverage mission over a 500 m × 400 m agricultural field near the dock with 70% front overlap and 60% side overlap at 60 m altitude for multispectral mapping."
#     }
# validated={
#         "db_record_id":int,
#         "user_id":data["user_id"],
#         "site_id":data["site_id"],
#         "org_id":data["org_id"],
#         "prompt":data["prompt"],
#         "class":"",
#         "reason":"",
#         "model_for_extraction":""
#     }
# c=Selection(validated,data)
# print(c.select_model())



    



