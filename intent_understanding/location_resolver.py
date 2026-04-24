
import json
from app.config import PROMPT_COMPLETION_DATABASE_CONFIG,PRODUCTION_DB_CONFIG
import mysql.connector
#import psycopg
# -----------------------------
# 🧠 Logging Cursor (GLOBAL)
# -----------------------------
# class LoggingCursor(psycopg.Cursor):
#     def execute(self, query, params=None):
#         print("\n🧾 Executing SQL:")
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

        return results

    def close(self):
        if self.conn:
            self.conn.close()


# if __name__ == "__main__":
#     resolver = LocationResolver()

#     try:
#         data = resolver.resolve()
#     except Exception as e:
#         print("🔥 Error:", str(e))
#     finally:
#         resolver.close()