from pysnmp.hlapi import *
import sys

SNMP_ENGINE = SnmpEngine()


#  AUTH HANDLER FOR v1, v2c, v3
def build_auth(profile):
    """
    profile example:
    {
        'snmp_version': 'v1' or 'v2c' or 'v3',
        'community': 'public',

        'v3_user': '',
        'auth_protocol': 'MD5' | 'SHA' | NONE
        'auth_password_hash': '',
        'priv_protocol': 'AES' | 'DES' | NONE
        'priv_password_hash': ''
    }
    """

    version = profile.get("snmp_version", "").lower()


    # SNMP v1
    if version == "v1":
        return CommunityData(profile["community"], mpModel=0)

    # SNMP v2c
    if version == "v2c":
        return CommunityData(profile["community"], mpModel=1)

    # SNMP v3 (3 security levels)
    if profile.get("priv_protocol", "").lower()=="none":
        profile["priv_password_hash"] = None
    #if profile.get("auth_protocol", "").lower()=="none":
    #    profile["auth_password_hash"] = None

    auth_proto_map = {
        "md5": usmHMACMD5AuthProtocol,
        "sha": usmHMACSHAAuthProtocol,
        "none": usmNoAuthProtocol,
        "": usmNoAuthProtocol
    }

    priv_proto_map = {
        "aes": usmAesCfb128Protocol,
        "des": usmDESPrivProtocol,
        "none": usmNoPrivProtocol,
        "": usmNoPrivProtocol
    }

    auth_protocol = auth_proto_map.get(profile.get("auth_protocol", "").lower(), usmNoAuthProtocol)
    priv_protocol = priv_proto_map.get(profile.get("priv_protocol", "").lower(), usmNoPrivProtocol)

    return UsmUserData(
        userName=profile.get("v3_user", ""),
        authKey=profile.get("auth_password_plain", None),
        privKey=profile.get("priv_password_plain", None),
        authProtocol=auth_protocol,
        privProtocol=priv_protocol
    )


# SNMP GET
def snmp_get(ip, oid, profile):
    try:
        auth = build_auth(profile)

        iterator = getCmd(
            SNMP_ENGINE,
            auth,
            UdpTransportTarget((ip, 161), timeout=2, retries=2),
            ContextData(),
            ObjectType(ObjectIdentity(oid))
        )

        errorIndication, errorStatus, errorIndex, varBinds = next(iterator)

        if errorIndication or errorStatus:
            print(f"[SNMP GET ERROR] {ip} {oid}: {errorIndication or errorStatus}")
            return None

        for _, value in varBinds:
            cls = value.__class__.__name__

            if cls in ["NoSuchObject", "NoSuchInstance", "EndOfMibView"]:
                return None

            if cls in ["Integer", "Counter32", "Counter64", "Gauge32", "TimeTicks"]:
                return int(value)

            return str(value)

    except Exception as e:
        print(f"[SNMP GET EXCEPTION] {ip}: {e}")
        return None


#  SNMP WALK
def snmp_walk(ip, base_oid, profile):
    result = {}

    try:
        auth = build_auth(profile)

        for (errorIndication, errorStatus, errorIndex, varBinds) in nextCmd(
                SNMP_ENGINE,
                auth,
                UdpTransportTarget((ip, 161), timeout=2, retries=2),
                ContextData(),
                ObjectType(ObjectIdentity(base_oid)),
                lexicographicMode=False
        ):
            if errorIndication or errorStatus:
                print(f"[SNMP WALK ERROR] {ip}: {errorIndication or errorStatus}")
                continue

            for name, val in varBinds:
                key = str(name)
                cls = val.__class__.__name__

                if cls in ["NoSuchObject", "NoSuchInstance", "EndOfMibView"]:
                    result[key] = None
                elif cls in ["Integer", "Counter32", "Counter64", "Gauge32", "TimeTicks"]:
                    result[key] = int(val)
                elif cls == "OctetString":
                    result[key] = val.prettyPrint()
                else:
                    result[key] = str(val)

        return result

    except Exception as e:
        print(f"[SNMP WALK EXCEPTION] {ip}: {e}")
        return {}
