from pydantic import BaseModel, Field
from typing import List, Optional, Literal


# -----------------------------
# Action Schema
# -----------------------------

class Action(BaseModel):
    type: Literal[
        "HOVER", "GIMBAL_CONTROL", "GIMBAL_DOWN", "GIMBAL_RECENTER",
        "IMAGE_CAPTURE_SINGLE", "IMAGE_DISTANCE", "IMAGE_INTERVAL",
        "IMAGE_STOP", "VIDEO_START", "VIDEO_STOP", "CAMERA_ZOOM"
    ]
    pitch: Optional[int] = None
    count: Optional[int] = None
    interval: Optional[float] = None
    distance: Optional[float] = None
    yaw: Optional[int] = None
    zoom:Optional[int] = None
    duration:Optional[float] = None



# -----------------------------
# Waypoint Schema
# -----------------------------

class Waypoint(BaseModel):
    name: Optional[str] = None   # <-- ALWAYS NULL
    angle_degrees: Optional[float] = None
    distance_meters: Optional[float] = None
    speed:Optional[float]=None
    altitude: Optional[float] = None
    altitude_mode: Optional[Literal["AGL", "ASL"]] = None
    actions: Optional[List[Action]] = None

class Takeoff(BaseModel):
    altitude: Optional[int] = None
    mode: Optional[str] = None
    speed: Optional[float] = None

class Camera(BaseModel):
    pitch: Optional[int] = None
    yaw_mode: Optional[str] = None
    poi: Optional[int] = None
# -----------------------------
# Finish Schema
# -----------------------------

class Finish(BaseModel):
    type: Optional[Literal["HOVER", "LAND", "RTL", "RTDS", "PL", "RTSL"]] = None
    duration:Optional[float] = None

# -----------------------------
# Final Response
# -----------------------------

class MissionResponse(BaseModel):
    waypoints: List[Waypoint] = []
    finish: Optional[Finish] = None
    takeoff: Optional[Takeoff] = None
    camera: Optional[Camera] = None