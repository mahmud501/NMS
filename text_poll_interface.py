import time
from modules.db import get_db
from modules.snmp_poller import snmp_walk, snmp_get
# from modules.interface_poller import poll_interfaces

# poll_interfaces()

def poll_interfaces():
    # """
    # Poll all devices for interfaces and their stats.
    # Interfaces are inserted once and updated if changed.
    # Stats are inserted as time-series.
    # """
    # # db = get_db()
    # cursor = db.cursor(dictionary=True)

    # Fetch all devices with SNMP profiles
    # cursor.execute("""
    #     SELECT d.device_id, d.ip_address, s.snmp_version, s.community, s.v3_user,
    #             s.auth_protocol, s.auth_password_hash,
    #             s.priv_protocol, s.priv_password_hash
    #     FROM devices d
    #     JOIN snmp_profiles s ON d.device_id = s.device_id
    # """)
    # devices = cursor.fetchall()

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

    for device in devices:
        #device_id = device['device_id']
        ip = device["ip_address"]

        # Build proper SNMP profile dict

        # SNMP WALK for interface table
        if_table_oid = "1.3.6.1.2.1.2.2"
        ip_table_oid = "1.3.6.1.2.1.4.20.1.1"
        ip_int_table_oid = "1.3.6.1.2.1.4.20.1.2"
        if_data = snmp_walk(ip, if_table_oid, device)
        print (f"Interface WALK result for {ip}: {if_data}")
        ip_data = snmp_walk(ip, ip_int_table_oid, device)
        # ipadd_data = snmp_walk(ip, ip_table_oid, device)
        # print(f"IP Address WALK result for {ip}: {ipadd_data}")
        # print(f"IP Address WALK result for {ip}: {ip_data}")
        interface_ips = {}
        for ip_oid, ip_index in ip_data.items():
            parts = ip_oid.split('.')
            ipv4_address = ".".join(parts[-4:])
            # print(f"IP Address {ipv4_address} is associated with if_index {ip_index} ")
            interface_ips[ip_index] = ipv4_address
        # print(f"Interface to IP mapping for device {ip}: {interface_ips}")
        #print(f"SNMP WALK result for {ip}: {if_data}")

        if not if_data:
            print(f"No interface data for device {ip}")
            continue

        # Group by interface index
        interfaces = {}
        for oid, value in if_data.items():
            parts = oid.split('.')
            if len(parts) < 11:  # base (7) + entry (1) + column (1) + index (1) = 10
                continue
            if_index = int(parts[-1])
            sub_oid = f"{parts[-2]}"
            if if_index not in interfaces:
                interfaces[if_index] = {}
            interfaces[if_index][sub_oid] = value
            #print(f"Collected OID {oid} with value {value} for if_index {if_index}")

        for if_index, data in interfaces.items():
            #print(f"Data for if_index {if_index}: {data}")
            # Extract interface info
            name = data.get('2', '')  # ifDescr
            description = data.get('2', '')  # ifDescr
            admin_status = 'up' if data.get('7') == 1 else 'down'  # ifAdminStatus
            oper_status = 'up' if data.get('8') == 1 else 'down'  # ifOperStatus
            speed = data.get('5')  # ifSpeed
            mac_address = data.get('6')  # Keep as is for now
            if mac_address and len(mac_address) == 14:
                mac_address = ':'.join(mac_address[i:i+2] for i in range(2, 14, 2))
            ipv4_address = interface_ips.get(if_index, "")
            print(f"Processing Device {ip} Interface {if_index}: Name={name}, AdminStatus={admin_status}, OperStatus={oper_status}, Speed={speed}, MAC={mac_address}, IP={ipv4_address}")
        #     # Check if interface exists
        #     # cursor.execute("SELECT interface_id, name, description, admin_status, oper_status, speed, mac_address FROM interfaces WHERE device_id = %s AND if_index = %s", (device_id, if_index))
        #     # existing = cursor.fetchone()

        #     # if existing:
        #     #     # Update if changed
        #     #     if (existing['name'] != name or
        #     #         existing['description'] != description or
        #     #         existing['admin_status'] != admin_status or
        #     #         existing['oper_status'] != oper_status or
        #     #         existing['speed'] != speed or
        #     #         existing['mac_address'] != mac_address):
        #     #         cursor.execute("""
        #     #             UPDATE interfaces
        #     #             SET name = %s, description = %s, admin_status = %s, oper_status = %s, speed = %s, mac_address = %s
        #     #             WHERE interface_id = %s
        #     #         """, (name, description, admin_status, oper_status, speed, mac_address, existing['interface_id']))
        #     # else:
        #     #     # Insert new interface
        #     #     cursor.execute("""
        #     #         INSERT INTO interfaces (device_id, if_index, name, description, mac_address, speed, admin_status, oper_status)
        #     #         VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        #     #     """, (device_id, if_index, name, description, mac_address, speed, admin_status, oper_status))

        #     # # Get interface_id
        #     # if existing:
        #     #     interface_id = existing['interface_id']
        #     # else:
        #     #     interface_id = cursor.lastrowid

            # Collect stats
            in_octets = data.get('10')  # ifInOctets
            out_octets = data.get('16')  # ifOutOctets
            in_errors = data.get('14')  # ifInErrors
            out_errors = data.get('20')  # ifOutErrors

            print(f"Device {ip} Interface {if_index} - InOctets: {in_octets}, OutOctets: {out_octets}, InErrors: {in_errors}, OutErrors: {out_errors}")
        # for ip_oid, ip_value in ip_data.items():
        #     ipv4_address = ip_value
        #     if_index_oid = ip_int_oid + str(ipv4_address)
        #     ip_if_index = snmp_get(ip, if_index_oid, device)
        #     # if_name = interfaces[ip_if_index].get('2', 'Unknown') if ip_if_index in interfaces else 'Unknown'
        #     print(f"IP Address {ipv4_address} is associated with if_index {ip_if_index} ")
        # #     # Insert stats
    #         cursor.execute("""
    #             INSERT INTO interface_stats (interface_id, in_octets, out_octets, in_errors, out_errors, timestamp)
    #             VALUES (%s, %s, %s, %s, %s, NOW())
    #         """, (interface_id, in_octets, out_octets, in_errors, out_errors))

    # db.commit()
    # db.close()
    print(f"Polled interfaces for {len(devices)} devices.")

if __name__ == "__main__":
    poll_interfaces()