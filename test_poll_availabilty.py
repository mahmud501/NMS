import subprocess
import time
from datetime import datetime, timedelta
from modules.snmp_poller import snmp_get

def ping_device(ip):
    """
    Ping the device and return (reachable: bool, latency: float in ms)
    """
    try:
        cmd = ["ping", "-n", "2", "-w", "1000", ip] if subprocess.os.name == 'nt' else ["ping", "-c", "1", "-W", "1", ip]
        start_time = time.time() 
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=4)
        # result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
        end_time = time.time()
        
        # print(f"[Debugging] Return code: {result.returncode}")
        # print(f"stdout: {result.stdout.strip()}")
        # print(f"stderr: {result.stderr.strip()}")
        latency = (end_time - start_time) * 1000
        # print(result)
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
        # If ping succeeds, try SNMP for uptime
    uptime_oid = "1.3.6.1.2.1.1.3.0"
    start_time = time.time()
    uptime_value = snmp_get(ip, uptime_oid, snmp_profile)
    end_time = time.time()
    snmp_latency = (end_time - start_time) * 1000
    if uptime_value is not None:
        uptime = uptime_value  # timeticks
    # device_up= ping_reachable and uptime    
    status = 'up' if ping_reachable or uptime else 'down'
    if ping_reachable:
        latency = ping_latency
    elif uptime:
        latency = snmp_latency
    else:
        latency=0

    return status, uptime, latency

def poll_device_availability():
    """
    Poll all devices for availability and uptime.
    """

    device_list =[
        {
            "ip_address": "10.10.25.1",
            "snmp_version": "v3",
            "community": "Mynms",
            "v3_user": "nmsuser",
            "auth_protocol": "SHA",
            "auth_password_hash": "Asdf1234",
            "priv_protocol": "NONE",
            "priv_password_hash": ""
        }
    ]
    devices = device_list  # List of devices

    # db = get_db()
    # cursor = db.cursor(dictionary=True)
    
    # # Fetch all devices with SNMP profiles
    # cursor.execute("""
    #     SELECT d.device_id, d.ip_address, s.snmp_version, s.community, s.v3_user,
    #            s.auth_protocol, s.auth_password_hash, s.priv_protocol, s.priv_password_hash
    #     FROM devices d
    #     JOIN snmp_profiles s ON d.device_id = s.device_id
    # """)
    # devices = cursor.fetchall()
    
    for device in devices:
        # device_id = device['device_id']
        ip = device['ip_address']
        now=datetime.now()
        status, uptime, latency = check_device_availability(ip, device) 
        last_reboot_time = now - timedelta(seconds=uptime/100)
    #     # Update devices table
    #     cursor.execute("""
    #         UPDATE devices
    #         SET status = %s, last_polled_time = NOW(), uptime = %s
    #         WHERE device_id = %s
    #     """, (status, uptime, device_id))
        
    #     # Insert into device_availability
    #     cursor.execute("""
    #         INSERT INTO device_availability (device_id, status, latency, timestamp)
    #         VALUES (%s, %s, %s, NOW())
    #     """, (device_id, status, latency))
        print(f"status: {status} uptime: {uptime} datetime: {datetime.now()} reboot_time: {last_reboot_time} latency: {latency}")    
    # db.commit()
    # db.close()
    print(f"Polled {len(devices)} devices for availability and uptime.")

poll_device_availability()