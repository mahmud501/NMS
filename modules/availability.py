import time
import subprocess
from modules.db import get_db
from modules.snmp_poller import snmp_get
from datetime import datetime, timedelta
from modules.utils import decrypt_password

def ping_device(ip):
    """
    Ping the device and return (reachable: bool, latency: float in ms)
    """
    try:
        cmd = ["ping", "-n", "2", "-w", "1000", ip] if subprocess.os.name == 'nt' else ["ping", "-c", "1", "-W", "1", ip]
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=4)
        end_time = time.time()
        latency = (end_time - start_time) * 1000
        if subprocess.os.name != 'nt':
            return result.returncode == 0, latency
        
        stdout = result.stdout.lower()
        if ("unreachable" in stdout or "failed" in stdout or
            "100% loss" in stdout or "request timed out" in stdout):
            return False, latency
    
        return True, latency
    except subprocess.TimeoutExpired:
        return False, 0
    except Exception as e:
        return False, 0

def check_device_availability(ip, snmp_profile):
    """
    Check device availability and uptime using ping and SNMP.
    Returns (status: str, uptime: int or None, latency: float)
    """
    # Ping for reachability
    ping_reachable, ping_latency = ping_device(ip)
    
    uptime = None
    snmp_latency = 0
    # if ping_reachable:
    uptime_oid = "1.3.6.1.2.1.1.3.0"
    start_time = time.time()
    uptime_value = snmp_get(ip, uptime_oid, snmp_profile)
    end_time = time.time()
    snmp_latency = (end_time - start_time) * 1000
    if uptime_value is not None:
        uptime = uptime_value  # timeticks    
    status = 'up' if ping_reachable or uptime else 'down'
    if ping_reachable:
        latency = ping_latency
    elif uptime:
        latency = snmp_latency
    else:
        latency=None

    return status, uptime, latency

def poll_device_availability():
    """
    Poll all devices for availability and uptime.
    """
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    # Fetch all devices with SNMP profiles
    cursor.execute("""
        SELECT d.device_id, d.ip_address, s.snmp_version, s.community, s.v3_user,
               s.auth_protocol, s.auth_password_hash, s.priv_protocol, s.priv_password_hash
        FROM devices d
        JOIN snmp_profiles s ON d.device_id = s.device_id
    """)
    devices = cursor.fetchall()
    
    for device in devices:
        device_id = device['device_id']
        ip = device['ip_address']
        device['auth_password_plain'] = decrypt_password(device['auth_password_hash'])
        device['priv_password_plain'] = decrypt_password(device['priv_password_hash'])
        
        status, uptime, latency = check_device_availability(ip, device)
        if uptime is not None:
            last_reboot = datetime.now()-timedelta(seconds=(uptime/100))
        else:
            last_reboot = None

        # Update devices table
        cursor.execute("""
            UPDATE devices
            SET status = %s, last_polled_time = NOW(), uptime = %s, last_reboot_time = %s
            WHERE device_id = %s
        """, (status, uptime, last_reboot, device_id))
        
        # Insert into device_availability
        cursor.execute("""
            INSERT INTO device_availability (device_id, status, latency, timestamp)
            VALUES (%s, %s, %s, NOW())
        """, (device_id, status, latency))
    
    db.commit()
    db.close()
    print(f"Polled {len(devices)} devices for availability and uptime.")

# def start_polling_service(interval_minutes=5):
#     """
#     Start a continuous polling service that runs every interval_minutes.
#     """
#     print(f"Starting ###availability polling service (interval: {interval_minutes} minutes)...")
#     while True:
#         try:
#             poll_device_availability()
#         except Exception as e:
#             print(f"Error during polling: {e}")
#         time.sleep(interval_minutes * 60)

# if __name__ == "__main__":
#     # Run once for testing
#     poll_device_availability()
    
#     # Uncomment to start continuous service
    # start_polling_service(interval_minutes=5)