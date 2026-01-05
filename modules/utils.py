from cryptography.fernet import Fernet
import os
from dotenv import load_dotenv

load_dotenv()

def format_time(timeticks):
    """ Convert timeticks in Human readable format """

    if timeticks is None:
        return "N/A"

    total_seconds = int(timeticks / 100)

    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    years, days = divmod(days, 365)

    time_parts=[]
    if years > 0:
        time_parts.append(f"{years}y")
    if days > 0:
        time_parts.append(f"{days}d")
    if hours > 0:
        time_parts.append(f"{hours}h")
    if minutes > 0:
        time_parts.append(f"{minutes}m")
    if seconds > 0 or not time_parts:
        time_parts.append(f"{seconds}s")

    time = " ".join(time_parts)
 
    return time    
 
key = os.getenv('SNMP_ENCRYPT_KEY').encode()
cipher = Fernet(key)

def encrypt_password(plain_password):
    if not plain_password:
        return None
    plain_bytes = plain_password.encode('utf-8')
    encrypted_bytes = cipher.encrypt(plain_bytes)
    return encrypted_bytes.decode('utf-8')

def decrypt_password(encrypted_password):
    if not encrypted_password:
        return None
    try:
        encrypted_bytes = encrypted_password.encode('utf-8')
        plain_bytes = cipher.decrypt(encrypted_bytes)
        return plain_bytes.decode('utf-8')
    except:
        return None
    
def format_speed(speed_bps):
    if speed_bps is None or speed_bps <= 0:
        return "Unknown"
    speed = float(speed_bps)
    if speed >= 1000000000:
        return f"{speed//1000000000:.0f} Gbps"
    elif speed >= 1000000:
        return f"{speed//1000000:.0f} Mbps"
    else:
        return f"{speed//1000:.0f} Kbps"