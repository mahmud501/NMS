from cryptography.fernet import Fernet
import bcrypt
import os
from dotenv import load_dotenv

load_dotenv()

# Fernet key for SNMP credentials (two-way encryption)
snmp_key = os.getenv('SNMP_ENCRYPT_KEY').encode()
snmp_cipher = Fernet(snmp_key)

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

# ===== SNMP CREDENTIALS (Two-way encryption) =====
def encrypt_snmp_password(plain_password):
    """Encrypt SNMP passwords using Fernet (reversible)"""
    if not plain_password:
        return None
    plain_bytes = plain_password.encode('utf-8')
    encrypted_bytes = snmp_cipher.encrypt(plain_bytes)
    return encrypted_bytes.decode('utf-8')

def decrypt_snmp_password(encrypted_password):
    """Decrypt SNMP passwords using Fernet"""
    if not encrypted_password:
        return None
    try:
        encrypted_bytes = encrypted_password.encode('utf-8')
        plain_bytes = snmp_cipher.decrypt(encrypted_bytes)
        return plain_bytes.decode('utf-8')
    except:
        return None

# ===== USER PASSWORDS (One-way hashing) =====
def hash_user_password(plain_password):
    """Hash user passwords using bcrypt (irreversible)"""
    if not plain_password:
        return None
    hashed_bytes = bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt())
    return hashed_bytes.decode('utf-8')

def verify_user_password(plain_password, hashed_password):
    """Verify user password against hash"""
    if not plain_password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except:
        return False

# ===== BACKWARD COMPATIBILITY =====
# Keep old function names for existing code
encrypt_password = encrypt_snmp_password
decrypt_password = decrypt_snmp_password
    
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