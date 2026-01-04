# OID definitions for different device types
# Standard and vendor-specific OIDs for monitoring

# Standard OIDs (RFC1213-MIB, IF-MIB, etc.)
STANDARD_OIDS = {
    'sysDescr': '1.3.6.1.2.1.1.1.0',
    'sysUpTime': '1.3.6.1.2.1.1.3.0',
    'sysName': '1.3.6.1.2.1.1.5.0',
    'sysLocation': '1.3.6.1.2.1.1.6.0',
    'sysContact': '1.3.6.1.2.1.1.4.0',
    'ifNumber': '1.3.6.1.2.1.2.1.0',
    'ifTable': '1.3.6.1.2.1.2.2',
    'ifDescr': '1.3.6.1.2.1.2.2.1.2',
    'ifOperStatus': '1.3.6.1.2.1.2.2.1.8',
    'ifInOctets': '1.3.6.1.2.1.2.2.1.10',
    'ifOutOctets': '1.3.6.1.2.1.2.2.1.16',
    'ipForwarding': '1.3.6.1.2.1.4.1.0',
}

# Cisco-specific OIDs
CISCO_OIDS = {
    # CPU and Memory
    'cpmCPUTotal5mins': '1.3.6.1.4.1.9.2.1.58.0',  # 5min CPU % (IOS)
    'cpmCPUTotal1min': '1.3.6.1.4.1.9.2.1.57.0',   # 1min CPU % (IOS)
    'cpmCPUTotal5minsNewer': '1.3.6.1.4.1.9.9.109.1.1.1.1.8',   # 5min CPU % (Newer IOS for walk)
    'ciscoMemoryPoolUsed': '1.3.6.1.4.1.9.9.48.1.1.1.5',   # Used memory (processor pool)
    'ciscoMemoryPoolFree': '1.3.6.1.4.1.9.9.48.1.1.1.6',   # Free memory (processor pool)
    # Alternative memory for switches (if pool not available)
    'oldcatalystmemused': 'iso.3.6.1.4.1.9.2.1.7.0',        # Old Catalyst used memory
    'oldcatalystmemfree': 'iso.3.6.1.4.1.9.2.1.8.0',        # Old Catalyst free memory  
    # DISK
    'hrStorageUsed': '1.3.6.1.2.1.25.2.3.1.6',              # Used storage
    'hrStorageSize': '1.3.6.1.2.1.25.2.3.1.5',            # Total storage 
    
    # Interfaces
    'ciscoInterfaceBandwidth': '1.3.6.1.4.1.9.2.2.1.1.6',     # Bandwidth
    
    # ASA specific (if applicable)
    'crasNumSessions': '1.3.6.1.4.1.9.9.392.1.3.35.0',        # ASA sessions
    
}

# Mikrotik-specific OIDs (RouterOS MIB)
MIKROTIK_OIDS = {
    # System
    'mtxrHealth': '1.3.6.1.4.1.14988.1.1.3.8.0',              # Health %
    'mtxrTemperature': '1.3.6.1.4.1.14988.1.1.3.10.0',        # Temperature
    
    # CPU
    'mtxrCpuLoad': '1.3.6.1.4.1.14988.1.1.3.11.0',            # CPU load %
    
    # Memory
    'mtxrTotalMemory': '1.3.6.1.4.1.14988.1.1.3.4.0',         # Total memory
    'mtxrFreeMemory': '1.3.6.1.4.1.14988.1.1.3.5.0',          # Free memory
    
    # Disk
    'mtxrTotalHddSpace': '1.3.6.1.4.1.14988.1.1.3.6.0',       # Total HDD
    'mtxrFreeHddSpace': '1.3.6.1.4.1.14988.1.1.3.7.0',        # Free HDD
    'hrStorageUsed': '1.3.6.1.2.1.25.2.3.1.6',              # Used storage
    'hrStorageSize': '1.3.6.1.2.1.25.2.3.1.5',            # Total storage 
    
    # Interfaces
    'mtxrInterfaceName': '1.3.6.1.4.1.14988.1.1.2.1.1.2',     # Interface names
    'mtxrInterfaceRxByte': '1.3.6.1.4.1.14988.1.1.2.1.1.3',   # RX bytes
    'mtxrInterfaceTxByte': '1.3.6.1.4.1.14988.1.1.2.1.1.4',   # TX bytes
    
    # Wireless (if applicable)
    'mtxrWlRtabAddr': '1.3.6.1.4.1.14988.1.1.2.2.1.2',        # Wireless clients
}

# Linux/Net-SNMP specific OIDs
LINUX_OIDS = {
    # CPU
    'ssCpuRawUser': '1.3.6.1.4.1.2021.11.50.0',               # CPU user %
    'ssCpuRawSystem': '1.3.6.1.4.1.2021.11.52.0',             # CPU system %
    'ssCpuRawIdle': '1.3.6.1.4.1.2021.11.53.0',               # CPU idle %
    
    # Memory
    'memTotalReal': '1.3.6.1.4.1.2021.4.5.0',                 # Total memory
    'memAvailReal': '1.3.6.1.4.1.2021.4.6.0',                 # Available memory
    'membufferused': '1.3.6.1.4.1.2021.4.14.0',               # Buffer used memory
    'memcachedused': '1.3.6.1.4.1.2021.4.15.0',               # Cached used memory
    
    # Disk
    'dskTotal': '1.3.6.1.4.1.2021.9.1.6.1',                   # Total disk
    'dskAvail': '1.3.6.1.4.1.2021.9.1.7.1',                   # Available disk
    'hrStorageUsed': '1.3.6.1.2.1.25.2.3.1.6',              # Used storage
    'hrStorageSize': '1.3.6.1.2.1.25.2.3.1.5',            # Total storage 
    
    # Load
    'laLoad1': '1.3.6.1.4.1.2021.10.1.3.1',                   # 1min load
    'laLoad5': '1.3.6.1.4.1.2021.10.1.3.2',                   # 5min load
    'laLoad15': '1.3.6.1.4.1.2021.10.1.3.3',                  # 15min load
    
    # Processes
    'hrSystemProcesses': '1.3.6.1.2.1.25.1.6.0',              # Number of processes
}

# Combined OID dictionary
DEVICE_OIDS = {
    'standard': STANDARD_OIDS,
    'cisco': {**STANDARD_OIDS, **CISCO_OIDS},
    'mikrotik': {**STANDARD_OIDS, **MIKROTIK_OIDS},
    'linux': {**STANDARD_OIDS, **LINUX_OIDS},
}

def get_oids_for_vendor(vendor):
    """
    Get OID dictionary for a specific vendor.
    Vendor should be lowercase: 'cisco', 'mikrotik', 'linux', or 'standard'
    """
    return DEVICE_OIDS.get(vendor.lower(), STANDARD_OIDS)

def get_oids_standard():
    """
    Get standard OID dictionary.
    """
    return STANDARD_OIDS

OID_OBJECT_MODEL = {
    "9.1.222" : "Cisco 7206VXR",
    "9.1.1227" : "Cisco Catalyst 3560(VIOS_L2)",
    "9.1.1902" : "Cisco ASA (V-ASA)",
}

def get_device_model(vendor_oid):
    return OID_OBJECT_MODEL.get(vendor_oid, "Unknown")
