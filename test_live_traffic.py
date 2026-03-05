# from modules.live_interface_bw_poller import poll_interface_bandwidth
from modules.utils import decrypt_password
from modules.snmp_poller import snmp_get
from modules.db import get_db
import time

def poll_interface_bandwidth(device_id, interface_index):
    """ 
    poll specific interface bandwidth for live graphs
    provide device_id and interface_index as parameters
    """

    db = get_db()
    cursor = db.cursor(dictionary=True)
    poll_Interval = 5

    # Fetch device info and SNMP profile
    cursor.execute("""
        SELECT d.device_id, d.ip_address, s.snmp_version, s.community, s.v3_user,
                s.auth_protocol, s.auth_password_hash,
                s.priv_protocol, s.priv_password_hash
        FROM devices d
        JOIN snmp_profiles s ON d.device_id = s.device_id
        WHERE d.device_id = %s
    """, (device_id,))
    device= cursor.fetchone()
    cursor.close()
    db.close()
    if not device:
        print(f"No device found with ID {device_id}")
        return
    ip = device['ip_address']
    device['auth_password_plain'] = decrypt_password(device['auth_password_hash'])
    device['priv_password_plain'] = decrypt_password(device['priv_password_hash'])

    # IfHCInOctets (Traffic In): .1.3.6.1.2.1.31.1.1.1.6.[interface_index]
    ifhc_in_oid = f".1.3.6.1.2.1.31.1.1.1.6.{interface_index}"
    # IfHCOutOctets (Traffic Out): .1.3.6.1.2.1.31.1.1.1.10.[interface_index]
    ifhc_out_oid = f".1.3.6.1.2.1.31.1.1.1.10.{interface_index}"

    in_octets_1 = snmp_get(ip, ifhc_in_oid, device)
    out_octets_1 = snmp_get(ip, ifhc_out_oid, device)
    print(f"Initial In Octets: {in_octets_1}, Initial Out Octets: {out_octets_1}")
    if in_octets_1 is None or out_octets_1 is None:
        print(f"Failed to retrieve initial bandwidth data for device {device_id}, interface {interface_index}")
        return
    time.sleep(poll_Interval)
    in_octets_2 = snmp_get(ip, ifhc_in_oid, device)
    out_octets_2 = snmp_get(ip, ifhc_out_oid, device)
    print(f"Second In Octets: {in_octets_2}, Second Out Octets: {out_octets_2}")
    if in_octets_2 is None or out_octets_2 is None:
        print(f"Failed to retrieve second bandwidth data for device {device_id}, interface {interface_index}")
        return
    # Calculate bandwidth in bits per second
    bandwidth_in = ((in_octets_2 - in_octets_1) * 8) / poll_Interval
    bandwidth_out = ((out_octets_2 - out_octets_1) * 8) / poll_Interval
    print(f"Bandwidth In: {bandwidth_in} bps, Bandwidth Out: {bandwidth_out} bps")  
    return bandwidth_in, bandwidth_out

while True:
    in_bps, out_bps = poll_interface_bandwidth(60, 3)
    print(f"Bandwidth In: {in_bps} bps")
    print(f"Bandwidth Out: {out_bps} bps")
    time.sleep(5)