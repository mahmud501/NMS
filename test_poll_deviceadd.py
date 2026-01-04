from modules.snmp_test import snmp_test


def test_device_add():

    device_list =[
        {
            "ip_address": "10.10.20.21",
            "snmp_version": "v3",
            "community": "Mynms",
            "v3_user": "nmsuser",
            "auth_protocol": "SHA",
            "auth_password_hash": "Asdf1234",
            "priv_protocol": "NONE",
            "priv_password_hash": "",
        }
    ]
    # devices=device_list[0]
    # print(devices)

    for device in device_list:
        ip = device.get("ip_address")
        print(ip)
        snmp_version = device.get("snmp_version")

        community = device.get("community")
        v3_user = device.get("v3_user")
        auth_protocol = device.get("auth_protocol")
        auth_password = device.get("auth_password_hash")
        priv_protocol = device.get("priv_protocol")
        priv_password = device.get("priv_password_hash")

        # # Determine auth_level for form display
        # auth_level = ""
        # if snmp_version == "v3":
        #     if auth_protocol and auth_protocol in ["MD5", "SHA"]:
        #         auth_level = "authNoPriv"
        #     elif priv_protocol and priv_protocol in ["DES", "AES"]:
        #         auth_level = "authPriv"
        
        reachable, hostname, vendor, os_version, model, serial_number, sysdes, error = snmp_test(
            ip, snmp_version, community,
            v3_user, auth_protocol, auth_password,
            priv_protocol, priv_password
        )
        
        print(f"{reachable} {hostname} {vendor} {os_version} {model} {serial_number} sysdes: {sysdes} {error}")
if __name__ == "__main__":
    test_device_add()