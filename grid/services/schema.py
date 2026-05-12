from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Any


class GridPoint(BaseModel):
    sequence: int
    point: List[float]


class GridConfig(BaseModel):
    gsd: Optional[float] = None
    angle: Optional[int] = 0
    points: List[GridPoint] = Field(default_factory=list)


class CameraSpecs(BaseModel):
    focalLength: Optional[float] = None
    sensorWidth: Optional[float] = None
    sensorHeight: Optional[float] = None
    pixelWidth: Optional[int] = None
    pixelHeight: Optional[int] = None


class GimbalSettings(BaseModel):
    pitch: Optional[int] = -90
    yaw: Optional[int] = 0


class ImageOverlap(BaseModel):
    front: Optional[int] = 80
    side: Optional[int] = 70


class ImageSpacing(BaseModel):
    x: Optional[float] = None
    y: Optional[float] = None


class ImageTrigger(BaseModel):
    distance: Optional[float] = None
    interval: Optional[float] = 0
    interval: Optional[float] = 0
    images: Optional[int] = 0


class MediaCapture(BaseModel):
    mode: Optional[Literal["distance", "interval", "video"]] = "distance"
    distance: Optional[float] = None


class MissionConfig(BaseModel):
    grid_config: GridConfig
    camera_specs: Optional[CameraSpecs] = None
    gimbal_settings: GimbalSettings
    image_overlap: ImageOverlap
    image_spacing: ImageSpacing
    image_trigger: ImageTrigger
    grid_area: Optional[float] = 0
    media_capture: MediaCapture


class TakeoffConfig(BaseModel):
    altitude: float
    altitude_mode: Literal["AGL", "AMSL", "REL"]
    speed: float
    actions: List[str] = Field(default_factory=list)


class RouteConfig(BaseModel):
    altitude: float
    altitude_mode: Literal["AGL", "AMSL", "REL"]
    speed: float
    radius: float


class PrecisionMode(BaseModel):
    type: Optional[str] = "RTK"
    land_height: Optional[float] = 0.1
    trigger_height: Optional[float] = 5
    guided_approach: Optional[bool] = False


class FinishAction(BaseModel):
    type: Optional[str] = "LAND"


class MissionResponse(BaseModel):
    type: str = "grid"
    name: Optional[str] = None
    color: Optional[str] = None
    city: Optional[str] = None
    label_id: Optional[int] = None
    dock_id: Optional[int] = None
    can_select_dock: Optional[bool] = True
    is_hidden: Optional[bool] = False
    is_private: Optional[bool] = False
    precision_mode: Optional[PrecisionMode] = Field(default_factory=PrecisionMode)
    finish_action: Optional[FinishAction] = Field(default_factory=FinishAction)
    mission_config: MissionConfig
    takeoff_config: TakeoffConfig
    route_config: RouteConfig
    total_distance: Optional[float] = 0
    total_duration: Optional[float] = 0
    waypoints: List[str] = Field(default_factory=list)  # ← typed as List[str], overwritten to [] in enforce