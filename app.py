from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from modules.db import get_db
from modules.add_devices import add_devices
from modules.utils import format_time, format_speed
from datetime import datetime, timedelta
import hashlib

app = Flask(__name__)

app.secret_key="NMS_Project"
app.jinja_env.filters['format_speed'] = format_speed

@app.route("/")
@app.route("/dashboard")
def dashboard():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM devices")
    devices = cursor.fetchall()
    cursor.execute("SELECT * FROM interfaces")
    interfaces = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template("dashboard.html", devices=devices, interfaces=interfaces)

    
@app.route("/devices/<device_type>")
def device_list(device_type):
    db=get_db()
    cursor=db.cursor(dictionary=True)

    query = " SELECT device_id, ip_address, hostname, status, model, vendor, serial_number, os_version, uptime FROM devices"

    if device_type == "up":
        query += " WHERE status = 'up'"
        page_title = "Up Devices"
    elif device_type == "down":
        query += " WHERE status = 'down'"
        page_title = "Down Devices"
    elif device_type =="all":
        page_title = "All Devices"
    else:
        page_title = "Devices"

    cursor.execute(query)
    devices= cursor.fetchall()
    cursor.close()
    db.close()
    for device in devices:
        device["formatted_uptime"]=format_time(device["uptime"])

    return render_template("device_list.html", devices=devices, page_title=page_title)

@app.route("/devices/device/<int:device_id>")
def device_details(device_id):
    
    db=get_db()
    cursor=db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM devices WHERE device_id=%s",(device_id,))
    device=cursor.fetchone()
    cursor.execute("SELECT * FROM interfaces WHERE device_id=%s",(device_id,))
    interfaces=cursor.fetchall()

    cursor.close()
    db.close()

    if not device:
        flash("Device not found!", "warning")
        return redirect(url_for("dashboard"))
    device["formatted_uptime"] = format_time(device["uptime"])

    return render_template("device_detail.html", page_title=device["ip_address"], device=device, interfaces=interfaces)

@app.route("/devices/add", methods=["GET", "POST"])
def add_device():
    if request.method == "GET":
        return render_template("add_device.html")

    # -------------------------------
    # Read form inputs
    # -------------------------------
    ip = request.form["ip_address"]
    snmp_version = request.form["snmp_version"]

    community = request.form.get("community")
    v3_user = request.form.get("v3_user")
    auth_protocol = request.form.get("auth_protocol")
    auth_password = request.form.get("auth_password")
    priv_protocol = request.form.get("priv_protocol")
    priv_password = request.form.get("priv_password")
    
    # Determine auth_level for form display
    auth_level = ""
    if snmp_version == "v3":
        if auth_protocol and auth_protocol in ["MD5", "SHA"]:
            auth_level = "authNoPriv"
        elif priv_protocol and priv_protocol in ["DES", "AES"]:
            auth_level = "authPriv"
    
    ok, device_add = add_devices(ip, snmp_version, community, v3_user, auth_protocol,
               auth_password, priv_protocol, priv_password)
    
    if ok:
        flash("Device Added Successfully", "success")
        return render_template("add_device.html", message=device_add)
    else:
        # Keep form data and show error
        flash(device_add,"error")
        return render_template("add_device.html", 
            message=device_add,
            ip_address=ip,
            snmp_version=snmp_version,
            auth_level=auth_level,
            community=community,
            v3_user=v3_user,
            auth_protocol=auth_protocol,
            priv_protocol=priv_protocol
        )

    # return redirect(f"/devices/{device_id}")

@app.route("/ports/<interface_filter>")
def interfaces_list(interface_filter="all"):
    db =get_db()
    cursor = db.cursor(dictionary=True)
    query = """ 
        SELECT i.*, d.ip_address FROM interfaces i
        JOIN devices d ON  i.device_id = d.device_id
    """

    page_title = "All Interfaces"
    if interface_filter == "up":
        query += " WHERE i.oper_status = 'up'"
        page_title = "Up Interfaces"
    elif interface_filter == 'down':
        query += " WHERE i.oper_status = 'down'"
        page_title = "Down Interfaces"
    elif interface_filter == "disabled":
        query += " WHERE i.admin_status = 'down'"
        page_title = "Disabled Interfaces"
    else:
        page_title = "Interfaces"

    cursor.execute(query)
    interfaces = cursor.fetchall()
    cursor.close()
    db.close()
    
    if not interfaces:
        return redirect(url_for("dashboard"))
    
    return render_template ("interfaces_list.html", page_title=page_title, interfaces=interfaces)

@app.route("/api/device/<int:device_id>/throughput")
def device_throughput(device_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT UNIX_TIMESTAMP(s.timestamp) * 1000 AS ts,
            SUM(s.in_bps) AS in_bps,
            SUM(s.out_bps) AS out_bps
        FROM interface_stats s
        JOIN interfaces i ON s.interface_id = i.interface_id
        WHERE i.device_id= %s
        AND s.timestamp >= NOW() - INTERVAL 1 DAY
        GROUP BY ts
        ORDER BY ts
    """, (device_id,)
    )
    result = cursor.fetchall()
    cursor.close()
    db.close()

    data = {
        "labels": [r["ts"] for r in result],
        "in": [r["in_bps"] for r in result],
        "out": [-r["out_bps"] for r in result]
    }
    
    return jsonify(data)

if __name__ == "__main__":
    app.run(debug=True)