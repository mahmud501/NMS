import time
from modules.snmp_poller import snmp_walk

def poll_interfaces():
    """
    Test poller for interface details including IPv4 and subnet.
    Prints results only (no DB insert).
    """
    device_list =[
        {
            "ip_address": "10.10.2.1",
            "snmp_version": "v3",
            "community": "Mynms",
            "v3_user": "nmsuser",
            "auth_protocol": "SHA",
            "auth_password_plain": "Asdf1234",
            "priv_protocol": "NONE",
            "priv_password_plain": None,
        }
    ]

    devices = device_list

    for device in devices:
        ip = device['ip_address']

        # Poll ifTable
        if_table_oid = "1.3.6.1.2.1.2.2"
        if_data = snmp_walk(ip, if_table_oid, device)

        # Poll IP → ifIndex
        ip_int_table_oid = "1.3.6.1.2.1.4.20.1.2"
        ip_data = snmp_walk(ip, ip_int_table_oid, device)

        # Poll IP → Netmask
        ip_netmask_table_oid = "1.3.6.1.2.1.4.20.1.3"
        ip_netmask_data = snmp_walk(ip, ip_netmask_table_oid, device)

        if not if_data:
            print(f"No interface data for device {ip}")
            continue

        # Build IP + subnet mapping
        interface_ips = {}
        for ip_oid, if_index in ip_data.items():
            parts = ip_oid.split('.')
            ipv4_address = ".".join(parts[-4:])
            interface_ips[if_index] = ipv4_address

        interface_ip_mask = {}
        for ip_oid, netmask in ip_netmask_data.items():
            parts = ip_oid.split('.')
            ipv4_address = ".".join(parts[-4:])
            netmask = netmask.encode("latin1")
            netmask = '.'.join(str(b) for b in netmask)
            interface_ip_mask[ipv4_address]= netmask

        print(f"IP Mapping for {ip}: {interface_ips}")
        print(f"netmask mapping for {ip}: {interface_ip_mask}")

        # Group interfaces
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

        print(f"Interface Raw Data for {ip}: {interfaces}")

        # Extract and print interface details
        for if_index, data in interfaces.items():
            name = data.get('2', '')
            admin_status = 'up' if data.get('7') == 1 else 'down'
            oper_status = 'up' if data.get('8') == 1 else 'down'
            mtu = data.get('4')
            speed = data.get('5')
            mac_address = data.get('6')

            if mac_address and len(mac_address) == 14:
                mac_address = ':'.join(mac_address[i:i+2] for i in range(2, 14, 2))

            ipv4_address = interface_ips.get(if_index, "")
            netmask = interface_ip_mask.get(ipv4_address,"")

            print(
                f"Device {ip} - Interface Index: {if_index}, "
                f"Name: {name}, Admin: {admin_status}, Oper: {oper_status}, "
                f"MTU: {mtu}, Speed: {speed}, MAC: {mac_address}, "
                f"IPv4: {ipv4_address}"
                f"netmask: {netmask}"
            )


if __name__ == "__main__":
    poll_interfaces()
