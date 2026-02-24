import psycopg
from difflib import SequenceMatcher
import logging
from app.config import PROMPT_COMPLETION_DATABASE_CONFIG
from .annotations_calculation import GeometryCenterCalculator

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

    # ----------------------------------
    # Get all geofence names (for fuzzy)
    # ----------------------------------

    def get_waypoint_names(self, site_id):

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT LOWER(name) FROM annotations WHERE site_id=%s;",
            (site_id,)
        )

        rows = cursor.fetchall()
        conn.close()

        return [r[0] for r in rows]

    # ----------------------------------
    # Fetch annotation geometry
    # ----------------------------------

    def get_annotation_row_by_name(self, site_id, name):

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT shape, geometry, height
            FROM annotations
            WHERE site_id=%s AND LOWER(name)=%s
            LIMIT 1;
        """, (site_id, name.lower()))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return {
            "shape": row[0],
            "geometry": row[1],
            "height": row[2]
        }

    # ----------------------------------

    def similarity(self, a, b):
        return SequenceMatcher(None, a, b).ratio()

    # ----------------------------------
    # Main pipeline
    # ----------------------------------

    def find_waypoint_closest_and_update(self, validated):

        site_id = validated["site_id"]
        waypoint_names = self.get_waypoint_names(site_id)
        waypoints = validated["model_for_extraction_json_output"].get("waypoints", [])

        THRESHOLD = 0.6

        for wp in waypoints:

            location = wp.get("location")
            if isinstance(location, list):
                continue

            if not location:
                wp["location"] = None
                continue

            if isinstance(location, str):
                location_lower = location.lower()

            # Fuzzy match
            if location_lower not in waypoint_names:

                scores = {
                    name: self.similarity(location_lower, name)
                    for name in waypoint_names
                }

                best_name, best_score = max(scores.items(), key=lambda x: x[1])

                if best_score < THRESHOLD:
                    wp["location"] = None
                    continue

                location_lower = best_name

            # ----------------------------------
            # Fetch annotation + calculate center
            # ----------------------------------

            annotation_row = self.get_annotation_row_by_name(site_id, location_lower)

            if not annotation_row:
                wp["location"] = None
                continue

            center = GeometryCenterCalculator.calculate(annotation_row)

            # Replace string with coordinates
            wp["location"] = center

        return validated


# ---------------- Test ----------------

if __name__ == "__main__":

    c = ConnectToDb()

    validated = {
        "site_id": 1,
        "model_for_extraction_json_output": {
            "waypoints": [
                {"sequence": 1, "location": "dock"},
                {"sequence": 2, "location": "warehouse loading dock"},
                {"sequence": 3, "location": "control room access"}
            ]
        }
    }

    print(c.find_waypoint_closest_and_update(validated))
