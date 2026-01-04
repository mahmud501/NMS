import time
from modules.db import get_db
from modules.snmp_poller import snmp_walk

def poll_arp():
    """
    Poll all devices for ARP table and insert into arp_table.
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

        # Poll ifTable for interface names
        if_table_oid = "1.3.6.1.2.1.2.2.1.2"
        if_data = snmp_walk(ip, if_table_oid, device)
        # print (f"Interface WALK result for {ip}: {if_data}")
        if_names = {}
        if if_data:
            for oid, value in if_data.items():
                parts = oid.split('.')
                if len(parts) == 11:
                    if_index = int(parts[-1])
                    if_names[if_index] = value

        # print (f"Interface names for {ip}: {if_names}")
        # Poll ARP table
        arp_table_oid = "1.3.6.1.2.1.4.22.1.2"   #"1.3.6.1.2.1.4.22" orignal oid
        arp_data = snmp_walk(ip, arp_table_oid, device)
        # print (f"ARP WALK result for {ip}: {arp_data}")

        if not arp_data:
            print(f"No ARP data for device {ip}")
            continue

        for oid, value in arp_data.items():
            parts = oid.split('.')
            if len(parts) < 15:
                continue
            if_index = int(parts[-5])
            ip_address = '.'.join(parts[-4:])
            mac_address = value
            if mac_address and len(mac_address) == 14:
                mac_address = ':'.join(mac_address[i:i+2] for i in range(2, 14, 2))
            interface_name = if_names.get(if_index)
            # print(f"Device {ip} - Interface: {interface_name}, IP: {ip_address}, MAC: {mac_address}")

            cursor.execute("""
                SELECT COUNT(*) AS count
                FROM arp_table
                WHERE device_id = %s AND ip_address = %s AND mac_address = %s
            """, (device_id, ip_address, mac_address))
            result = cursor.fetchone()
            if result['count'] == 0:
                cursor.execute("""
                    INSERT INTO arp_table (device_id, ip_address, mac_address, interface_name, timestamp)
                    VALUES (%s, %s, %s, %s, NOW())
                """, (device_id, ip_address, mac_address, interface_name))

    db.commit()
    db.close()
    print(f"Polled ARP for {len(devices)} devices.")