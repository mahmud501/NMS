from modules.db import get_db
from modules.snmp_test import snmp_test

 # -------------------------------
    # SNMP Test before adding to DB
    # -------------------------------
def add_devices(ip, snmp_version, community, v3_user, auth_protocol,
               auth_password, priv_protocol, priv_password):
    reachable, hostname, vendor, os_version, model, serial_number, systemDescription, error = snmp_test(
        ip, snmp_version, community,
        v3_user, auth_protocol, auth_password,
        priv_protocol, priv_password
    )

    if not reachable:
        return False, f"SNMP Test Failed: {error}"
    
    else:
        # Device info already fetched
        device_type = vendor  # or separate if needed

        # -------------------------------
        # Insert into DB
        # -------------------------------

        if snmp_version in ["v1", "v2c"]:
            auth_protocol_db = "NONE"
        else:
            auth_protocol_db = auth_protocol if auth_protocol in ["MD5", "SHA"] else "NONE"

        # Sanitize priv_protocol
        if snmp_version in ["v1", "v2c"]:
            priv_protocol_db = "NONE"
        elif priv_protocol in ["DES", "AES"]:
            priv_protocol_db = priv_protocol
        else:
            priv_protocol_db = "NONE"

        db = get_db()
        cursor = db.cursor()

        # Check if IP already exists
        cursor.execute("SELECT hostname FROM devices WHERE ip_address = %s", (ip,))
        existing = cursor.fetchone()
        if existing:
            db.close()
            return False, f"Device {existing} with IP {ip} already exists."

        cursor.execute("""
            INSERT INTO devices (hostname, ip_address, vendor, os_version, device_type, model, serial_number, sys_description, created_at, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), 'up')
        """, (hostname, ip, vendor, os_version, device_type, model, serial_number, systemDescription))

        device_id = cursor.lastrowid

        # Password hashing (only if provided)
        #_auth_pw = hashlib.sha256(auth_password.encode()).hexdigest() if auth_password else None
        #_priv_pw = hashlib.sha256(priv_password.encode()).hexdigest() if priv_password else None

        cursor.execute("""
        INSERT INTO snmp_profiles (
            device_id, snmp_version, community,
            v3_user, auth_protocol, auth_password_hash,
            priv_protocol, priv_password_hash, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, (
        device_id,
        snmp_version,
        community,
        v3_user,
        auth_protocol_db,
        auth_password,
        priv_protocol_db,
        priv_password
    ))
        db.commit()
        db.close()
        return True, f"Device {hostname} added successfully."