from pysnmp.hlapi import *
import re
from modules.oids import get_device_model

SYSOBJECT_OID = "1.3.6.1.2.1.1.2.0"
SYSNAME_OID = "1.3.6.1.2.1.1.5.0"
SYSDESC_OID = "1.3.6.1.2.1.1.1.0"
SERIAL_OID = "1.3.6.1.2.1.47.1.1.1.1.11.1"

MD5_auth= usmHMACMD5AuthProtocol
SHA_auth=usmHMACSHAAuthProtocol
AES_priv=usmAesCfb128Protocol
DES_priv=usmDESPrivProtocol
NO_priv = usmNoPrivProtocol

def snmp_test(ip, version, community=None, v3_user=None, auth_protocol=None,
              auth_password=None, priv_protocol=None, priv_password=None):
    """
    Test SNMP reachability and get device info.
    Returns: (reachable: bool, hostname: str, vendor: str, os_version: str, model: str, serial_number: str, error: str or None)
    """
    try:
        # --- SNMP Auth ---
        if version in ["v1", "v2c"]:
            auth = CommunityData(community, mpModel=1 if version == "v2c" else 0)
        else:
            auth_proto = SHA_auth if auth_protocol == "SHA" else MD5_auth
            priv_proto = usmNoPrivProtocol  # only auth, no priv

            auth = UsmUserData(
                userName=v3_user,
                authKey=auth_password,
                privKey=None,
                authProtocol=auth_proto,
                privProtocol=priv_proto
            )

        # --- SNMP GET ---
        iterator = getCmd(
            SnmpEngine(),
            auth,
            UdpTransportTarget((ip, 161), timeout=2, retries=2),
            ContextData(),
            ObjectType(ObjectIdentity(SYSOBJECT_OID)),
            ObjectType(ObjectIdentity(SYSNAME_OID)),
            ObjectType(ObjectIdentity(SYSDESC_OID)),
            ObjectType(ObjectIdentity(SERIAL_OID))
        )

        errorIndication, errorStatus, errorIndex, varBinds = next(iterator)

        if errorIndication:
            return False, None, None, None, None, None,None, str(errorIndication)
        if errorStatus:
            return False, None, None, None, None, None, None, str(errorStatus.prettyPrint())

        vendor_oid = varBinds[0][1].prettyPrint()
        hostname   = varBinds[1][1].prettyPrint()
        sysDescr   = varBinds[2][1].prettyPrint() if len(varBinds) > 2 else None
        serial_number = varBinds[3][1].prettyPrint() if len(varBinds) > 3 else "Unknown"
        if "No Such Object" in str(serial_number):
            serial_number = "Unknown"

        vendor, model = vendor_detect(vendor_oid)

        # Parse sysDescr
        os_version = "Unknown"
        device_type = vendor

        # if sysDescr:
        #     parts = sysDescr.split(',')
        #     if vendor == "Cisco":
        #         # Cisco format: "Cisco IOS Software, MODEL Software (...), Version VERSION, ..."
        #         for part in parts:
        #             part = part.strip()
        #             if 'Software' in part and not part.startswith('Cisco'):
        #                 words = part.split()
        #                 for word in words:
        #                     word = word.strip('()')
        #                     if word.isalnum() and not word.isdigit() and len(word) > 2 and word not in ['Software', 'IOS']:
        #                         model = word
        #                         break
        #                 if model != "Unknown":
        #                     break
                
        #         for part in parts:
        #             if 'Experimental' in part:
        #                 part=part.replace('Experimental','').strip()
        #             if 'Version' in part:
        #                 version_part = part.replace('Version', '').strip()
        #                 os_version = version_part.split()[0]
        #                 break
        #     elif vendor == "Mikrotik":
        #         # Mikrotik format: "RouterOS CHR, Model: Unknown, ..."
        #         if parts:
        #             first_part = parts[0].strip()
        #             if 'RouterOS' in first_part:
        #                 os_version = 'RouterOS'
        #                 words = first_part.split()
        #                 if len(words) > 1:
        #                     model = words[1]  # e.g., "CHR"
        #         # Model might be "Unknown" as per string, so leave as Unknown
        #     else:
        #         # Generic fallback
        #         for part in parts:
        #             if 'Version' in part:
        #                 version_part = part.replace('Version', '').strip()
        #                 os_version = version_part.split()[0]
        #                 break

        os_version, model = extract_os_model(sysDescr, model)

        return True, hostname, vendor, os_version, model, serial_number, sysDescr, None

    except Exception as e:
        return False, None, None, None, None, None, None, str(e)


def vendor_detect(vendor_oid):
    """
    Detect vendor from SYSOBJECT_OID string
    """
    vendor_map = {
            "9": "Cisco",
            "14988": "Mikrotik",
            "8072": "Linux"
        }

    if not vendor_oid:
        return "Unknown", "None"
    
    model = "None"
    vendor = "Unknown"
    matches = re.findall(r"(\d+(?:\.\d+)+)", str(vendor_oid))
    if matches:
        oid = max(matches, key=lambda s: s.count('.'))
    else:
        oid = str(vendor_oid).strip()
    
    parts = oid.split('.')
    if len(parts) >7 and parts[:6] == ['1','3','6','1','4','1']:
        enterprise_id = parts[6]
        vendor = vendor_map.get(enterprise_id, "Unknown")
    
    m_ent = re.search(r"enterprise\.(\d+)", str(vendor_oid))
    if m_ent:
        enterprise_id = m_ent.group(1)
        vendor = vendor_map.get(enterprise_id, "Unknown")
    if parts and parts[0] in ("9","14988","8072"):
        ent = parts[0]
        vendor = vendor_map.get(ent, "Unknown")
    
    if vendor_oid.startswith("1.3.6.1.4.1.9"):
        vendor = "Cisco"
    if vendor_oid.startswith("1.3.6.1.4.1.14988"):
        vendor = "Mikrotik"
    if vendor_oid.startswith("1.3.6.1.4.1.8072"):
        vendor = "Linux"
    
    match_oid = re.search(r"(?:enterprises\.|1\.3\.6\.1\.4\.1\.)([\d\.]+)$", vendor_oid)
    d_model = match_oid.group(1) if match_oid else None
    print(d_model)
    model = get_device_model(d_model)

    return vendor, model

def extract_os_model(sysDescr, model):
    """ Extract OS_Version and Model from system description """
    
    os_version = "Unknown"

    sd = sysDescr.strip()

    if "Cisco IOS Software" in sd:
        version_match = re.search(r"Version\s+([\w\.\(\):]+)", sd)
        version = version_match.group(1) if version_match else None
        
        feature = "Unknown"
        parent_match = re.search(r"\(([^)]+)\)", sd)
        if parent_match:
            paren_text = parent_match.group(1)

            fs_match = re.search(r"(ADVENTERPRISEK9|UNIVERSALK9|IPBASEK9|SECURITYK9)",paren_text)
            if fs_match:
                feature = fs_match.group(1)

            if model == "UnKnown":
                model = paren_text.split("-")[0]
        os_version = f"Cisco IOS {version} {feature}"

        return os_version, model

    if "Cisco Adaptive Security Appliance" in sd:
        version_match = re.search(r"Version\s+([\w\.\(\)]+)", sd)
        version = version_match.group(1) if version_match else "Unknown"

        if "V-ASA"  not in model:
            model_match = re.search(r"ASA\s*\d+[-\w]*", sd)
            model = model_match.group(0) if model_match else "ASA"
        os_version = f"Cisco ASA {version}"

        return os_version, model
    
    if sd.startswith("Linux"):
        parts = sd.split()
        kernel = parts[2] if len(parts) > 2 else "Unknown"
        arch = parts[-1] if parts[-1] in ("x86_64", "armv7l", "aarch64") else ""
        model = arch if arch else "Generic Linux"

        os_version = f"Linux Kernel {kernel}"
        
        return os_version, model
    
    if "RouterOS" in sd:
        os_version = "Mikrotik RouterOS"
        model = "CHR" if "CHR" in sd else "RouterBOARD"
        
        return os_version, model
    
    return os_version, model