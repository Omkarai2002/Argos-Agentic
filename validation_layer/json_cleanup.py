import json
from dataclasses import dataclass
from typing import Dict
from jsons import (ACTIONS,
                   TEMPLATE,
                   WAYPOINT,
                   CHAIN)

@dataclass
class EnterDataToJSON:
    
    def parse_json(self, chain, extracted_json):

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

            extracted_json.setdefault("waypoints", [])
            
            for i, wp in enumerate(waypoints):
                temp_dict = {}
                temp_act=[]
                temp_dict["sequence"] = i + 1
                temp_dict["location"] = wp.get("name")
                temp_dict["altitude"] = wp.get("altitude")
                temp_dict["altitude_mode"] = wp.get("altitude_mode")
                temp_dict["speed"] = wp.get("speed")
                temp_dict["radius"]= wp.get("radius")
                actions=wp.get("actions")
                for i, act in enumerate(actions):

                    if not isinstance(act, dict):
                        continue

                    temp_dict_act = {}

                    temp_dict_act["sequence"] = i + 1
                    temp_dict_act["type"] = act.get("type")

                    # CREATE params FIRST
                    temp_dict_act["params"] = {}

                    temp_dict_act["params"]["pitch"] = act.get("pitch")
                    temp_dict_act["params"]["yaw"] = act.get("yaw")
                    temp_dict_act["params"]["duration"] = act.get("duration")
                    temp_dict_act["params"]["interval"] = act.get("interval")
                    temp_dict_act["params"]["count"] = act.get("count")
                    temp_dict_act["params"]["zoom"] = act.get("zoom")
                    temp_dict_act["params"]["distance"] = act.get("distance")

                    temp_act.append(temp_dict_act)
        
                temp_dict["actions"] = temp_act
                extracted_json["waypoints"].append(temp_dict)

        return extracted_json

# extracted_json=TEMPLATE
# j=EnterDataToJSON()
# print(j.parse_json(CHAIN,extracted_json))
    



