from flask import Flask, render_template, request, redirect,url_for
from modules.db import get_db
from modules.snmp_test import snmp_test, vendor_detect
from modules.snmp_poller import snmp_get, snmp_walk
from modules.availability import ping_device

print(ping_device("10.10.20.1"))


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
db=get_db()
cursor=db.cursor(dictionary=True)
cursor.execute("""
               Select d.device_id, d.ip_address, d.device_type, s.snmp_version, s.community, s.v3_user,
                      s.auth_protocol, s.auth_password_hash,
                      s.priv_protocol, s.priv_password_hash
               FROM devices d
               JOIN snmp_profiles s ON d.device_id = s.device_id
               """)
device_list1=cursor.fetchall()
cursor.close()
db.close()
if not device_list:  
    print("No devices found in the database.")
else:
    device=device_list[0]
    ip = device["ip_address"]
    UPTIME_OID = "1.3.6.1.2.1.1.3.0"
    uptime = snmp_get(ip, UPTIME_OID, device)

    print(f"Device {ip} uptime: {uptime}")
    reachable, hostname, vendor, os_version, model, serial_number, error = snmp_test(
    ip, device["snmp_version"], 
    community=device.get("community"),
    v3_user=device.get("v3_user"),
    auth_protocol=device.get("auth_protocol"),
    auth_password=device.get("auth_password_hash"),
    priv_protocol=device.get("priv_protocol"),
    priv_password=device.get("priv_password_hash")
    )

    if reachable:
        print(f"Device {ip} is reachable, hostname: {hostname}")
        print(f"Vendor: {vendor}, OS Version: {os_version}, Model: {model}, Serial: {serial_number}")
    else:
        print(f"SNMP Test Failed: {error}")