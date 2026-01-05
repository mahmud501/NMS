import time
from modules.db import get_db
from modules.snmp_poller import snmp_walk
from modules.utils import decrypt_password

def poll_interfaces():
    """
    Poll all devices for interfaces and their stats.
    Interfaces are inserted once and updated if changed.
    Stats are inserted as time-series.
    """
    db = get_db()
    cursor = db.cursor(dictionary=True)

    poll_Interval = 300

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

        # Build proper SNMP profile dict

        # SNMP WALK for interface table
        if_table_oid = "1.3.6.1.2.1.2.2"
        if_data = snmp_walk(ip, if_table_oid, device)
        ip_int_table_oid = "1.3.6.1.2.1.4.20.1.2"
        ip_data = snmp_walk(ip, ip_int_table_oid, device)
        ifX_table_oid = "1.3.6.1.2.1.31.1.1.1"
        ifX_data = snmp_walk(ip, ifX_table_oid, device)

        interface_ips = {}
        for ip_oid, ip_index in ip_data.items():
            parts = ip_oid.split('.')
            ipv4_address = ".".join(parts[-4:])
            interface_ips[ip_index] = ipv4_address

        if not if_data:
            print(f"No interface data for device {ip}")
            continue

        # Group by interface index
        interfaces = {}
        for oid, value in if_data.items():
            parts = oid.split('.')
            if len(parts) < 11:  
                 continue
            if_index = int(parts[-1])
            sub_oid = f"{parts[-2]}"
            if if_index not in interfaces:
                interfaces[if_index] = {}
            interfaces[if_index][sub_oid] = value
        for oid, value in ifX_data.items():
            parts = oid.split('.')
            if len(parts) >= 11 and parts[-2] == '18':
                if_index = int(parts[-1])
                if if_index in interfaces:
                    interfaces[if_index]['18'] = value

        for if_index, data in interfaces.items():
            # Extract interface info
            name = data.get('2', '')  # ifDescr
            description = data.get('18', '')  # ifDescr
            admin_status = 'up' if data.get('7') == 1 else 'down'  # ifAdminStatus
            oper_status = 'up' if data.get('8') == 1 else 'down'  # ifOperStatus
            speed = data.get('5')  # ifSpeed
            mac_address = data.get('6')  # Keep as is for now
            if mac_address and len(mac_address) == 14:
                mac_address = ':'.join(mac_address[i:i+2] for i in range(2, 14, 2))
            ipv4_address = interface_ips.get(if_index, "")

            # Check if interface exists
            cursor.execute("SELECT interface_id, name, description, admin_status, oper_status, speed, mac_address, ipv4_address FROM interfaces WHERE device_id = %s AND if_index = %s", (device_id, if_index))
            existing = cursor.fetchone()

            if existing:
                # Update if changed
                if (existing['name'] != name or
                    existing['description'] != description or
                    existing['admin_status'] != admin_status or
                    existing['oper_status'] != oper_status or
                    existing['speed'] != speed or
                    existing['mac_address'] != mac_address or
                    existing['ipv4_address'] != ipv4_address):
                    cursor.execute("""
                        UPDATE interfaces
                        SET name = %s, description = %s, admin_status = %s, oper_status = %s, speed = %s, mac_address = %s, ipv4_address = %s, updated_at = NOW()
                        WHERE interface_id = %s
                    """, (name, description, admin_status, oper_status, speed, mac_address, ipv4_address, existing['interface_id']))
            else:
                # Insert new interface
                cursor.execute("""
                    INSERT INTO interfaces (device_id, if_index, name, description, mac_address, ipv4_address, speed, admin_status, oper_status, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """, (device_id, if_index, name, description, mac_address, ipv4_address, speed, admin_status, oper_status))

            # Get interface_id
            if existing:
                interface_id = existing['interface_id']
            else:
                interface_id = cursor.lastrowid

            cursor.execute("""
                SELECT in_octets, out_octets
                FROM interface_stats
                WHERE interface_id = %s
                ORDER BY timestamp DESC
                LIMIT 1
            """, (interface_id,))
            
            prev = cursor.fetchone()

            # Collect stats
            in_octets = data.get('10', 0)  # ifInOctets
            out_octets = data.get('16', 0)  # ifOutOctets
            in_errors = data.get('14', 0)  # ifInErrors
            out_errors = data.get('20', 0)  # ifOutErrors

            in_bps = 0
            out_bps = 0

            if prev:
                prev_in = int(prev['in_octets'])
                prev_out = int(prev['out_octets'])

                if in_octets >= prev_in:
                    in_bps = ((in_octets-prev_in)*8)//poll_Interval
                if out_octets >= prev_out:
                    out_bps = ((out_octets-prev_out)*8)//poll_Interval

            # Insert stats
            cursor.execute("""
                INSERT INTO interface_stats (interface_id, in_octets, out_octets, in_bps, out_bps, in_errors, out_errors, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """, (interface_id, in_octets, out_octets, in_bps, out_bps, in_errors, out_errors))

    db.commit()
    db.close()
    print(f"Polled interfaces for {len(devices)} devices.")

if __name__ == "__main__":
    poll_interfaces()