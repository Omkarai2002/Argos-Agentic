# geofence_validator.py

import mysql.connector
import math
from typing import Dict
from app.config import PROMPT_COMPLETION_DATABASE_CONFIG,PRODUCTION_DB_CONFIG
#import psycopg
import json

class GeofenceValidator:

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

    def fetch_geofences(self, site_id):
        conn = self.get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT type, coordinates
            FROM geofences
            WHERE site_id = %s AND is_active = 1 AND deleted_at = NULL;
        """, (site_id,))

        rows = cur.fetchall()
        conn.close()

        return [{"type": r[0].lower(), "coordinates": r[1]} for r in rows]

    # ---------------- Geometry ---------------- #

    def distance(self, p1, p2):
        """Haversine distance in meters"""
        R = 6371000

        lat1, lon1 = map(math.radians, p1)
        lat2, lon2 = map(math.radians, p2)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        return 2 * R * math.asin(math.sqrt(a))

    def point_in_circle(self, point, center, radius):
        return self.distance(point, center) <= radius

    def point_in_rectangle(self, point, rect):
        """rect expects dict: west, east, south, north"""
        lat, lon = point
        return (
            rect["west"] <= lon <= rect["east"]
            and rect["south"] <= lat <= rect["north"]
        )

    def point_in_polygon(self, point, polygon):
        """Ray casting algorithm. polygon = list of [lon, lat]"""
        lat, lon = point
        x, y = lon, lat  # convert to (x=lon, y=lat)

        inside = False
        n = len(polygon)

        p1x, p1y = polygon[0]

        for i in range(n + 1):
            p2x, p2y = polygon[i % n]

            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside

            p1x, p1y = p2x, p2y

        return inside

    # ---------------- Main Validator ---------------- #

    def validate(self, validated: Dict) -> Dict:

        site_id = validated["site_id"]
        geofences = self.fetch_geofences(site_id)

        waypoints = validated["model_for_extraction_json_output"].get("waypoints", [])

        for wp in waypoints:

            raw_loc = wp.get("location")
            print("raw_loc:",raw_loc)
            # -------- Normalize location -------- #
            try:
    # -------- Case 1: dict -------- #
                if isinstance(raw_loc, dict):
                    lat = float(raw_loc.get("lat"))
                    lon = float(raw_loc.get("lon"))
                    loc = (lat, lon)

                # -------- Case 2: list/tuple -------- #
                elif isinstance(raw_loc, (list, tuple)) and len(raw_loc) >= 2:
                    lon = float(raw_loc[0])
                    lat = float(raw_loc[1])
                    loc = (lat, lon)

                else:
                    raise ValueError("Invalid location format")

            except:
                wp["location"] = []
                continue
            # -------- Basic validation -------- #
            if not isinstance(loc, (list, tuple)) or len(loc) < 2:
                wp["location"] = []
                continue

            valid = True

            # -------- Check against all geofences -------- #
            for fence in geofences:

                print('geofence:', fence)

                ftype = fence["type"]
                coords = json.loads(fence["coordinates"]) if isinstance(fence["coordinates"], str) else fence["coordinates"]

                if ftype == "circle":
                    try:
                        lon_c, lat_c, radius = coords
                        center = (lat_c, lon_c)

                        if not self.point_in_circle(loc, center, radius):
                            valid = False
                    except:
                        continue

                elif ftype == "polygon":
                    if not self.point_in_polygon(loc, coords):
                        valid = False

                elif ftype == "rectangle":
                    if not self.point_in_rectangle(loc, coords):
                        valid = False

                if valid:
                    break

            # -------- Final decision -------- #
            if not valid:
                wp["location"] = []

            print("loc:", loc, "| valid:", valid)

        return validated