from pydantic import BaseModel
from typing import List, Optional

class Waypoint(BaseModel):
    location: str
    action: List[str] = None

class MissionPlan(BaseModel):
    waypoints: List[Waypoint]