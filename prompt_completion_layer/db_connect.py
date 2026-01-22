import psycopg
from app.config import DATABASE_CONFIG

class ConnectToDb:
    def __init__(self):
        self.dbname = DATABASE_CONFIG["DB_NAME"]
        self.user = DATABASE_CONFIG["DB_USER"]
        self.password = DATABASE_CONFIG["DB_PASSWORD"]
        self.host = DATABASE_CONFIG["DB_HOST"]
        self.port = DATABASE_CONFIG["DB_PORT"]

    def get_connection(self):
        conn = psycopg.connect(
            dbname=self.dbname,
            user=self.user,
            password=self.password,
            host=self.host,
            port=self.port
        )
        return conn
    
    def execute_query(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM prompt_conversations;")
        record = cursor.fetchall()
        print("You are connected to - ", record,"\n")
        cursor.close()
        conn.close()
# Example usage
if __name__ == "__main__":
    db_connector = ConnectToDb()
    db_connector.execute_query()
    print("dB connection successful.")
    print(db_connector.execute_query())   