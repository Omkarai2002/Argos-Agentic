# geofence_validator.py

import psycopg
import math
from typing import List, Dict
from app.config import PROMPT_COMPLETION_DATABASE_CONFIG


class GeofenceValidator:

    def __init__(self):
        self.dbname = PROMPT_COMPLETION_DATABASE_CONFIG["DB_NAME"]
        self.user = PROMPT_COMPLETION_DATABASE_CONFIG["DB_USER"]
        self.password = PROMPT_COMPLETION_DATABASE_CONFIG["DB_PASSWORD"]
        self.host = PROMPT_COMPLETION_DATABASE_CONFIG["DB_HOST"]
        self.port = PROMPT_COMPLETION_DATABASE_CONFIG["DB_PORT"]

    # ---------------- DB ---------------- #

    def get_connection(self):
        return psycopg.connect(
            dbname=self.dbname,
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
            FROM geofence
            WHERE site_id = %s;
        """, (site_id,))

        rows = cur.fetchall()
        conn.close()

        return [{"type": r[0].lower(), "coordinates": r[1]} for r in rows]

    # ---------------- Geometry ---------------- #

    def point_in_circle(self, point, center, radius=50):
        # radius default safety if not stored
        return self.distance(point, center) <= radius

    def point_in_rectangle(self, point, rect):

        lon, lat = point[:2]

        return (
            rect["west"] <= lon <= rect["east"]
            and rect["south"] <= lat <= rect["north"]
        )

    def point_in_polygon(self, point, polygon):

        x, y = point[:2]
        inside = False

        pts = polygon
        n = len(pts)

        p1x, p1y = pts[0][0], pts[0][1]

        for i in range(n + 1):
            p2x, p2y = pts[i % n][0], pts[i % n][1]

            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside

            p1x, p1y = p2x, p2y

        return inside

    def distance(self, p1, p2):
        return math.sqrt(
            (p1[0] - p2[0]) ** 2 +
            (p1[1] - p2[1]) ** 2
        )

    # ---------------- Main Validator ---------------- #

    def validate(self, validated: Dict) -> Dict:

        site_id = validated["site_id"]
        geofences = self.fetch_geofences(site_id)

        waypoints = validated["model_for_extraction_json_output"].get("waypoints", [])

        for wp in waypoints:

            loc = wp.get("location")

            # Skip empty or non-numeric
            if not isinstance(loc, list) or len(loc) < 2:
                wp["location"] = []
                continue

            valid = False

            for fence in geofences:

                ftype = fence["type"]
                coords = fence["coordinates"]

                if ftype == "circle":
                    # coordinates stored as [lon,lat,alt]
                    if self.point_in_circle(loc, coords):
                        valid = True

                elif ftype == "polygon":
                    if self.point_in_polygon(loc, coords):
                        valid = True

                elif ftype == "rectangle":
                    if self.point_in_rectangle(loc, coords):
                        valid = True

                if valid:
                    break

            if not valid:
                wp["location"] = []

        return validated


# ---------------- Test ---------------- #

# if __name__ == "__main__":

#     validator = GeofenceValidator()

#     validated = {
#         "site_id": 1,
#         "model_for_extraction_json_output": {
#             "waypoints": [
#                 {"sequence": 1, "location": [73.7572, 19.9587, 10]},
#                 {"sequence": 2, "location": [70.0, 10.0, 10]}
#             ]
#         }
#     }

#     print(validator.validate(validated))
