from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from modules.reports import generate_availability_report, generate_performance_report, create_pdf_report, save_report_to_db
from modules.alerts import check_alerts, get_active_alerts, acknowledge_alert, resolve_alert
from modules.db import get_db
from modules.add_devices import add_devices
from modules.utils import format_time, format_speed
from datetime import datetime, timedelta
import hashlib
import bcrypt
import os

app = Flask(__name__)

app.secret_key="NMS_Project"
app.jinja_env.filters['format_speed'] = format_speed

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

class User(UserMixin):
    def __init__(self, user_id, username, email, role_id, role_name):
        self.id = user_id
        self.username = username
        self.email = email
        self.role_id = role_id
        self.role_name = role_name

@login_manager.user_loader
def load_user(user_id):
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return None

    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT u.user_id, u.username, u.email, u.role_id, r.role_name
        FROM users u
        JOIN roles r ON u.role_id = r.role_id
        WHERE u.user_id = %s AND u.is_active = 1
    """, (user_id,))
    row = cursor.fetchone()
    cursor.close()

    if row:
        return User(row["user_id"], row["username"], row["email"], row["role_id"], row["role_name"])
    return None


@app.route("/")
@app.route("/dashboard")
@login_required
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
@login_required
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
@login_required
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

@app.route("/devices/device/<int:device_id>/ports")
@login_required
def device_ports(device_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM interfaces WHERE device_id=%s",(device_id,))
    interfaces=cursor.fetchall()
    cursor.execute("SELECT * FROM devices WHERE device_id=%s",(device_id,))
    device=cursor.fetchone()
    cursor.close()
    db.close()

    page_title= f"{device['ip_address']}-ports"

    return render_template("device_interfaces_detail.html",page_title=page_title,interfaces=interfaces,device=device)

@app.route("/devices/add", methods=["GET", "POST"])
@login_required
def add_device():
    if current_user.role_name not in ['admin', 'operator']:
        flash('Access denied. Insufficient privileges.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == "GET":
        return render_template("add_device.html",page_title="Add Device")

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
        return redirect(url_for('device_list', device_type='all'))
    else:
        # Keep form data and show error
        flash(device_add,"error")
        return render_template("add_device.html", 
            page_title="Add Device",
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

@app.route("/device/delete")
@login_required
def delete_device():
    if current_user.role_name not in ['admin']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT device_id, ip_address FROM devices")
    devices = cursor.fetchall()
    cursor.close()
    db.close()

    return render_template("delete_device.html", page_title="Delete device", devices=devices)

@app.route("/api/device/delete/", methods=["POST"])
@login_required
def api_delete_device():
    if current_user.role_name not in ['admin']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    device_id = request.form.get("device_id")
    confirm = request.form.get("confirm_delete")

    if not device_id or not confirm:
        flash("Invalid delete request!", "error")
        return redirect(url_for("delete_device"))

    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("DELETE FROM devices WHERE device_id=%s", (device_id,))
        db.commit()
        flash("Device and all related data deleted successfully.", "success")
    except Exception as e:
        db.rollback()
        flash(f"Delete failed: {str(e)}", "error")
    finally:
        cursor.close()
        db.close()

    return redirect(url_for("device_list", device_type="all"))

@app.route("/ports/<interface_filter>")
@login_required
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
@login_required
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

@app.route("/api/device/<int:device_id>/memory")
@login_required
def device_memory(device_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT UNIX_TIMESTAMP(timestamp) * 1000 AS ts,
            memory_usage_pct AS mem_use
        FROM device_health
        WHERE device_id=%s AND timestamp >= NOW() - INTERVAL 1 DAY
        ORDER BY timestamp
    """,(device_id,))
    result=cursor.fetchall()
    data = {
        "labels": [r["ts"] for r in result],
        "memory": [r["mem_use"] for r in result]
    }

    return jsonify(data)

@app.route("/alerts")
@login_required
def alerts():
    alerts = get_active_alerts()
    return render_template("alerts.html", alerts=alerts)

@app.route("/api/alerts/acknowledge/<int:alert_id>", methods=["POST"])
@login_required
def api_acknowledge_alert(alert_id):
    acknowledge_alert(alert_id, current_user.id)
    return jsonify({"success": True})

@app.route("/reports")
@login_required
def reports():
    return render_template("reports.html")

@app.route("/reports/availability")
@login_required
def availability_report():
    data = generate_availability_report()
    return render_template("report_availability.html", data=data)

@app.route("/reports/performance")
@login_required
def performance_report():
    data = generate_performance_report()
    return render_template("report_performance.html", data=data)

@app.route("/users")
@login_required
def users():
    if current_user.role_name not in ['admin']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT u.*, r.role_name 
        FROM users u 
        JOIN roles r ON u.role_id = r.role_id 
        ORDER BY u.username
    """)
    users_list = cursor.fetchall()
    cursor.close()
    db.close()
    
    return render_template("users.html", users=users_list)

@app.route("/users/add", methods=["GET", "POST"])
@login_required
def add_user():
    if current_user.role_name not in ['admin']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == "POST":
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role_id = request.form.get('role_id')
        
        # Validate input
        if not all([username, email, password, role_id]):
            flash('All fields are required.', 'error')
            return redirect(url_for('add_user'))
        
        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        db = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, role_id)
                VALUES (%s, %s, %s, %s)
            """, (username, email, password_hash, role_id))
            db.commit()
            flash('User created successfully.', 'success')
            return redirect(url_for('users'))
        except mysql.connector.IntegrityError as e:
            db.rollback()
            if 'username' in str(e):
                flash('Username already exists.', 'error')
            elif 'email' in str(e):
                flash('Email already exists.', 'error')
            else:
                flash('Error creating user.', 'error')
        finally:
            cursor.close()
            db.close()
    
    # Get roles for dropdown
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM roles ORDER BY role_name")
    roles = cursor.fetchall()
    cursor.close()
    db.close()
    
    return render_template("add_user.html", roles=roles)

@app.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
def edit_user(user_id):
    if current_user.role_name not in ['admin']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == "POST":
        email = request.form.get('email')
        role_id = request.form.get('role_id')
        is_active = request.form.get('is_active') == 'on'
        new_password = request.form.get('new_password')
        
        db = get_db()
        cursor = db.cursor()
        try:
            if new_password:
                password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                cursor.execute("""
                    UPDATE users 
                    SET email = %s, role_id = %s, is_active = %s, password_hash = %s
                    WHERE user_id = %s
                """, (email, role_id, is_active, password_hash, user_id))
            else:
                cursor.execute("""
                    UPDATE users 
                    SET email = %s, role_id = %s, is_active = %s
                    WHERE user_id = %s
                """, (email, role_id, is_active, user_id))
            
            db.commit()
            flash('User updated successfully.', 'success')
            return redirect(url_for('users'))
        except Exception as e:
            db.rollback()
            flash('Error updating user.', 'error')
        finally:
            cursor.close()
            db.close()
    
    # Get user data
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT u.*, r.role_name 
        FROM users u 
        JOIN roles r ON u.role_id = r.role_id 
        WHERE u.user_id = %s
    """, (user_id,))
    user_data = cursor.fetchone()
    
    # Get roles
    cursor.execute("SELECT * FROM roles ORDER BY role_name")
    roles = cursor.fetchall()
    cursor.close()
    db.close()
    
    if not user_data:
        flash('User not found.', 'error')
        return redirect(url_for('users'))
    
    return render_template("edit_user.html", user=user_data, roles=roles)

@app.route("/alerts/thresholds")
@login_required
def alert_thresholds():
    if current_user.role_name not in ['admin', 'operator']:
        flash('Access denied. Admin or Operator privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT t.*, d.hostname, d.ip_address, i.name as interface_name
        FROM alert_thresholds t
        LEFT JOIN devices d ON t.device_id = d.device_id
        LEFT JOIN interfaces i ON t.interface_id = i.interface_id
        ORDER BY t.metric_type, d.hostname
    """)
    thresholds = cursor.fetchall()
    cursor.close()
    db.close()
    
    return render_template("alert_thresholds.html", thresholds=thresholds)

@app.route("/alerts/thresholds/add", methods=["GET", "POST"])
@login_required
def add_alert_threshold():
    if current_user.role_name not in ['admin', 'operator']:
        flash('Access denied. Admin or Operator privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == "POST":
        device_id = request.form.get('device_id')
        interface_id = request.form.get('interface_id') or None
        metric_type = request.form.get('metric_type')
        warning_threshold = request.form.get('warning_threshold') or None
        critical_threshold = request.form.get('critical_threshold') or None
        
        # Validate input
        if not all([device_id, metric_type]):
            flash('Device and metric type are required.', 'error')
            return redirect(url_for('add_alert_threshold'))
        
        # Convert to float if provided
        try:
            warning_threshold = float(warning_threshold) if warning_threshold else None
            critical_threshold = float(critical_threshold) if critical_threshold else None
        except ValueError:
            flash('Invalid threshold values.', 'error')
            return redirect(url_for('add_alert_threshold'))
        
        db = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("""
                INSERT INTO alert_thresholds (device_id, interface_id, metric_type, warning_threshold, critical_threshold)
                VALUES (%s, %s, %s, %s, %s)
            """, (device_id, interface_id, metric_type, warning_threshold, critical_threshold))
            db.commit()
            flash('Alert threshold created successfully.', 'success')
            return redirect(url_for('alert_thresholds'))
        except Exception as e:
            db.rollback()
            flash('Error creating alert threshold.', 'error')
        finally:
            cursor.close()
            db.close()
    
    # Get devices and interfaces for dropdowns
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT device_id, hostname, ip_address FROM devices ORDER BY hostname")
    devices = cursor.fetchall()
    
    cursor.execute("""
        SELECT i.interface_id, i.name, d.hostname, d.ip_address
        FROM interfaces i
        JOIN devices d ON i.device_id = d.device_id
        ORDER BY d.hostname, i.name
    """)
    interfaces = cursor.fetchall()
    cursor.close()
    db.close()
    
    return render_template("add_alert_threshold.html", devices=devices, interfaces=interfaces)

@app.route("/alerts/thresholds/<int:threshold_id>/edit", methods=["GET", "POST"])
@login_required
def edit_alert_threshold(threshold_id):
    if current_user.role_name not in ['admin', 'operator']:
        flash('Access denied. Admin or Operator privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == "POST":
        device_id = request.form.get('device_id')
        interface_id = request.form.get('interface_id') or None
        metric_type = request.form.get('metric_type')
        warning_threshold = request.form.get('warning_threshold') or None
        critical_threshold = request.form.get('critical_threshold') or None
        is_active = request.form.get('is_active') == 'on'
        
        # Convert to float if provided
        try:
            warning_threshold = float(warning_threshold) if warning_threshold else None
            critical_threshold = float(critical_threshold) if critical_threshold else None
        except ValueError:
            flash('Invalid threshold values.', 'error')
            return redirect(url_for('edit_alert_threshold', threshold_id=threshold_id))
        
        db = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("""
                UPDATE alert_thresholds 
                SET device_id = %s, interface_id = %s, metric_type = %s, 
                    warning_threshold = %s, critical_threshold = %s, is_active = %s
                WHERE threshold_id = %s
            """, (device_id, interface_id, metric_type, warning_threshold, critical_threshold, is_active, threshold_id))
            db.commit()
            flash('Alert threshold updated successfully.', 'success')
            return redirect(url_for('alert_thresholds'))
        except Exception as e:
            db.rollback()
            flash('Error updating alert threshold.', 'error')
        finally:
            cursor.close()
            db.close()
    
    # Get threshold data
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT t.*, d.hostname, d.ip_address, i.name as interface_name
        FROM alert_thresholds t
        LEFT JOIN devices d ON t.device_id = d.device_id
        LEFT JOIN interfaces i ON t.interface_id = i.interface_id
        WHERE t.threshold_id = %s
    """, (threshold_id,))
    threshold = cursor.fetchone()
    
    if not threshold:
        flash('Alert threshold not found.', 'error')
        cursor.close()
        db.close()
        return redirect(url_for('alert_thresholds'))
    
    # Get devices and interfaces
    cursor.execute("SELECT device_id, hostname, ip_address FROM devices ORDER BY hostname")
    devices = cursor.fetchall()
    
    cursor.execute("""
        SELECT i.interface_id, i.name, d.hostname, d.ip_address
        FROM interfaces i
        JOIN devices d ON i.device_id = d.device_id
        ORDER BY d.hostname, i.name
    """)
    interfaces = cursor.fetchall()
    cursor.close()
    db.close()
    
    return render_template("edit_alert_threshold.html", threshold=threshold, devices=devices, interfaces=interfaces)

@app.route("/alerts/thresholds/<int:threshold_id>/delete", methods=["POST"])
@login_required
def delete_alert_threshold(threshold_id):
    if current_user.role_name not in ['admin', 'operator']:
        flash('Access denied. Admin or Operator privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("DELETE FROM alert_thresholds WHERE threshold_id = %s", (threshold_id,))
        db.commit()
        flash('Alert threshold deleted successfully.', 'success')
    except Exception as e:
        db.rollback()
        flash('Error deleting alert threshold.', 'error')
    finally:
        cursor.close()
        db.close()
    
    return redirect(url_for('alert_thresholds'))

@app.route("/alerts/check", methods=["POST"])
@login_required
def check_alerts_route():
    check_alerts()
    flash("Alert check completed", "success")
    return redirect(url_for("alerts"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')

        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT u.user_id, u.username, u.email, 
                u.password_hash, u.role_id, r.role_name 
                FROM users u 
                JOIN roles r ON u.role_id = r.role_id 
                WHERE u.username = %s AND u.is_active = 1
            """, 
                (username,))
        user_data = cursor.fetchone()
        cursor.close()
        db.close()

        if user_data and bcrypt.checkpw(password.encode('utf-8'), user_data['password_hash'].encode('utf-8')):
            user = User(user_data['user_id'], user_data['username'], user_data['email'], user_data['role_id'], user_data['role_name'])
            login_user(user)

            # Update last login
            db = get_db()
            cursor = db.cursor()
            cursor.execute("UPDATE users SET last_login = NOW() WHERE user_id = %s", (user_data['user_id'],))
            db.commit()
            cursor.close()
            db.close()

            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')

    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)