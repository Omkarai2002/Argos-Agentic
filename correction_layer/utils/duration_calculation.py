import math

def total_time_calculation(validated):
    #s=d/t
    distance=validated["model_for_extraction_json_output"]["total_distance"]
    time=0
    speed=0
    if validated["model_for_extraction_json_output"]["finish_action"]["type"]=="HOVER":
        if validated["model_for_extraction_json_output"]["finish_action"]["duration"]:
            time=time + validated["model_for_extraction_json_output"]["finish_action"]["duration"]

    for i in range(len(validated["model_for_extraction_json_output"]["waypoints"])):
        print(validated["model_for_extraction_json_output"]["waypoints"])
        if validated["model_for_extraction_json_output"]["waypoints"][i]["speed"]:
                speed=speed+validated["model_for_extraction_json_output"]["waypoints"][i]["speed"]

        for j in range(len(validated["model_for_extraction_json_output"]["waypoints"][i]["actions"])):
            if validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["type"]=="HOVER":
                if validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["duration"]:
                    time=time+validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["duration"]
            
    if validated["model_for_extraction_json_output"]["takeoff_config"]["speed"]:
         speed=speed+validated["model_for_extraction_json_output"]["takeoff_config"]["speed"]
    
    return (distance/speed)
         







