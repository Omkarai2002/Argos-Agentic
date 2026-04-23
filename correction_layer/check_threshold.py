from .geofence_validator import GeofenceValidator
from .db_manage import ConnectToDb
from .utils.distance_calculation import total_route_distance
from .utils.duration_calculation import total_time_calculation
class CheckThreshold:
    def __init__(self,validated):
        self.validated=validated
        self.geofence=GeofenceValidator()
        self.c = ConnectToDb()

    def parse_distance(self):
        gps_points = []

        waypoints = self.validated.get("model_for_extraction_json_output", {}).get("waypoints", [])

        for wp in waypoints:
            loc = wp.get("location")

            try:
                # Case 1: dict
                if isinstance(loc, dict):
                    lat = float(loc.get("lat"))
                    lon = float(loc.get("lon"))
                    gps_points.append((lat, lon))

                # Case 2: list/tuple
                elif isinstance(loc, (list, tuple)) and len(loc) >= 2:
                    lon = float(loc[0])
                    lat = float(loc[1])
                    gps_points.append((lat, lon))

                else:
                    continue

            except:
                continue

        return gps_points

    def check_waypoints(self):
        wayp=self.validated["model_for_extraction_json_output"]["waypoints"]
        finish_action = self.validated["model_for_extraction_json_output"]["finish_action"]

        action_type = finish_action.get("type")
        duration = finish_action.get("duration")

        if not action_type:  # empty or None
            finish_action["type"] = "RTDS"
            finish_action["duration"] = None

        elif action_type == "HOVER":
            if not duration:
                finish_action["duration"] = 20

        else:
            finish_action["duration"] = None
        
        self.validated["model_for_extraction_json_output"]["type"]=self.validated["class"]
        #TAKEOFF ALTITUDE CHECK
        try:
            takeoff_config_alt=self.validated["model_for_extraction_json_output"]["takeoff_config"].get("altitude",0)
            if not takeoff_config_alt or (takeoff_config_alt<=10):
                self.validated["model_for_extraction_json_output"]["takeoff_config"]["altitude"]=40
        except:
            self.validated["model_for_extraction_json_output"]["takeoff_config"]["altitude"]=40
                                                    
        #TAKEOFF SPEED CHECK
        try:
            takeoff_config_speed=self.validated["model_for_extraction_json_output"]["takeoff_config"].get("speed",0)
            if not self.validated["model_for_extraction_json_output"]["takeoff_config"]["altitude_mode"]:
                self.validated["model_for_extraction_json_output"]["takeoff_config"]["altitude_mode"]="REL"
            if not takeoff_config_speed or (takeoff_config_speed >=10 or takeoff_config_speed<=1) or type(takeoff_config_speed)!=int:
                self.validated["model_for_extraction_json_output"]["takeoff_config"]["speed"]=4
        except:
            self.validated["model_for_extraction_json_output"]["takeoff_config"]["speed"]=4
            self.validated["model_for_extraction_json_output"]["takeoff_config"]["altitude_mode"]="REL"
        #WAYPOINT CHECK 
        for i in range(len(wayp)):
            
            if self.validated["model_for_extraction_json_output"]["waypoints"][i]["location"] == []:

                return {
                    "status": "need_location",
                    "waypoint_index": i,
                    "message": f"Location missing for waypoint {i+1}. Please enter location name.",
                    "mission": self.validated
                }

            loc=self.validated["model_for_extraction_json_output"]["waypoints"][i]["location"]
            if not loc:
                new_loc=input(f"location not mentioned for waypoint {i+1},enter location name within geofence:")

            try:
                alt=self.validated["model_for_extraction_json_output"]["waypoints"][i]["altitude"]
                print("alt:",alt)
                if not alt or (alt<=10 or alt>=100):
                    self.validated["model_for_extraction_json_output"]["waypoints"][i]["altitude"]=40
                
            except:
                self.validated["model_for_extraction_json_output"]["waypoints"][i]["altitude"]=40
            if not self.validated["model_for_extraction_json_output"]["waypoints"][i]["altitude_mode"]:
                self.validated["model_for_extraction_json_output"]["waypoints"][i]["altitude_mode"]="REL"
            try:
                spd=self.validated["model_for_extraction_json_output"]["waypoints"][i]["speed"]
                if not spd or (spd<=1 or spd>=10):
                    self.validated["model_for_extraction_json_output"]["waypoints"][i]["speed"]=4

            except:
                  self.validated["model_for_extraction_json_output"]["waypoints"][i]["speed"]=4

            if self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"] :
                for j in range(len(self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"])):
                    if self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["type"]=="HOVER":
                        if not self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["duration"] or self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["duration"]>=100:
                            dur=10
                            self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["duration"]=dur

                    if self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["type"]=="GIMBAL_CONTROL":
                        
                        if not self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["pitch"]:
                            gc=180
                            self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["pitch"]=gc
                        if not self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["yaw"]:
                            gc=90
                            self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["yaw"]=gc

                    if self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["type"]=="CAMERA_ZOOM":
                        
                        if not self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["zoom"] or (self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["zoom"]<=0 or self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["zoom"]>=100) :           
                            self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["zoom"]=50   
                            self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["yaw"]=None
                            self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["pitch"]=None
                            self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["interval"]=None
                            self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["count"]=None      
                        else:
                            self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["yaw"]=None
                            self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["pitch"]=None
                            self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["interval"]=None
                            self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["count"]=None
                    if self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["type"]=="IMAGE_SINGLE":
                        self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["interval"]=0
                        self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["count"]=1
                        self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["zoom"]=None
                        self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["yaw"]=None
                        self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["pitch"]=None

                    if self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["type"]=="IMAGE_DISTANCE":
                        if not self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["distance"]:
                            self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["distance"]=2
                            self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["zoom"]=None
                            self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["yaw"]=None
                            self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["pitch"]=None
                            self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["interval"]=None

                        if self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["distance"]:
                            self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["count"]=None
                            self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["zoom"]=None
                            self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["yaw"]=None
                            self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["pitch"]=None
                            self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["duration"]=None
                            self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["interval"]=None                           

                    if self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["type"]=="IMAGE_INTERVAL":
                        if not self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["interval"]:
                            self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["interval"]=2
                            self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["zoom"]=None
                            self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["yaw"]=None
                            self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["pitch"]=None
                            self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["count"]=None
                            self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["duration"]=None
                        if self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["interval"]:
                            self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["count"]=None
                            self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["zoom"]=None
                            self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["yaw"]=None
                            self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["pitch"]=None
                            self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["duration"]=None
                            self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["count"]=None    

                    if self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["type"]=="VIDEO_START":
                        self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["count"]=None
                        self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["zoom"]=None
                        self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["yaw"]=None
                        self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["pitch"]=None
                        self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["duration"]=None
                        self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["count"]=None    

                    if self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["type"]=="VIDEO_STOP":
                        self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["count"]=None
                        self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["zoom"]=None
                        self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["yaw"]=None
                        self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["pitch"]=None
                        self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["duration"]=None
                        self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["count"]=None  
        gps_points=self.parse_distance()               
        try:
            gps_points = self.parse_distance()

            if not gps_points:
                pass

            segments, total = total_route_distance(gps_points)
            self.validated["model_for_extraction_json_output"]["total_distance"] = total

        except Exception as e:
            print(f"Distance calculation failed: {e}")
            pass
        duration=total_time_calculation(self.validated)
        self.validated["model_for_extraction_json_output"]["total_duration"]=duration
        return {
                "status": "ok",
                "mission": self.validated
                }

# validated={'db_record_id': '130', 'user_id': 1, 'site_id': 1, 'org_id': 1, 'prompt': 'Create a point mission where the drone takes off from the Main Entrance Checkpoint, flies to the Warehouse Loading Dock, performs a clockwise loiter with a 25 m radius at 60 m altitude for 90 seconds, then returns and lands back at the Main Entrance Checkpoint.', 'class': 'point', 'reason': 'The primary operation occurs while the drone is stationary during the 90-second loiter.', 'complexity': 0.4, 'model_for_extraction': 'gpt-5-nano', 'model_for_extraction_json_output': {'type': '', 'name': '', 'city': '', 'label_id': 0, 'total_distance': 500, 'total_duration': 400, 'finish_action': {'type': 'LAND', 'duration': None}, 'waypoints': [{'sequence': 1, 'location': [], 'altitude': None, 'altitude_mode': None, 'speed': None, 'radius': 25.0, 'actions': [{'sequence': 1, 'type': 'HOVER', 'params': {'pitch': None, 'yaw': None, 'duration': 90, 'interval': None, 'count': None, 'zoom': None, 'distance': None}}]}, {'sequence': 2, 'location': [73.7572, 19.9587, 10], 'altitude': None, 'altitude_mode': None, 'speed': None, 'radius': None, 'actions': []}], 'takeoff_config': {'altitude': None, 'altitude_mode': None, 'speed': None}, 'route_config': {'altitude': 40, 'altitude_mode': 'AGL', 'speed': 4, 'radius': 2}, 'mission_config': {'mode': 'orbit', 'base_path': [[72.8777, 19.076]], 'layers': [{'altitude': 20, 'altitude_mode': 'AGL'}, {'altitude': 30, 'altitude_mode': 'AGL'}, {'altitude': 40, 'altitude_mode': 'AGL'}], 'camera_profile': {'pitch': 0, 'yaw_mode': 'poi', 'poi': [72.8777, 19.076]}, 'yaw_step': 0, 'limits': {'max_vertical_speed': 0, 'layer_spacing': 0}}, 'dock_id': 0, 'can_select_dock': True, 'is_hidden': False, 'is_private': True, 'camera_profile': {'pitch': None, 'yaw_mode': None, 'poi': None}}}
# c=CheckThreshold(validated)
# print(c.check_waypoints())
