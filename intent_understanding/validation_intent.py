from .schemas import MissionResponse

def validate_waypoints(data):
    print("✅ VALIDATION RUNNING")

    for i, wp in enumerate(data.waypoints):
        print(f"Checking waypoint {i}: type={wp.type}")

        if wp.type == "relative":
            if wp.angle_degrees is None:
                raise ValueError(f"Waypoint {i}: angle_degrees is missing")
            if wp.distance_meters is None:
                raise ValueError(f"Waypoint {i}: distance_meters is missing")
            if not (0 <= wp.angle_degrees <= 360):
                raise ValueError(f"Waypoint {i}: angle_degrees {wp.angle_degrees} out of range 0-360")
            if wp.distance_meters <= 0:
                raise ValueError(f"Waypoint {i}: distance_meters must be > 0")

        elif wp.type == "absolute":
            if not wp.location:
                raise ValueError(f"Waypoint {i}: location is missing")

        else:
            
            raise ValueError(f"Waypoint {i}: unknown type '{wp.type}'")