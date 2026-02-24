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
        gps_points=[]
        for i in range(len(self.validated["model_for_extraction_json_output"]["waypoints"])):
            gps_points.append(tuple(self.validated["model_for_extraction_json_output"]["waypoints"][i]["location"][0:2]))
        return gps_points

    def check_waypoints(self):
        wayp=self.validated["model_for_extraction_json_output"]["waypoints"]
        if self.validated["model_for_extraction_json_output"]["finish_action"]["type"] not in ["HOVER"]:
            self.validated["model_for_extraction_json_output"]["finish_action"]["duration"] = None
        if self.validated["model_for_extraction_json_output"]["finish_action"]["type"] in ["HOVER"]:
            if not self.validated["model_for_extraction_json_output"]["finish_action"]["duration"]:
                self.validated["model_for_extraction_json_output"]["finish_action"]["duration"]=20
        
        if not self.validated["model_for_extraction_json_output"]["takeoff_config"]["altitude"] or (self.validated["model_for_extraction_json_output"]["takeoff_config"]["altitude"]<=10):
            alti=input("altitude is not valid for the drone to fly enter y for updating values and n for getting default:")
            if alti=="y" or alti=="Y":
                altit=int(input("Enter the altitude below 100m:"))
                
                if 10<=altit<=100:
                    self.validated["model_for_extraction_json_output"]["takeoff_config"]["altitude"]=altit
                else:
                    self.validated["model_for_extraction_json_output"]["takeoff_config"]["altitude"]=40

            else:
                self.validated["model_for_extraction_json_output"]["takeoff_config"]["altitude"]=40
                
        if not self.validated["model_for_extraction_json_output"]["takeoff_config"]["speed"] or (self.validated["model_for_extraction_json_output"]["takeoff_config"]["speed"]>=10 or self.validated["model_for_extraction_json_output"]["takeoff_config"]["speed"]<=1):
            spd=input("speed is not valid for the drone to fly enter y for updating values and n for getting default:")
            if spd=="y" or spd=="Y":
                speed=int(input("Enter the speed below 10m/s:"))
                
                if 1<=speed<=10:
                    self.validated["model_for_extraction_json_output"]["takeoff_config"]["speed"]=speed
                else:
                    self.validated["model_for_extraction_json_output"]["takeoff_config"]["speed"]=4

            else:
                self.validated["model_for_extraction_json_output"]["takeoff_config"]["speed"]=4
        

        
        for i in range(len(wayp)):
            wayp_dict=dict
            if self.validated["model_for_extraction_json_output"]["waypoints"][i]["location"]==[]:
                new_loc=input(f"location out of geofence for waypoint {i+1},enter location name within geofence:")
                self.validated["model_for_extraction_json_output"]["waypoints"][i]["location"]=str(new_loc)
                
                validated=self.c.find_waypoint_closest_and_update(self.validated)
                validated=self.geofence.validate(validated)
                
            if not self.validated["model_for_extraction_json_output"]["waypoints"][i]["location"]:
                new_loc=input(f"location not mentioned for waypoint {i+1},enter location name within geofence:")
            
            if self.validated["model_for_extraction_json_output"]["waypoints"][i]["altitude"] and (self.validated["model_for_extraction_json_output"]["waypoints"][i]["altitude"]<=10 or self.validated["model_for_extraction_json_output"]["waypoints"][i]["altitude"]>=100):
                alt=int(input("Enter the altitude between 10 metres to 100 metres,not above or below that:"))
                if alt<=10 or alt>=100:
                    self.validated["model_for_extraction_json_output"]["waypoints"][i]["altitude"]=self.validated["model_for_extraction_json_output"]["takeoff_config"]["altitude"]
                self.validated["model_for_extraction_json_output"]["waypoints"][i]["altitude"]=alt
            
            if self.validated["model_for_extraction_json_output"]["waypoints"][i]["speed"] and (self.validated["model_for_extraction_json_output"]["waypoints"][i]["speed"]<=1 or self.validated["model_for_extraction_json_output"]["waypoints"][i]["speed"]>=10):
                spd=int(input(f"Enter the speed between 1 m/s to 10 m/s,not above or below that for {i}th waypoint:"))
                if spd<=1 or spd>=10:
                    self.validated["model_for_extraction_json_output"]["waypoints"][i]["speed"]=self.validated["model_for_extraction_json_output"]["takeoff_config"]["speed"]
                self.validated["model_for_extraction_json_output"]["waypoints"][i]["speed"]=spd
            
            if self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"] or (len(self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"])!=0):
                for j in range(len(self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"])):
                    if self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["type"]=="HOVER":
                        if self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["duration"]>=100 or not self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["duration"]:
                            dur=int(input(f"enter the duration between 1 to 100 for the drone to hover for {i}th waypoint and {j}th action"))
                            if 1<=self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["duration"]<=100:
                                self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["duration"]=30
                            self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["duration"]=dur

                        if self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["type"]=="GIMBAL_CONTROL":
                            
                            if not self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["pitch"]:
                                gc=float(input(f"enter the gimbal control pitch for {i}th waypoint and {j}th action"))            
                                self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["pitch"]=gc
                            if not self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["yaw"]:
                                gc=float(input("enter the gimbal control yaw")) 
                                self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["yaw"]=gc

                        if self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["type"]=="CAMERA_ZOOM":
                            
                            if not self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["zoom"] or (self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["zoom"]<=0 or self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["zoom"]>=100) :
                                zm=int(input(f"enter the camera zoom score between 0 to 100 for {i}th waypoint and {j}th action :"))
                                if 0>=zm or zm>=100:          
                                    self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["zoom"]=20
                                self.validated["model_for_extraction_json_output"]["waypoints"][i]["actions"][j]["params"]["zoom"]=zm
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
        return self.validated

# validated={'db_record_id': '130', 'user_id': 1, 'site_id': 1, 'org_id': 1, 'prompt': 'Create a point mission where the drone takes off from the Main Entrance Checkpoint, flies to the Warehouse Loading Dock, performs a clockwise loiter with a 25 m radius at 60 m altitude for 90 seconds, then returns and lands back at the Main Entrance Checkpoint.', 'class': 'point', 'reason': 'The primary operation occurs while the drone is stationary during the 90-second loiter.', 'complexity': 0.4, 'model_for_extraction': 'gpt-5-nano', 'model_for_extraction_json_output': {'type': '', 'name': '', 'city': '', 'label_id': 0, 'total_distance': 500, 'total_duration': 400, 'finish_action': {'type': 'LAND', 'duration': None}, 'waypoints': [{'sequence': 1, 'location': [], 'altitude': None, 'altitude_mode': None, 'speed': None, 'radius': 25.0, 'actions': [{'sequence': 1, 'type': 'HOVER', 'params': {'pitch': None, 'yaw': None, 'duration': 90, 'interval': None, 'count': None, 'zoom': None, 'distance': None}}]}, {'sequence': 2, 'location': [73.7572, 19.9587, 10], 'altitude': None, 'altitude_mode': None, 'speed': None, 'radius': None, 'actions': []}], 'takeoff_config': {'altitude': None, 'altitude_mode': None, 'speed': None}, 'route_config': {'altitude': 40, 'altitude_mode': 'AGL', 'speed': 4, 'radius': 2}, 'mission_config': {'mode': 'orbit', 'base_path': [[72.8777, 19.076]], 'layers': [{'altitude': 20, 'altitude_mode': 'AGL'}, {'altitude': 30, 'altitude_mode': 'AGL'}, {'altitude': 40, 'altitude_mode': 'AGL'}], 'camera_profile': {'pitch': 0, 'yaw_mode': 'poi', 'poi': [72.8777, 19.076]}, 'yaw_step': 0, 'limits': {'max_vertical_speed': 0, 'layer_spacing': 0}}, 'dock_id': 0, 'can_select_dock': True, 'is_hidden': False, 'is_private': True, 'camera_profile': {'pitch': None, 'yaw_mode': None, 'poi': None}}}
# c=CheckThreshold(validated)
# print(c.check_waypoints())
