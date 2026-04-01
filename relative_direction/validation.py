from .schemas import MissionResponse
def validate_waypoints(data):
    print("✅ VALIDATION RUNNING")

    for i, wp in enumerate(data.waypoints):
        print(f"Checking waypoint {i}: {wp}")

        # ONLY check type first
        if wp.type == "relative":
            if wp.angle_degrees is None:
                raise ValueError("angle missing")

            if wp.distance_meters is None:
                raise ValueError("distance missing")

        elif wp.type == "absolute":
            if not wp.location:
                raise ValueError("location missing")

        else:
            raise ValueError("unknown type")