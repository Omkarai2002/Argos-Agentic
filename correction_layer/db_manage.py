
from difflib import SequenceMatcher
import logging
from app.config import PROMPT_COMPLETION_DATABASE_CONFIG,PRODUCTION_DB_CONFIG
from .annotations_calculation import GeometryCenterCalculator
import mysql.connector
import psycopg
logger = logging.getLogger(__name__)


class ConnectToDb:

    def __init__(self):
        
        self.dbname = PROMPT_COMPLETION_DATABASE_CONFIG["DB_NAME"]
        self.user = PROMPT_COMPLETION_DATABASE_CONFIG["DB_USER"]
        self.password = PROMPT_COMPLETION_DATABASE_CONFIG["DB_PASSWORD"]
        self.host = PROMPT_COMPLETION_DATABASE_CONFIG["DB_HOST"]
        self.port = PROMPT_COMPLETION_DATABASE_CONFIG["DB_PORT"]
        # self.dbname = PRODUCTION_DB_CONFIG["PRODUCTION_DB_NAME"]
        # self.user = PRODUCTION_DB_CONFIG["PRODUCTION_DB_USER"]
        # self.password = PRODUCTION_DB_CONFIG["PRODUCTION_DB_PASSWORD"]
        # self.host = PRODUCTION_DB_CONFIG["PRODUCTION_HOST"]
        # self.port = PRODUCTION_DB_CONFIG["PRODUCTION_PORT"]
    def get_connection(self):
        return psycopg.connect(
            dbname=self.dbname,
            user=self.user,
            password=self.password,
            host=self.host,
            port=self.port
        )
#         return mysql.connector.connect(
#     database=self.dbname,
#     user=self.user,
#     password=self.password,
#     host=self.host,
#     port=self.port
# )

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
    def token_overlap(self,a, b):
        a_set = set(a.split())
        b_set = set(b.split())
        return len(a_set & b_set) / max(len(a_set), 1)
    
    def find_waypoint_closest_and_update(self, validated):
        try:
            site_id = validated.get("site_id")

            if not site_id:
                return validated

            # Fetch waypoint names safely
            waypoint_names = self.get_waypoint_names(site_id) or []
            waypoint_names = [
                name.lower() for name in waypoint_names
                if isinstance(name, str)
            ]

            waypoints = validated.get(
                "model_for_extraction_json_output", {}
            ).get("waypoints", [])

            THRESHOLD = 0.6

            for wp in waypoints:
                try:
                    location = wp.get("location")

                    # If already coordinates, skip
                    if isinstance(location, list):
                        continue

                    # If invalid or empty location
                    if not location or not isinstance(location, str):
                        wp["location"] = None
                        continue

                    location_lower = location.lower()

                    # If no candidates exist in DB
                    if not waypoint_names:
                        wp["location"] = None
                        continue

                    # If exact match exists
                    if location_lower in waypoint_names:
                        best_name = location_lower
                    else:
                        # Build similarity scores safely
                        scores = {}

                        for name in waypoint_names:
                            try:
                                score = max(
                                    self.similarity(location_lower, name),
                                    self.token_overlap(location_lower, name)
                                )
                                if isinstance(score, (int, float)):
                                    scores[name] = score
                            except Exception:
                                continue

                        # If similarity produced nothing
                        if not scores:
                            wp["location"] = None
                            continue

                        best_name, best_score = max(
                            scores.items(),
                            key=lambda x: x[1]
                        )

                        if best_score < THRESHOLD:
                            wp["location"] = None
                            continue

                    # Fetch annotation row safely
                    annotation_row = self.get_annotation_row_by_name(
                        site_id, best_name
                    )

                    if not annotation_row:
                        wp["location"] = None
                        continue

                    # Calculate center safely
                    try:
                        center = GeometryCenterCalculator.calculate(annotation_row)
                        wp["location"] = center
                    except Exception:
                        wp["location"] = None
                        continue

                except Exception:
                    # If anything unexpected happens in one waypoint
                    wp["location"] = None
                    continue

            return validated

        except Exception:
            # Absolute fallback safeguard
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
