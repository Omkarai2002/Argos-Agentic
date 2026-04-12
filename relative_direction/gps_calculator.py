import math


class GpsCalculationRelative:

    def get_new_gps(self, lat1, lon1, distance_m, bearing_deg):
        """
        lat1, lon1 -> current location in degrees
        distance_m -> distance in meters
        bearing_deg -> direction in degrees (0 = North, 90 = East)
        """

        R = 6371000  # Earth radius in meters

        # Convert to radians
        lat1 = math.radians(lat1)
        lon1 = math.radians(lon1)
        bearing = math.radians(bearing_deg)

        # Angular distance
        d_by_R = distance_m / R

        # New latitude
        lat2 = math.asin(
            math.sin(lat1) * math.cos(d_by_R) +
            math.cos(lat1) * math.sin(d_by_R) * math.cos(bearing)
        )

        # New longitude
        lon2 = lon1 + math.atan2(
            math.sin(bearing) * math.sin(d_by_R) * math.cos(lat1),
            math.cos(d_by_R) - math.sin(lat1) * math.sin(lat2)
        )

        return {
            "lat": math.degrees(lat2),
            "lon": math.degrees(lon2)
        }

    def indivisual_waypoint_gps_fetch(self, validated):
        """
        Converts relative waypoints (angle + distance)
        into absolute GPS coordinates
        """

        lat = validated["dock_coordinates"]["lat"]
        lon = validated["dock_coordinates"]["lon"]

        waypoints = validated["model_for_extraction_json_output"].get("waypoints", [])

        # -----------------------------
        # STEP 1: Generate GPS points
        # -----------------------------
        for i in range(len(waypoints)):

            wp = waypoints[i]

            distance = wp.get("distance_meters")
            degrees = wp.get("angle_degrees")

            # Skip invalid waypoints
            if distance is None or degrees is None:
                continue

            if i==0:
                lat = validated["dock_coordinates"]["lat"]
                lon = validated["dock_coordinates"]["lon"]     
                new_gps = self.get_new_gps(lat, lon, distance, degrees)
                new_gps=[new_gps["lon"],new_gps["lat"]]
                # Store GPS properly (NOT in name)
                print("new_gps:",new_gps)
                validated["model_for_extraction_json_output"]["waypoints"][i]["name"]=new_gps
                print("validated:",validated["model_for_extraction_json_output"]["waypoints"][i]["name"])
            if i!=0:
                print("validated:",validated["model_for_extraction_json_output"]["waypoints"][i-1]["name"])
                lat=validated["model_for_extraction_json_output"]["waypoints"][i-1]["name"][1]
                lon=validated["model_for_extraction_json_output"]["waypoints"][i-1]["name"][0]
                new_gps = self.get_new_gps(lat, lon, distance, degrees)
                new_gps=[new_gps["lon"],new_gps["lat"]]
                print("new_gps:",new_gps)
                validated["model_for_extraction_json_output"]["waypoints"][i]["name"]=new_gps
            # Update reference point for next waypoint
            


        return validated