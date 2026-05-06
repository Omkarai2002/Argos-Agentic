from pydantic import BaseModel, Field, model_validator
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
    pitch: Optional[int] = Field(default=None, ge=-90, le=90)
    yaw: Optional[int] = Field(default=None, ge=-180, le=180)
    zoom: Optional[int] = Field(default=None, ge=1, le=30)
    count: Optional[int] = Field(default=None, ge=1)
    interval: Optional[float] = Field(default=None, gt=0)
    distance: Optional[float] = Field(default=None, gt=0)
    duration: Optional[float] = Field(default=None, gt=0)


# -----------------------------
# Location Schema (replaces bare string)
# -----------------------------

class Location(BaseModel):
    name: Optional[str] = None       # "School", "Hospital"
    lat: Optional[float] = None
    lng: Optional[float] = None

    @model_validator(mode="after")
    def must_have_name_or_coords(self):
        has_coords = self.lat is not None and self.lng is not None
        has_name = bool(self.name)
        if not has_coords and not has_name:
            raise ValueError("Location must have either a name or lat/lng coordinates")
        return self


# -----------------------------
# Waypoint Schema
# -----------------------------

class Waypoint(BaseModel):
    type: Literal["absolute", "relative"]           # required, no Optional
    name: Optional[str] = None
    angle_degrees: Optional[float] = Field(default=None, ge=0, le=360)
    distance_meters: Optional[float] = Field(default=None, gt=0)
    location: Optional[Location] = None             # structured, not str
    speed: Optional[float] = Field(default=None, gt=0)
    altitude: Optional[float] = Field(default=None, ge=0)
    altitude_mode: Optional[Literal["AGL", "ASL"]] = None
    actions: Optional[List[Action]] = None

    @model_validator(mode="after")
    def validate_type_fields(self):
        if self.type == "relative":
            if self.angle_degrees is None:
                raise ValueError("relative waypoint requires angle_degrees")
            if self.distance_meters is None:
                raise ValueError("relative waypoint requires distance_meters")

        elif self.type == "absolute":
            if self.location is None:
                raise ValueError(
                    "absolute waypoint requires location "
                    "(provide name, lat/lng, or both)"
                )
        return self


# -----------------------------
# Takeoff Schema
# -----------------------------

class Takeoff(BaseModel):
    altitude: Optional[int] = Field(default=None, ge=0)
    mode: Optional[str] = None
    speed: Optional[float] = Field(default=None, gt=0)


# -----------------------------
# Camera Schema
# -----------------------------

class Camera(BaseModel):
    pitch: Optional[int] = Field(default=None, ge=-90, le=90)
    yaw_mode: Optional[str] = None
    poi: Optional[int] = None


# -----------------------------
# Finish Schema
# -----------------------------

class Finish(BaseModel):
    type: Optional[Literal["HOVER", "LAND", "RTL", "RTDS", "PL", "RTSL"]] = None
    duration: Optional[float] = Field(default=None, gt=0)


# -----------------------------
# Final Response
# -----------------------------

class MissionResponse(BaseModel):
    waypoints: List[Waypoint]
    finish: Optional[Finish] = None
    takeoff: Optional[Takeoff] = None
    camera: Optional[Camera] = None