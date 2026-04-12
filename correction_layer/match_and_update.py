def match_update(validated,optimized):

    waypoints=validated["model_for_extraction_json_output"]["waypoints"]
    for i in range(len(waypoints)):
        speed=optimized[i].get("speed",4)
        if not validated["model_for_extraction_json_output"]["waypoints"][i]["speed"]:
            validated["model_for_extraction_json_output"]["waypoints"][i]["speed"]=speed
        altitude=optimized[i].get("altitude",4)
        if not validated["model_for_extraction_json_output"]["waypoints"][i]["altitude"]:
            validated["model_for_extraction_json_output"]["waypoints"][i]["altitude"]=altitude
        altitude_mode=optimized[i].get("altitude_mode",'AGL')
        if not validated["model_for_extraction_json_output"]["waypoints"][i]["altitude_mode"]:
            validated["model_for_extraction_json_output"]["waypoints"][i]["altitude_mode"]=altitude_mode
        actions=validated["model_for_extraction_json_output"]["waypoints"][i]["actions"]
        for j in range(len(actions)):
            action_type=validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["type"]
            action_duration=validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["duration"]
            action_pitch=validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["pitch"]
            action_yaw=validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["yaw"]
            action__interval=validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["interval"]
            action_count=validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["zoom"]
            action_distance=validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["distance"]

            for k in range(len(optimized[i].get("action"))):
                optimized_action_type=optimized[i]["action"][k]["type"]
                optimized_action_duration=optimized[i]["action"][k]["params"].get("duration",0)
                optimized_action_pitch=optimized[i]["action"][k]["params"].get("pitch",0)
                optimized_action_yaw=optimized[i]["action"][k]["params"].get("yaw",0)
                optimized_action_interval=optimized[i]["action"][k]["params"].get("interval",0)
                optimized_action_count=optimized[i]["action"][k]["params"].get("count",0)
                optimized_action_distance=optimized[i]["action"][k]["params"].get("distance",0)
                optimized_action_zoom=optimized[i]["action"][k]["params"].get("zoom",0)

                if action_type==optimized_action_type and action_type=="HOVER" and not action_duration:
                    validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["duration"]=optimized_action_duration

                if action_type==optimized_action_type and action_type=="GIMBAL_CONTROL" and not (optimized_action_pitch or optimized_action_yaw):
                    validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["pitch"]=optimized_action_pitch
                    validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["yaw"]=optimized_action_yaw

                if action_type==optimized_action_type and action_type=="CAMERA_ZOOM" and not optimized_action_zoom:
                    validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["zoom"]=optimized_action_zoom

                if action_type==optimized_action_type and action_type=="IMAGE_CAPTURE_SINGLE" and not (optimized_action_interval or optimized_action_count):
                    validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["interval"]=optimized_action_interval
                    validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["count"]=optimized_action_count

                if action_type==optimized_action_type and action_type=="IMAGE_DISTANCE" and not optimized_action_distance:
                    validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["distance"]=optimized_action_distance
                
                if action_type==optimized_action_type and action_type=="IMAGE_INTERVAL" and not optimized_action_interval:
                    validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["interval"]=optimized_action_interval
                
        
    return validated