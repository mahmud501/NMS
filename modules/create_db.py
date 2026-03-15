import mysql.connector
from config import DB_CONFIG

def create_database():
    conn = mysql.connector.connect(
        host=DB_CONFIG["host"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
    )

    cursor = conn.cursor()

    db_name = DB_CONFIG["database"]

    # Create DB if it doesn't exist (idempotent)
    cursor.execute("SHOW DATABASES LIKE %s", (db_name,))
    result = cursor.fetchone()
    
    if result:
        print(f"Database '{db_name}' already exists.")
    else:
        cursor.execute(
        f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        print(f"Database '{db_name}' created successfully.")

    cursor.close()
    conn.close()