import psycopg
from difflib import SequenceMatcher
import logging
from app.config import PROMPT_COMPLETION_DATABASE_CONFIG

logger = logging.getLogger(__name__)


class ConnectToDb:

    def __init__(self):
        self.dbname = PROMPT_COMPLETION_DATABASE_CONFIG["DB_NAME"]
        self.user = PROMPT_COMPLETION_DATABASE_CONFIG["DB_USER"]
        self.password = PROMPT_COMPLETION_DATABASE_CONFIG["DB_PASSWORD"]
        self.host = PROMPT_COMPLETION_DATABASE_CONFIG["DB_HOST"]
        self.port = PROMPT_COMPLETION_DATABASE_CONFIG["DB_PORT"]

    def get_connection(self):
        try:
            return psycopg.connect(
                dbname=self.dbname,
                user=self.user,
                password=self.password,
                host=self.host,
                port=self.port
            )
        except Exception as e:
            logger.error(f"DB connection failed: {e}")
            raise

    def get_waypoint_names(self, site_id):
        """
        Fetch all geofence names for given site
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            query = "SELECT name FROM geofence WHERE site_id=%s;"
            cursor.execute(query, (site_id,))

            rows = cursor.fetchall()
            conn.close()

            return [row[0].lower() for row in rows]

        except Exception as e:
            logger.error(f"Error fetching waypoint names: {e}")
            raise

    def similarity(self, a, b):
        return SequenceMatcher(None, a, b).ratio()

    def find_waypoint_closest_and_update(self, validated):

        try:
            site_id = validated["site_id"]
            waypoint_names = self.get_waypoint_names(site_id)

            waypoints = validated["model_for_extraction_json_output"].get("waypoints", [])

            THRESHOLD = 0.6

            for idx, wp in enumerate(waypoints, start=1):

                location = wp.get("location")

                if not location:
                    wp["location"] = None

                    continue

                location_lower = location.lower()

                if location_lower in waypoint_names:
                    continue

                scores = {
                    name: self.similarity(location_lower, name)
                    for name in waypoint_names
                }

                best_name, best_score = max(scores.items(), key=lambda x: x[1])

                if best_score >= THRESHOLD:
                    
                    wp["location"] = best_name
                else:
                    
                    wp["location"] = None
    
            return validated

        except Exception as e:
            logger.error(f"Error in waypoint correction: {e}")
            raise



c=ConnectToDb()
validated={'db_record_id': '129', 'user_id': 1, 'site_id': 1, 'org_id': 1, 'prompt': 'Create a point mission where the drone flies from the dock to a target GPS coordinate, performs a clockwise loiter with 25 m radius at 60 m altitude for 90 seconds, then returns to the dock.', 'class': 'point', 'reason': 'The primary task occurs during a stationary loiter at a target point after travel, not while continuously moving.', 'complexity': 0.4, 'model_for_extraction': 'gpt-5-nano', 'model_for_extraction_json_output': {'type': '', 'name': '', 'city': '', 'label_id': 0, 'total_distance': 500, 'total_duration': 400, 'finish_action': {'type': 'RTL', 'duration': None}, 'waypoints': [{'sequence': 1, 'location': 'dock', 'altitude': None, 'altitude_mode': None, 'speed': None, 'radius': None, 'actions': []}, {'sequence': 2, 'location': None, 'altitude': None, 'altitude_mode': None, 'speed': None, 'radius': 25.0, 'actions': [{'sequence': 1, 'type': 'HOVER', 'params': {'pitch': None, 'yaw': None, 'duration': 90, 'interval': None, 'count': None, 'zoom': None, 'distance': None}}]}, {'sequence': 3, 'location': 'dock', 'altitude': None, 'altitude_mode': None, 'speed': None, 'radius': None, 'actions': []}], 'takeoff_config': {'altitude': None, 'altitude_mode': None, 'speed': None}, 'route_config': {'altitude': 40, 'altitude_mode': 'AGL', 'speed': 4, 'radius': 2}, 'mission_config': {'mode': 'orbit', 'base_path': [[72.8777, 19.076]], 'layers': [{'altitude': 20, 'altitude_mode': 'AGL'}, {'altitude': 30, 'altitude_mode': 'AGL'}, {'altitude': 40, 'altitude_mode': 'AGL'}], 'camera_profile': {'pitch': 0, 'yaw_mode': 'poi', 'poi': [72.8777, 19.076]}, 'yaw_step': 0, 'limits': {'max_vertical_speed': 0, 'layer_spacing': 0}}, 'dock_id': 0, 'can_select_dock': True, 'is_hidden': False, 'is_private': True, 'camera_profile': {'pitch': None, 'yaw_mode': None, 'poi': None}}}
print(c.find_waypoint_closest_and_update(validated))