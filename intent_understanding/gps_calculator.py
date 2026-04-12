import math
import psycopg
import logging
from app.config import PROMPT_COMPLETION_DATABASE_CONFIG
from correction_layer.annotations_calculation import GeometryCenterCalculator
logger = logging.getLogger(__name__)


class ConnectToDb:

    def __init__(self):
        self.dbname = PROMPT_COMPLETION_DATABASE_CONFIG["DB_NAME"]
        self.user = PROMPT_COMPLETION_DATABASE_CONFIG["DB_USER"]
        self.password = PROMPT_COMPLETION_DATABASE_CONFIG["DB_PASSWORD"]
        self.host = PROMPT_COMPLETION_DATABASE_CONFIG["DB_HOST"]
        self.port = PROMPT_COMPLETION_DATABASE_CONFIG["DB_PORT"]

    def get_connection(self):
        return psycopg.connect(
            dbname=self.dbname,
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
                
                try:
                    c=ConnectToDb()
                    annotation_row=c.get_center_of_annotations(name=location,validated=validated)
                    print("annotations_row:",annotation_row)
                    center = GeometryCenterCalculator.calculate(annotation_row)
                    print("center_for_annotations:",center)
                    validated["model_for_extraction_json_output"]["waypoints"][i]["name"]  = center[0:2]
                except Exception:
                    validated["model_for_extraction_json_output"]["waypoints"][i]["name"] = None
                    continue
                if not location:
                    raise ValueError(f"Missing location for absolute waypoint at index {i}")
                
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
                if i==0:
                    new_gps = self.get_new_gps(lat, lon, distance, degrees)
                    print("new_gps:",new_gps)
                    lat = new_gps["lat"]
                    lon = new_gps["lon"]
                    validated["model_for_extraction_json_output"]["waypoints"][i]["name"] = [lon,lat]
                    print("validated_for_Omkar:",validated)
                if i!=0:
                    
                    lon=validated["model_for_extraction_json_output"]["waypoints"][i-1]["name"][0]
                    lat=validated["model_for_extraction_json_output"]["waypoints"][i-1]["name"][1]
                    new_gps = self.get_new_gps(lat, lon, distance, degrees)
                    print("new_gps:",new_gps)
                    lat = new_gps["lat"]
                    lon = new_gps["lon"]
                    
                    validated["model_for_extraction_json_output"]["waypoints"][i]["name"] = [lon,lat]

            else:
                raise ValueError(f"Unknown waypoint type at index {i}: {wp_type}")

        return validated
    
