from pydantic import BaseModel
from typing import List,Optional,Dict

class ActionParams(BaseModel):
    pitch:Optional[float]
    yaw:Optional[float]
    duration:Optional[int]
    interval:Optional[int]
    count:Optional[int]
    zoom:Optional[int]
    distance:Optional[float]

class Action(BaseModel):
    sequence:Optional[int]
    type:Optional[str]
    params:ActionParams

class Waypoints(BaseModel):
    sequence: Optional[int] = None
    location: Optional[str] = None
    altitude: Optional[float] = None
    altitude_mode: Optional[str] = None
    speed: Optional[float] = None
    radius: Optional[float] = None
    actions: Optional[List[Action]] = None

class TakeOffconfig(BaseModel):
    altitude: Optional[int]
    altitude_mode:Optional[str]
    speed:Optional[int]

class RouteConfig(BaseModel):
    altitude: Optional[int]
    altitude_mode:Optional[str]
    speed:Optional[int]

class MissionConfig(BaseModel):
    mode:Optional[str]
    base_path:Optional[list]
    layers:Optional[list]
    camera_profile:dict

class CameraProfile(BaseModel):
    pitch:Optional[int]
    yaw_mode:Optional[str]
    poi:Optional[list]

class Template(BaseModel):
    waypoints: Optional[List[Waypoints]] = None
    takeoff_config: Optional[TakeOffconfig] = None
    route_config: Optional[RouteConfig] = None
    mission_config: Optional[MissionConfig] = None



