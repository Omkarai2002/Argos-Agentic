def validate_waypoints(data):
    print("✅ VALIDATION RUNNING")

    for i, wp in enumerate(data.waypoints):
        print(f"Checking waypoint {i}: {wp}")

        # 🧭 RELATIVE waypoint
        if wp.angle_degrees is not None or wp.distance_meters is not None:
            if wp.angle_degrees is None:
                raise ValueError("angle missing")

            if wp.distance_meters is None:
                raise ValueError("distance missing")

        # 📍 ABSOLUTE waypoint (if you later add location)
        elif hasattr(wp, "location") and wp.location:
            pass  # valid

        else:
            raise ValueError("Invalid waypoint: neither relative nor absolute")