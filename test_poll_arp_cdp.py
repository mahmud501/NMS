import time
from modules.db import get_db
from modules.snmp_poller import snmp_walk
# from modules.arp_poller import poll_arp
# from modules.cdp_poller import poll_cdp

# poll_arp()

# def poll_arp():
#     print("Starting ARP poller test...")
#     # """
#     # Poll all devices for ARP table and insert into arp_table.
#     # """
#     # db = get_db()
#     # cursor = db.cursor(dictionary=True)

#     # # Fetch all devices with SNMP profiles
#     # cursor.execute("""
#     #     SELECT d.device_id, d.ip_address, s.snmp_version, s.community, s.v3_user,
#     #             s.auth_protocol, s.auth_password_hash,
#     #             s.priv_protocol, s.priv_password_hash
#     #     FROM devices d
#     #     JOIN snmp_profiles s ON d.device_id = s.device_id
#     # """)
#     # devices = cursor.fetchall()
#     device_list =[
#         {
#             "ip_address": "10.10.25.1",
#             "snmp_version": "v3",
#             "community": "Mynms",
#             "v3_user": "nmsuser",
#             "auth_protocol": "SHA",
#             "auth_password_hash": "Asdf1234",
#             "priv_protocol": "NONE",
#             "priv_password_hash": ""
#         }
#     ]
#     devices = device_list  # List of devices

#     for device in devices:
#         # device_id = device['device_id']
#         ip = device["ip_address"]

#         # Build proper SNMP profile dict
#         # snmp_profile = {
#         #     "snmp_version": device.get("snmp_version", "v2c"),
#         #     "community": device.get("community", "public"),
#         #     "v3_user": device.get("v3_user", ""),
#         #     "auth_protocol": device.get("auth_protocol", ""),
#         #     "auth_password_hash": device.get("auth_password_hash", ""),
#         #     "priv_protocol": device.get("priv_protocol", ""),
#         #     "priv_password_hash": device.get("priv_password_hash", "")
#         # }

#         # Poll ifTable for interface names
#         if_table_oid = "1.3.6.1.2.1.2.2.1.2"
#         if_data = snmp_walk(ip, if_table_oid, device)
#         # print (f"Interface WALK result for {ip}: {if_data}")
#         if_names = {}
#         if if_data:
#             for oid, value in if_data.items():
#                 parts = oid.split('.')
#                 if len(parts) == 11:
#                     if_index = int(parts[-1])
#                     if_names[if_index] = value

#         # print (f"Interface names for {ip}: {if_names}")
#         # Poll ARP table
#         arp_table_oid = "1.3.6.1.2.1.4.22.1.2"   #"1.3.6.1.2.1.4.22" orignal oid
#         arp_data = snmp_walk(ip, arp_table_oid, device)
#         # print (f"ARP WALK result for {ip}: {arp_data}")

#         if not arp_data:
#             print(f"No ARP data for device {ip}")
#             continue

#         # # Group by ARP entry index
#         # arp_entries = {}
#         for oid, value in arp_data.items():
#             parts = oid.split('.')
#             if len(parts) < 15:
#                 continue
#             if_index = int(parts[-5])
#             ip_address = '.'.join(parts[-4:])
#             mac_address = value
#             if mac_address and len(mac_address) == 14:
#                 mac_address = ':'.join(mac_address[i:i+2] for i in range(2, 14, 2))
#             interface_name = if_names.get(if_index)
#             print(f"Device {ip} - Interface: {interface_name}, IP: {ip_address}, MAC: {mac_address}")
#         #     arp_entries[key][sub_oid] = value

#         # for key, data in arp_entries.items():
#         #     if_index, ip_addr = key.split('_', 1)
#         #     if_index = int(if_index)
#         #     mac_hex = data.get('1.3.1')  # ipNetToMediaPhysAddress
#         #     if mac_hex:
#         #         mac_address = ':'.join(f'{int(mac_hex[i:i+2], 16):02x}' for i in range(0, len(mac_hex), 2)) if isinstance(mac_hex, str) else None
#         #     else:
#         #         mac_address = None
#         #     interface_name = if_names.get(if_index, f"Interface {if_index}")

#         #     if mac_address and ip_addr:
#     #             cursor.execute("""
#     #                 INSERT INTO arp_table (device_id, ip_address, mac_address, interface_name, timestamp)
#     #                 VALUES (%s, %s, %s, %s, NOW())
#     #             """, (device_id, ip_addr, mac_address, interface_name))

#     # db.commit()
#     # db.close()
#     print(f"Polled ARP for {len(devices)} devices.")

def poll_cdp():
    """
    Poll all devices for CDP neighbors and insert into cdp_neighbors.
    """
    device_list =[
        {
            "ip_address": "10.10.25.10",
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
        ip = device['ip_address']

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
        print (f"Inteface test: {ip}: {if_names}")
        # Poll CDP table
        cdp_table_oid = "1.3.6.1.4.1.9.9.23.1.2.1.1"
        cdp_data = snmp_walk(ip, cdp_table_oid, device)
        print (f"CDP WALK result for {ip}: {cdp_data}")

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

        print(f"CDP Entries for device {ip}: {cdp_entries}")
        for if_index, data in cdp_entries.items():
            local_interface = if_names.get(if_index, f"Interface {if_index}")
            neighbor_device = data.get(6)  # cdpCacheDevice
            neighbor_address = data.get(4)    # cdpCacheAddress
            if neighbor_address and len(neighbor_address) >= 10:
                neighbor_address = '.'.join(str(int(neighbor_address[i:i+2], 16)) for i in range(2, 10, 2))
            neighbor_platform = data.get(8)   # cdpCachePlatform
            neighbor_port = data.get(7)       # cdpCachePortID

            print(f"Device {ip} - Local Interface: {local_interface}, Neighbor Device ID: {neighbor_device}, "
                  f"Neighbor Address: {neighbor_address}, Neighbor Platform: {neighbor_platform}, "
                  f"Neighbor Port: {neighbor_port}")
    


if __name__ == "__main__":
    # poll_arp()
    poll_cdp()