import time
from modules.db import get_db
from modules.snmp_poller import snmp_walk
from modules.utils import decrypt_password

def poll_cdp():
    """
    Poll all devices for CDP neighbors and insert into cdp_neighbors.
    """
    db = get_db()
    cursor = db.cursor(dictionary=True)

    # Fetch all devices with SNMP profiles
    cursor.execute("""
        SELECT d.device_id, d.ip_address, s.snmp_version, s.community, s.v3_user,
                s.auth_protocol, s.auth_password_hash,
                s.priv_protocol, s.priv_password_hash
        FROM devices d
        JOIN snmp_profiles s ON d.device_id = s.device_id
    """)
    devices = cursor.fetchall()

    for device in devices:
        device_id = device['device_id']
        ip = device['ip_address']
        device['auth_password_plain'] = decrypt_password(device['auth_password_hash'])
        device['priv_password_plain'] = decrypt_password(device['priv_password_hash'])

        # Poll ifTable for interface names
        if_table_oid = "1.3.6.1.2.1.2.2.1.2" #"1.3.6.1.2.1.2.2" - original oid
        if_data = snmp_walk(ip, if_table_oid, device)
        if_names = {}
        if if_data:
            for oid, value in if_data.items():
                parts = oid.split('.')
                if len(parts) == 11:
                    if_index = int(parts[-1])
                    if_names[if_index] = str(value)

        # Poll CDP table
        cdp_table_oid = "1.3.6.1.4.1.9.9.23.1.2.1.1"
        cdp_data = snmp_walk(ip, cdp_table_oid, device)

        if not cdp_data:
            print(f"No CDP data for device {ip}")
            continue

        cdp_entries = {}
        for oid, value in cdp_data.items():
            parts = oid.split('.')
            if parts and len(parts) < 16:
                continue
            if_index = int(parts[-2])
            sub_oid = int(parts[-3])
            if if_index not in cdp_entries:
                cdp_entries[if_index] = {}
            cdp_entries[if_index][sub_oid] = value

        #print(f"CDP Entries for device {ip}: {cdp_entries}")
        for if_index, data in cdp_entries.items():
            local_interface = if_names.get(if_index, f"Interface {if_index}")
            neighbor_device = data.get(6)  # cdpCacheDevice
            neighbor_address = data.get(4)    # cdpCacheAddress
            if neighbor_address and len(neighbor_address) >= 10:
                neighbor_ip = '.'.join(str(int(neighbor_address[i:i+2], 16)) for i in range(2, 10, 2))
            neighbor_platform = data.get(8)   # cdpCachePlatform
            neighbor_port = data.get(7)       # cdpCachePortID

            if neighbor_device:
                cursor.execute("""
                    SELECT cdp_id
                    FROM cdp_neighbors
                    WHERE device_id = %s AND local_interface = %s AND neighbor_device = %s AND neighbor_ip = %s
                """, (device_id, local_interface, neighbor_device, neighbor_ip))
                existing = cursor.fetchone()
                if not existing:
                    cursor.execute("""
                        INSERT INTO cdp_neighbors (device_id, local_interface, neighbor_device, neighbor_ip, neighbor_port, platform, timestamp)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    """, (device_id, local_interface, neighbor_device, neighbor_ip, neighbor_port, neighbor_platform))
                else:
                    cursor.execute("""
                        UPDATE cdp_neighbors
                        SET neighbor_port = %s, platform = %s, neighbor_ip = %s, timestamp = NOW()
                        WHERE cdp_id = %s
                    """, (neighbor_port, neighbor_platform, neighbor_ip, existing['cdp_id']))

            cursor.execute("""
                DELETE FROM cdp_neighbors
                           where device_id = %s
                                AND timestamp < NOW() - INTERVAL 1 WEEK
            """, (device_id,))

    db.commit()
    db.close()
    print(f"Polled CDP for {len(devices)} devices.")

if __name__ == "__main__":
    poll_cdp()