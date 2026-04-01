import math


class GpsCalculation:

    def get_new_gps(self, lat1, lon1, distance_m, bearing_deg):
        """
        Calculate new GPS point given:
        lat1, lon1 -> current location in degrees
        distance_m -> distance in meters
        bearing_deg -> direction in degrees (0 = North, 90 = East)
        """

        R = 6371000  # Earth radius in meters

        lat1 = math.radians(lat1)
        lon1 = math.radians(lon1)
        bearing = math.radians(bearing_deg)

        d_by_R = distance_m / R

        lat2 = math.asin(
            math.sin(lat1) * math.cos(d_by_R) +
            math.cos(lat1) * math.sin(d_by_R) * math.cos(bearing)
        )

        lon2 = lon1 + math.atan2(
            math.sin(bearing) * math.sin(d_by_R) * math.cos(lat1),
            math.cos(d_by_R) - math.sin(lat1) * math.sin(lat2)
        )

        return {
            "lat": math.degrees(lat2),
            "lon": math.degrees(lon2)
        }

    # ---------------------------------------
    # 🔥 ABSOLUTE LOCATION RESOLVER
    # ---------------------------------------
    def get_location_coordinates(self, location_name, validated):
        """
        Fetch GPS coordinates for a named location.
        You can replace this with Neo4j / DB lookup.
        """

        # Example placeholder (replace with DB call)
        location_map = {
            "gate A": {"lat": 19.9590, "lon": 73.7575},
            "gate B": {"lat": 19.9600, "lon": 73.7580}
        }

        coords = location_map.get(location_name)

        if coords is None:
            raise ValueError(f"Unknown location: {location_name}")

        return coords

    # ---------------------------------------
    # 🧠 MAIN HYBRID GPS ENGINE
    # ---------------------------------------
    def indivisual_waypoint_gps_fetch(self, validated):
        """
        Converts waypoints (absolute + relative)
        into absolute GPS coordinates
        """

        # Initial reference point (dock)
        lat = validated["dock_coordinates"]["lat"]
        lon = validated["dock_coordinates"]["lon"]

        waypoints = validated["model_for_extraction_json_output"].get("waypoints", [])

        for i in range(len(waypoints)):
            wp = waypoints[i]

            wp_type = wp.get("type")

            if wp_type == "absolute":
                location = wp.get("location")
                print("location:",location)
                if not location:
                    raise ValueError(f"Missing location for absolute waypoint at index {i}")
                validated["model_for_extraction_json_output"]["waypoints"][i]["names"] = location
                # Don't resolve coordinates — keep location name as-is
                # The flight controller will handle named locations
                # Just update lat/lon reference for any subsequent relative waypoints
                # coords = self.get_location_coordinates(location, validated)
                # lat = coords["lat"]
                # lon = coords["lon"]

                # DON'T set wp["coordinates"] for absolute waypoints

            elif wp_type == "relative":
                distance = wp.get("distance_meters")
                degrees = wp.get("angle_degrees")

                if distance is None or degrees is None:
                    raise ValueError(f"Invalid relative waypoint at index {i}")

                new_gps = self.get_new_gps(lat, lon, distance, degrees)
                print("new_gps:",new_gps)
                lat = new_gps["lat"]
                lon = new_gps["lon"]

                validated["model_for_extraction_json_output"]["waypoints"][i]["names"] = new_gps

            else:
                raise ValueError(f"Unknown waypoint type at index {i}: {wp_type}")

        return validated