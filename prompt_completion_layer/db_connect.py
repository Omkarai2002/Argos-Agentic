
from app.config import PROMPT_COMPLETION_DATABASE_CONFIG,PRODUCTION_DB_CONFIG
import mysql.connector
import psycopg
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
    def execute_query(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM prompt_conversations;")
        record = cursor.fetchall()
        print("You are connected to - ", record,"\n")
        cursor.close()
        conn.close()
# Example usage
# if __name__ == "__main__":
#     db_connector = ConnectToDb()
#     db_connector.execute_query()
#     print("dB connection successful.")
#     print(db_connector.execute_query())   