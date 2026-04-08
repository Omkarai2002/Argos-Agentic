from pydantic import BaseModel

class Params(BaseModel):
    speed: float
    altitude: float
    altitude_mode: str
    reason:str