import json
from dataclasses import dataclass
from typing import Dict
from jsons import (ACTIONS,
                   TEMPLATE,
                   WAYPOINT,
                   CHAIN)
import copy
@dataclass
class EnterDataToJSON:
    
    def parse_json(self, chain, extracted_json:Dict)->Dict:

        # finish
        finish = chain.get("finish")
        if finish and finish.get("type"):
            extracted_json["finish_action"] = finish

        # takeoff
        takeoff = chain.get("takeoff")
        if takeoff:
            extracted_json.setdefault("takeoff_config", {})
            extracted_json["takeoff_config"]["altitude"] = takeoff.get("altitude")
            extracted_json["takeoff_config"]["altitude_mode"] = takeoff.get("mode")
            extracted_json["takeoff_config"]["speed"] = takeoff.get("speed")

        # camera
        camera = chain.get("camera")
        if camera:
            extracted_json["camera_profile"] = camera

        # waypoints
        waypoints = chain.get("waypoints", [])

        if waypoints:
                
            # extracted_json.setdefault("waypoints", [])
            
            extracted_json["waypoints"] = []   # hard reset

            for i, wp in enumerate(waypoints):
                temp_dict = {}
                temp_act=[]
                temp_dict["sequence"] = i + 1
                temp_dict["location"] = wp.get("name")
                altitude = wp.get("altitude")
                temp_dict["altitude"] = int(altitude) if altitude is not None else None
                altitude_mode=wp.get("altitude_mode")
                temp_dict["altitude_mode"] = int(altitude_mode) if altitude_mode is not None else None
                speed = wp.get("speed")
                temp_dict["speed"] = float(speed) if speed is not None else None
                radius = wp.get("radius")
                temp_dict["radius"] = float(radius) if radius is not None else None

                actions=wp.get("actions")
                for i, act in enumerate(actions):

                    if not isinstance(act, dict):
                        continue

                    temp_dict_act = {}

                    temp_dict_act["sequence"] = i + 1
                    temp_dict_act["type"] = str(act.get("type"))

                    # CREATE params FIRST
                    temp_dict_act["params"] = {}

                    temp_dict_act["params"]["pitch"] = float(act.get("pitch")) if act.get("pitch") else None
                    temp_dict_act["params"]["yaw"] = str(act.get("yaw")) if act.get("yaw") else None
                    temp_dict_act["params"]["duration"] = int(act.get("duration")) if act.get("duration") else None
                    temp_dict_act["params"]["interval"] = int(act.get("interval")) if act.get("interval") else None
                    temp_dict_act["params"]["count"] = int(act.get("count")) if act.get("count") else None
                    temp_dict_act["params"]["zoom"] = float(act.get("zoom")) if act.get("zoom") else None
                    temp_dict_act["params"]["distance"] = float(act.get("distance")) if act.get("distance") else None

                    temp_act.append(temp_dict_act)
        
                temp_dict["actions"] = temp_act
                extracted_json["waypoints"].append(temp_dict)

        return extracted_json

# extracted_json=TEMPLATE
# j=EnterDataToJSON()
# print(j.parse_json(CHAIN,extracted_json))
    



