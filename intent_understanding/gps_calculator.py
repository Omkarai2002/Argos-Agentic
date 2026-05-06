import math
#import psycopg
import mysql.connector
import logging
from app.config import PROMPT_COMPLETION_DATABASE_CONFIG,PRODUCTION_DB_CONFIG
from correction_layer.annotations_calculation import GeometryCenterCalculator
logger = logging.getLogger(__name__)

class ConnectToDb:

    def __init__(self):
        
        # self.dbname = PROMPT_COMPLETION_DATABASE_CONFIG["DB_NAME"]
        # self.user = PROMPT_COMPLETION_DATABASE_CONFIG["DB_USER"]
        # self.password = PROMPT_COMPLETION_DATABASE_CONFIG["DB_PASSWORD"]
        # self.host = PROMPT_COMPLETION_DATABASE_CONFIG["DB_HOST"]
        # self.port = PROMPT_COMPLETION_DATABASE_CONFIG["DB_PORT"]
        self.dbname = PRODUCTION_DB_CONFIG["PRODUCTION_DB_NAME"]
        self.user = PRODUCTION_DB_CONFIG["PRODUCTION_DB_USER"]
        self.password = PRODUCTION_DB_CONFIG["PRODUCTION_DB_PASSWORD"]
        self.host = PRODUCTION_DB_CONFIG["PRODUCTION_HOST"]
        self.port = PRODUCTION_DB_CONFIG["PRODUCTION_PORT"]
    def get_connection(self):
        # return psycopg.connect(
        #     dbname=self.dbname,
        #     user=self.user,
        #     password=self.password,
        #     host=self.host,
        #     port=self.port
        # )
        return mysql.connector.connect(
    database=self.dbname,
    user=self.user,
    password=self.password,
    host=self.host,
    port=self.port
)


    def get_annotation_row_by_name(self, site_id,org_id, name):

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT shape, geometry, height
            FROM annotations
            WHERE site_id=%s AND organization_id=%s AND name=%s 
            LIMIT 1;
        """, (site_id,org_id, name))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return {
            "shape": row[0],
            "geometry": row[1],
            "height": row[2]
        }
    def get_center_of_annotations(self,name,validated):
        site_id=validated["site_id"]
        org_id=validated["org_id"]
        user_id=validated["user_id"]
        annotation_row=self.get_annotation_row_by_name(site_id,org_id,name)
        return annotation_row


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

    def indivisual_waypoint_gps_fetch(self, validated):
        lat = validated["dock_coordinates"]["lat"]
        lon = validated["dock_coordinates"]["lon"]

        waypoints = validated["model_for_extraction_json_output"].get("waypoints", [])

        for i in range(len(waypoints)):
            wp = waypoints[i]
            wp_type = wp.get("type")

            if wp_type == "absolute":
                location = wp.get("location")

                if not location:
                    raise ValueError(f"Missing location for absolute waypoint at index {i}")

                # ✅ Handle both old str format and new Location dict format
                if isinstance(location, dict):
                    location_name = location.get("name")
                else:
                    location_name = location  # legacy plain string

                if not location_name:
                    raise ValueError(
                        f"Absolute waypoint at index {i} has no resolvable name "
                        f"(location={location})"
                    )

                try:
                    c = ConnectToDb()
                    annotation_row = c.get_center_of_annotations(name=location_name, validated=validated)
                    
                    print("annotations_row:", annotation_row)
                    center = GeometryCenterCalculator.calculate(annotation_row)
                    print("center_for_annotations:", center)

                    # center is [lon, lat, ...] based on how relative reads it
                    resolved_lon, resolved_lat = center[0], center[1]
                    validated["model_for_extraction_json_output"]["waypoints"][i]["name"] = [resolved_lon, resolved_lat]

                    # ✅ Update reference so subsequent relative waypoints chain correctly
                    lat = resolved_lat
                    lon = resolved_lon

                except Exception as e:
                    # ✅ Raise instead of silently poisoning downstream waypoints
                    raise ValueError(
                        f"Failed to resolve absolute waypoint '{location}' at index {i}: {e}"
                    ) from e

            elif wp_type == "relative":
                distance = wp.get("distance_meters")
                degrees = wp.get("angle_degrees")

                if distance is None or degrees is None:
                    raise ValueError(f"Invalid relative waypoint at index {i}: missing distance or angle")

                # ✅ Unified logic — always use current lat/lon reference, no i==0 special case needed
                # For i==0, lat/lon is dock. For i>0, it was updated by previous waypoint.
                if i > 0:
                    prev_name = validated["model_for_extraction_json_output"]["waypoints"][i-1].get("name")
                    if not prev_name or not isinstance(prev_name, (list, tuple)) or len(prev_name) < 2:
                        raise ValueError(
                            f"Cannot resolve relative waypoint at index {i}: "
                            f"previous waypoint at index {i-1} has no resolved coordinates"
                        )
                    lon, lat = prev_name[0], prev_name[1]

                new_gps = self.get_new_gps(lat, lon, distance, degrees)
                print("new_gps:", new_gps)
                lat = new_gps["lat"]
                lon = new_gps["lon"]
                validated["model_for_extraction_json_output"]["waypoints"][i]["name"] = [lon, lat]

            else:
                raise ValueError(f"Unknown waypoint type at index {i}: {wp_type}")

        return validated
    
