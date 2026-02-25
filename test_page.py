from modules.oids import get_device_model
from modules.notifications import create_default_notification_settings
from modules.db import get_db

def create_default_notification_settings():
    """Create default notification settings for all users."""
    db = get_db()
    cursor = db.cursor(dictionary=True)

    try:
        # Get all users
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()

        for user in users:
            # Check if settings already exist
            cursor.execute("SELECT setting_id FROM notification_settings WHERE user_id = %s", (user['user_id'],))
            existing = cursor.fetchone()
            cursor.fetchall()

            if not existing:
                # Create default settings for warning and critical alerts
                cursor.execute("""
                    INSERT INTO notification_settings (user_id, alert_severity, email_enabled)
                    VALUES (%s, 'warning', TRUE), (%s, 'critical', TRUE)
                """, (user['user_id'], user['user_id']))

        db.commit()
        print("Created default notification settings for all users")

    except Exception as e:
        print(f"Error creating default notification settings: {e}")
        db.rollback()
    finally:
        cursor.close()
        db.close()

create_default_notification_settings()

# query = " SELECT device_id, ip_address, hostname, status, model, serial_number, os_version, uptime FROM devices"
# query += " WHERE status = 'up'"
# print(query)
# from modules.utils import format_time
# print(format_time(12700788))

# # Test it
# print(format_time(12700788))  # → 1d 11h 16m 47s
# print(format_time(45))        # → 45s
# print(format_time(3661))      # → 1h 1m 1s
# print(format_time(90061))     # → 1d 1h 1m 1s
# print(format_time(0))         # → 0s
# model = get_device_model("enterprises.9.1.222")
# print(model)
import os
# from dotenv import load_dotenv
from cryptography.fernet import Fernet

# # load_dotenv() # Loads the .env file into the environment
# key = os.getenv('SNMP_ENCRYPT_KEY')
# print(key)

key = os.getenv("SNMP_ENCRYPT_KEY").encode()
cipher = Fernet(key)

# When adding a device
plain_password = "mysecretpassword"
plain_bytes= plain_password.encode('utf-8')
print(plain_bytes)
encrypted_password = cipher.encrypt(plain_bytes).decode()
print(encrypted_password)

plain_test = cipher.decrypt(encrypted_password.encode()).decode()
print(plain_test)
