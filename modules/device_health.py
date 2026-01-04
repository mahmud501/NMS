import time
from modules.db import get_db
from modules.snmp_poller import snmp_get, snmp_walk
from modules.oids import get_oids_for_vendor

def poll_device_health():
    """
    Poll all devices for health status.
    """
    db = get_db()
    cursor = db.cursor(dictionary=True)

    # Fetch all devices with SNMP profiles
    cursor.execute("""
        SELECT d.device_id, d.ip_address, d.vendor, d.os_version, s.snmp_version, s.community, s.v3_user,
                s.auth_protocol, s.auth_password_hash,
                s.priv_protocol, s.priv_password_hash
        FROM devices d
                   JOIN snmp_profiles s ON d.device_id = s.device_id
    """)
    devices = cursor.fetchall()

    for device in devices:
        device_id =  device['device_id']
        ip = device['ip_address']
        vendor = device['vendor']

        oids= get_oids_for_vendor(vendor)
        
        if vendor.lower() == "cisco":
            #cpu_oid = "1.3.6.1.4.1.9.9.109.1.1.1.1.8.1" 
            #cpu_oid = "1.3.6.1.4.1.9.2.1.57.0"
            cpu_oid = oids.get("cpmCPUTotal5mins")
            cpu_oid_new = oids.get("cpmCPUTotal5minsNewer")
            mem_used_oid = oids.get("ciscoMemoryPoolUsed")
            mem_free_oid = oids.get("ciscoMemoryPoolFree")
            mem_used_old_oid = oids.get("oldcatalystmemused")
            mem_free_old_oid = oids.get("oldcatalystmemfree")
            # mem_used_walk_oid = oids.get("hrStorageUsed")
            # mem_free_walk_oid = oids.get("hrStorageSize")
            disk_total_oid = oids.get("hrStorageSize")
            disk_used_oid = oids.get("hrStorageUsed")

            
            cpu = snmp_get(ip, cpu_oid, device)
            if cpu is None:
                cpu_walk = snmp_walk(ip, cpu_oid_new, device)
                cpu=sum(v for v in cpu_walk.values() if v is not None)

            mem_use_walk = snmp_walk(ip, mem_used_oid, device)
            mem_used=sum(v for v in mem_use_walk.values() if v is not None)
            #print(f"mem_used initial value for device {ip}: {mem_used}")
            if mem_used ==0:
                mem_used = snmp_get(ip, mem_used_old_oid, device)
                #print(f"Using old catalyst mem used OID for device {ip}, value: {mem_used}")

            mem_free_walk = snmp_walk(ip, mem_free_oid, device)
            mem_free=sum(v for v in mem_free_walk.values() if v is not None)
            #print(f"mem_free initial value for device {ip}: {mem_free}")
            if mem_free==0:
                mem_free=snmp_get(ip, mem_free_old_oid, device)
                #print(f"Using old catalyst mem free OID for device {ip}, value: {mem_free}")

            mem_total = mem_used + mem_free if mem_used is not None and mem_free is not None else None
            memory_used_pct = (mem_used / mem_total * 100) if mem_total else None
            #print(f"Device {ip} (Cisco), CPU OID: {cpu_oid}, CPU: {cpu}, Used: {mem_used}, Free: {mem_free}, Total: {mem_total}, Used %: {memory_used_pct}")
            disk_used = snmp_get(ip, disk_used_oid, device)
            disk_total = snmp_get(ip, disk_total_oid, device)
            disk_used_pct = (disk_used / disk_total * 100) if disk_total is not None and disk_used is not None else None

        elif vendor.lower() == "mikrotik":
            cpu_oid = oids.get("mtxrCpuLoad")
            mem_total_oid = oids.get("mtxrTotalMemory")
            mem_free_oid = oids.get("mtxrFreeMemory")
            disk_total_oid = oids.get("hrStorageSize")
            disk_used_oid = oids.get("hrStorageUsed")

            cpu = snmp_get(ip, cpu_oid, device)
            mem_total = snmp_get(ip, mem_total_oid, device)
            mem_free = snmp_get(ip, mem_free_oid, device)
            mem_used = mem_total - mem_free if mem_total is not None and mem_free is not None else None
            memory_used_pct = (mem_used / mem_total * 100) if mem_total else None
            #print(f"Device {ip} (Mikrotik), CPU OID: {cpu_oid}, CPU: {cpu}, Mem Total OID: {mem_total_oid}, Total: {mem_total}, Free: {mem_free}, Used: {mem_used}, Used %: {memory_used_pct}")
            disk_used = snmp_get(ip, disk_used_oid, device)
            disk_total = snmp_get(ip, disk_total_oid, device)
            disk_used_pct = (disk_used / disk_total * 100) if disk_total is not None and disk_total != 0 and disk_used is not None else None

        elif vendor.lower() == "linux":
            cpu_oid = oids.get("laLoad5")
            mem_total_oid = oids.get("memTotalReal")
            mem_free_oid = oids.get("memAvailReal")
            disk_used_oid = oids.get("hrStorageUsed")
            disk_total_oid = oids.get("hrStorageSize")

            cpu = snmp_get(ip, cpu_oid, device)
            mem_total = snmp_get(ip, mem_total_oid, device)
            mem_free = snmp_get(ip, mem_free_oid, device)
            mem_used = mem_total - mem_free if mem_total is not None and mem_free is not None else None
            memory_used_pct = (mem_used / mem_total * 100) if mem_total else None
            disk_use_walk = snmp_walk(ip, disk_used_oid, device)
            disk_total_walk = snmp_walk(ip, disk_total_oid, device)
            disk_used=sum(v for v in disk_use_walk.values() if v is not None)
            disk_total=sum(v for v in disk_total_walk.values() if v is not None)
            disk_used_pct = (disk_used / disk_total * 100) if disk_total is not None and disk_total !=0 and disk_used is not None else None
            #print(f"Device {ip} (Linux), CPU OID: {cpu_oid}, CPU: {cpu}, Mem Total OID: {mem_total_oid}, Total: {mem_total}, Free: {mem_free}, Used: {mem_used}, Used %: {memory_used_pct}")
        else:
            cpu = None
            memory_used_pct = None
            disk_used_pct = None

            # Update devices table
        cursor.execute("""
            INSERT INTO device_health (device_id, cpu_usage_pct, memory_usage_pct, disk_usage_pct, timestamp)
                       VALUES (%s, %s, %s, %s, NOW())
                       """, (device_id, cpu, memory_used_pct, disk_used_pct))
        
    db.commit()
    db.close()
    print(f"Polled {len(devices)} devices for health status.")


if __name__ == "__main__":
    poll_device_health()
