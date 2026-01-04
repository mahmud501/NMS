import mysql.connector
from config import DB_CONFIG

def get_db():
    try:
        return mysql.connector.connect(
            host=DB_CONFIG["host"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            database=DB_CONFIG["database"]
        )
    except mysql.connector.Error as err:
        print(f"[DB ERROR] Cannot connect to MySQL: {err}")
        return None