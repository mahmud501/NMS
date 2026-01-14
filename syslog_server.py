import socket
from datetime import datetime
from modules.db import get_db

SYSLOG_UDP_PORT = 514
BUFFER_SIZE = 4096

SEVERITY_MAP = {
    0: "Emergency", 1: "Alert", 2: "Critical", 3: "Error",
    4: "Warning", 5: "Notice", 6: "Informational", 7: "Debug"
}

def get_device_id(ip):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT device_id FROM devices WHERE ip_address=%s", (ip,))
    row = cursor.fetchone()
    cursor.close()
    db.close()
    return row["device_id"] if row else None


def parse_syslog(msg):
    raw_msg = msg.decode(errors="ignore").strip()

    severity = 6   # default informational
    facility = "system"

    # If message starts with <PRI>
    if raw_msg.startswith("<") and ">" in raw_msg:
        pri = int(raw_msg[1:raw_msg.index(">")])
        facility = str(pri // 8)
        severity = pri % 8

    return raw_msg, severity, facility


def start_syslog_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", SYSLOG_UDP_PORT))
    print("[+] Syslog server started on UDP 514")

    # try:
    while True:
        data, addr = sock.recvfrom(BUFFER_SIZE)

        raw_message, severity, facility = parse_syslog(data)
        severity_text = SEVERITY_MAP.get(severity, "Unknown")
        device_ip = addr[0]
        if device_ip == "172.25.200.163":
            device_ip = "10.10.20.22"

        device_id = get_device_id(device_ip)
        
        db = get_db()
        cursor = db.cursor()

        cursor.execute("""
            INSERT INTO syslog_messages
            (device_id, device_ip, severity, severity_text, facility, message, raw_message, timestamp)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            device_id,
            device_ip,
            severity,
            severity_text,
            facility,
            raw_message[:1000],
            raw_message,
            datetime.now()
        ))

        db.commit()
        cursor.close()
        db.close()

        print(f"[SYSLOG] {device_ip} | Sev: {severity_text} {severity} | {raw_message[:80]}")
    # except KeyboardInterrupt:
    #     print("\n[!] Syslog server stopped by user")
    # finally:
    #     sock.close()


if __name__ == "__main__":
    start_syslog_server()
