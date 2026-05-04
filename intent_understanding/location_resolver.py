
import json
from app.config import PROMPT_COMPLETION_DATABASE_CONFIG,PRODUCTION_DB_CONFIG
import mysql.connector
#import psycopg
# -----------------------------
# Logging Cursor (GLOBAL)
# -----------------------------
# class LoggingCursor(psycopg.Cursor):
#     def execute(self, query, params=None):
#         print("\nExecuting SQL:")
#         print(query.strip())

#         if params:
#             print("Params:", params)
#             try:
#                 print("Final SQL:", self.mogrify(query, params).decode())
#             except Exception:
#                 pass

#         return super().execute(query, params)


class LocationResolver:
    def __init__(self):
        #Apply logging globally
        
        # self.conn = psycopg.connect(
        #     dbname=PROMPT_COMPLETION_DATABASE_CONFIG["DB_NAME"],
        #     user=PROMPT_COMPLETION_DATABASE_CONFIG["DB_USER"],
        #     password=PROMPT_COMPLETION_DATABASE_CONFIG["DB_PASSWORD"],
        #     host=PROMPT_COMPLETION_DATABASE_CONFIG["DB_HOST"],
        #     port=PROMPT_COMPLETION_DATABASE_CONFIG["DB_PORT"],
        #     cursor_factory=LoggingCursor   #global logging
        # )
        
        self.conn=mysql.connector.connect(
            database = PRODUCTION_DB_CONFIG["PRODUCTION_DB_NAME"],
        user = PRODUCTION_DB_CONFIG["PRODUCTION_DB_USER"],
        password = PRODUCTION_DB_CONFIG["PRODUCTION_DB_PASSWORD"],
        host = PRODUCTION_DB_CONFIG["PRODUCTION_HOST"],
        port = PRODUCTION_DB_CONFIG["PRODUCTION_PORT"])

    def resolve(self,site_id,user_id,org_id):
        query = f"SELECT name FROM annotations where site_id={site_id} and organization_id={org_id};"

        with self.conn.cursor() as cursor:
            cursor.execute(query)
            results = cursor.fetchall()

        clean_list = [row[0] for row in results]
        # Optional: print first row
        # if clean_list:
        #     print(clean_list)
        print("db_result:",results)
        return results

    def close(self):
        if self.conn:
            self.conn.close()


# if __name__ == "__main__":
#     validated={'db_record_id': 'ebb37bbc-cd25-468d-b88b-63947c4a7906', 'user_id': 3, 'site_id': 2, 'org_id': 1, 'prompt': 'Fly to admin building at the speed of 3 m/s and altitude of 20 m. from there go to cricket ground at the speed of 3m/s and altitude of 25m, now go to water tank at the speed of 3m/s and altitude of 30m, then hover there for 5 sec and rtds as finish action', 'class': 'path', 'reason': 'The drone follows a fixed sequence of named locations without using relative offsets.', 'category': 'absolute_location', 'complexity': 0.6, 'model_for_extraction': 'gpt-4o', 'model_for_extraction_json_output': {'type': '', 'name': '', 'city': '', 'label_id': 0, 'total_distance': 500, 'total_duration': 400, 'finish_action': {'type': 'RTDS', 'duration': None}, 'waypoints': [{'sequence': 1, 'location': None, 'altitude': 20, 'altitude_mode': None, 'speed': 3.0, 'radius': None, 'actions': None}, {'sequence': 2, 'location': [73.67101753283364, 19.96210195236348, 0], 'altitude': 25, 'altitude_mode': None, 'speed': 3.0, 'radius': None, 'actions': None}, {'sequence': 3, 'location': None, 'altitude': 30, 'altitude_mode': None, 'speed': 3.0, 'radius': None, 'actions': [{'sequence': 1, 'type': 'HOVER', 'params': {'pitch': None, 'yaw': None, 'duration': 5, 'interval': None, 'count': None, 'zoom': None, 'distance': None}}]}], 'takeoff_config': {'altitude': None, 'altitude_mode': None, 'speed': None}, 'route_config': {'altitude': 40, 'altitude_mode': 'AGL', 'speed': 4, 'radius': 2}, 'mission_config': {'mode': 'orbit', 'base_path': [[72.8777, 19.076]], 'layers': [{'altitude': 20, 'altitude_mode': 'AGL'}, {'altitude': 30, 'altitude_mode': 'AGL'}, {'altitude': 40, 'altitude_mode': 'AGL'}], 'camera_profile': {'pitch': 0, 'yaw_mode': 'poi', 'poi': [72.8777, 19.076]}, 'yaw_step': 0, 'limits': {'max_vertical_speed': 0, 'layer_spacing': 0}}, 'dock_id': 0, 'can_select_dock': True, 'is_hidden': False, 'is_private': True, 'camera_profile': {'pitch': None, 'yaw_mode': None, 'poi': None}}}
#     resolver = LocationResolver()
#     org_id=validated["org_id"]
#     site_id=validated["site_id"]
#     user_id=validated["user_id"]
#     try:
#         data = resolver.resolve(site_id,user_id,org_id)
#     except Exception as e:
#         print("🔥 Error:", str(e))
#     finally:
#         resolver.close()