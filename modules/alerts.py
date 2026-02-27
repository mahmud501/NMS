import time
from modules.db import get_db
from modules.snmp_poller import snmp_get
from datetime import datetime
from modules.utils import decrypt_password
from modules.notifications import send_alert_notifications

def check_alerts():
    """
    Check all active alert thresholds and generate alerts if conditions are met.
    Also auto-resolve alerts when conditions return to normal.
    """
    db = get_db()
    cursor = db.cursor(dictionary=True)

    # First, check for alerts that should be resolved (conditions back to normal)
    cursor.execute("""
        SELECT a.alert_id, a.device_id, a.interface_id, a.alert_type, t.warning_threshold, t.critical_threshold, d.ip_address
        FROM alerts a
        LEFT JOIN alert_thresholds t ON 
            a.device_id = t.device_id AND 
            COALESCE(a.interface_id, 0) = COALESCE(t.interface_id, 0) AND 
            a.alert_type = t.metric_type
        LEFT JOIN devices d ON a.device_id=d.device_id
        WHERE a.resolved_at IS NULL
    """)
    unresolved_alerts = cursor.fetchall()
    alerts_generated = []

    for alert in unresolved_alerts:
        alert_id = alert['alert_id']
        device_id = alert['device_id']
        interface_id = alert['interface_id']
        metric_type = alert['alert_type']
        warning_threshold = alert['warning_threshold']
        critical_threshold = alert['critical_threshold']

        should_resolve = False
        # Resolve alert if alter threshold has been deleted     
        if not warning_threshold and not critical_threshold and metric_type !="down":
            should_resolve = True
            severity = "info"
            if should_resolve:
                resolve_alert(alert_id)
                alert_data = {
                    'alert_id': alert_id,
                    'device_name': f'Device ID: {device_id} Alert ID:{alert_id}',
                    'device_ip': alert['ip_address'],
                    'severity': severity,
                    'message': 'Alert Threshold Deleted',
                    'alert_type': metric_type,
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                alerts_generated.append(alert_data)
        # Get current value
        if metric_type == "down":
            cursor.execute("""
                SELECT status FROM device_availability
                WHERE device_id=%s 
                ORDER BY timestamp DESC
                LIMIT 1
            """, (device_id,))
            result = cursor.fetchone()
            should_resolve = False
            if result['status'].lower() == 'up':
                should_resolve=True
                severity = "info"
            if should_resolve:
                # Auto-resolve the alert
                resolve_alert(alert_id)
                print(f"Auto-resolved alert {alert_id} - {device_id} is Up now")
                alert_data = {
                    'alert_id': alert_id,
                    'device_name': f'{device_id}',
                    'device_ip': alert['ip_address'],
                    'severity': severity,
                    'message': f'{alert["ip_address"]} is Up',
                    'alert_type': metric_type,
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                alerts_generated.append(alert_data)
        else:
            if metric_type == 'cpu':
                cursor.execute("""
                    SELECT cpu_usage_pct as value
                    FROM device_health
                    WHERE device_id = %s
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, (device_id,))
            elif metric_type == 'memory':
                cursor.execute("""
                    SELECT memory_usage_pct as value
                    FROM device_health
                    WHERE device_id = %s
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, (device_id,))
            elif metric_type == 'disk':
                cursor.execute("""
                    SELECT disk_usage_pct as value
                    FROM device_health
                    WHERE device_id = %s
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, (device_id,))
            elif metric_type == 'interface_traffic':
                cursor.execute("""
                    SELECT (in_bps + out_bps) / 1000000 as value
                    FROM interface_stats
                    WHERE interface_id = %s
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, (interface_id,))

            result = cursor.fetchone()
            if result and result['value'] is not None:
                current_value = float(result['value'])
                
                # Check if condition has improved below all thresholds
                # Alert should be resolved if:
                # 1. If there's a critical threshold, value must be below it
                # 2. If there's a warning threshold, value must be below it
                # 3. At least one threshold must exist
                should_resolve = False
                
                if critical_threshold is not None:
                    if warning_threshold is not None:
                        # Both thresholds exist - must be below BOTH
                        should_resolve = current_value < critical_threshold and current_value < warning_threshold
                    else:
                        # Only critical exists - must be below it
                        should_resolve = current_value < critical_threshold
                elif warning_threshold is not None:
                    # Only warning exists - must be below it
                    should_resolve = current_value < warning_threshold
                if should_resolve:
                # Auto-resolve the alert
                    resolve_alert(alert_id)
                    print(f"Auto-resolved alert {alert_id} - condition returned to normal (value: {current_value})")
                    alert_data = {
                        'alert_id': alert_id,
                        'device_name': f'{device_id}',
                        'device_ip': alert['ip_address'],
                        'severity': 'info',
                        'message': f'Condition returned to normal (value: {current_value})',
                        'alert_type': metric_type,
                        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    alerts_generated.append(alert_data)

    # Get all active thresholds (excluding ignored alerts with future ignore_until times)
    cursor.execute("""
        SELECT t.*, d.ip_address, d.hostname, i.name as interface_name
        FROM alert_thresholds t
        JOIN devices d ON t.device_id = d.device_id
        LEFT JOIN interfaces i ON t.interface_id = i.interface_id
        WHERE t.is_active = TRUE
    """)
    thresholds = cursor.fetchall()

    
    for threshold in thresholds:
        threshold_id= threshold['threshold_id']
        device_id = threshold['device_id']
        device_status = threshold['device_status']
        metric_type = threshold['metric_type']
        interface_id = threshold['interface_id']

        if device_status == 'down':
            cursor.execute("""
                SELECT status FROM device_availability
                WHERE device_id=%s
                ORDER BY timestamp DESC
                LIMIT 1
            """, (device_id,))
            result = cursor.fetchone()
            severity = None
            if result and result['status'].lower() == 'down':
                severity = 'critical'
                metric_type = 'down'
                threshold['metric_type'] = metric_type
                current_value = 0
                cursor.execute("""
                    SELECT alert_id, is_ignored, ignore_until, notified_at FROM alerts
                    WHERE device_id = %s AND alert_type = %s
                    AND resolved_at IS NULL
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (device_id, metric_type))
                existing_alert = cursor.fetchone()

                # Skip if alert is currently ignored and ignore period hasn't expired
                if existing_alert and existing_alert['is_ignored']:
                    if existing_alert['ignore_until'] is None or existing_alert['ignore_until'] > datetime.now():
                        continue

                if not existing_alert:
                    # Create new alert and notify immediately
                    message = generate_alert_message(threshold, current_value, severity)
                    cursor.execute("""
                        INSERT INTO alerts (device_id, alert_type, severity, message, threshold_id, notified_at)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                    """, (device_id, metric_type, severity, message, threshold_id))
                    alert_id = cursor.lastrowid

                    alert_data = {
                        'alert_id': alert_id,
                        'device_name': threshold['hostname'] or threshold['ip_address'],
                        'device_ip': threshold['ip_address'],
                        'severity': severity,
                        'message': message,
                        'alert_type': metric_type,
                        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }

                    alerts_generated.append(alert_data)
                elif not existing_alert['notified_at']:
                    # Alert exists but wasn't notified yet, notify now
                    message = generate_alert_message(threshold, current_value, severity)
                    alert_data = {
                        'alert_id': existing_alert['alert_id'],
                        'device_name': threshold['hostname'] or threshold['ip_address'],
                        'device_ip': threshold['ip_address'],
                        'severity': severity,
                        'message': message,
                        'alert_type': metric_type,
                        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    alerts_generated.append(alert_data)
                    # Mark as notified
                    cursor.execute("""
                        UPDATE alerts SET notified_at = NOW() WHERE alert_id = %s
                    """, (existing_alert['alert_id'],))
                else:
                    # Alert exists and was already notified, just update the value
                    cursor.execute("""
                        UPDATE alerts SET severity = %s WHERE alert_id = %s
                    """, (severity, existing_alert['alert_id']))

        else:
            # Get latest metric value based on type
            if metric_type == 'cpu':
                cursor.execute("""
                    SELECT cpu_usage_pct as value
                    FROM device_health
                    WHERE device_id = %s
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, (device_id,))
            elif metric_type == 'memory':
                cursor.execute("""
                    SELECT memory_usage_pct as value
                    FROM device_health
                    WHERE device_id = %s
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, (device_id,))
            elif metric_type == 'disk':
                cursor.execute("""
                    SELECT disk_usage_pct as value
                    FROM device_health
                    WHERE device_id = %s
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, (device_id,))
            elif metric_type == 'interface_traffic':
                cursor.execute("""
                    SELECT (in_bps + out_bps) / 1000000 as value  -- Convert to Mbps
                    FROM interface_stats
                    WHERE interface_id = %s
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, (interface_id,))

            result = cursor.fetchone()
            if not result or result['value'] is None:
                continue

            current_value = float(result['value'])
            warning_threshold = threshold['warning_threshold']
            critical_threshold = threshold['critical_threshold']

            # Determine severity
            severity = None
            threshold_value = None

            if critical_threshold is not None and current_value >= critical_threshold:
                severity = 'critical'
                threshold_value = critical_threshold
            elif warning_threshold is not None and current_value >= warning_threshold:
                severity = 'warning'
                threshold_value = warning_threshold

        if severity:
            # Check if alert already exists and is not resolved
            if interface_id:
                cursor.execute("""
                    SELECT alert_id, is_ignored, ignore_until, notified_at FROM alerts
                    WHERE device_id = %s AND interface_id = %s AND alert_type = %s
                    AND resolved_at IS NULL
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (device_id, interface_id, metric_type))
            else:
                cursor.execute("""
                    SELECT alert_id, is_ignored, ignore_until, notified_at FROM alerts
                    WHERE device_id = %s AND interface_id IS NULL AND alert_type = %s
                    AND resolved_at IS NULL
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (device_id, metric_type))

            existing_alert = cursor.fetchone()

            # Skip if alert is currently ignored and ignore period hasn't expired
            if existing_alert and existing_alert['is_ignored']:
                if existing_alert['ignore_until'] is None or existing_alert['ignore_until'] > datetime.now():
                    continue

            if not existing_alert:
                # Create new alert and notify immediately
                message = generate_alert_message(threshold, current_value, severity)
                cursor.execute("""
                    INSERT INTO alerts (device_id, interface_id, alert_type, severity, message, value, threshold, threshold_id, notified_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """, (device_id, interface_id, metric_type, severity, message, current_value, threshold_value, threshold_id))
                alert_id = cursor.lastrowid

                alert_data = {
                    'alert_id': alert_id,
                    'device_name': threshold['hostname'] or threshold['ip_address'],
                    'device_ip': threshold['ip_address'],
                    'severity': severity,
                    'message': message,
                    'alert_type': metric_type,
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }

                alerts_generated.append(alert_data)
            elif not existing_alert['notified_at']:
                # Alert exists but wasn't notified yet, notify now
                message = generate_alert_message(threshold, current_value, severity)
                alert_data = {
                    'alert_id': existing_alert['alert_id'],
                    'device_name': threshold['hostname'] or threshold['ip_address'],
                    'device_ip': threshold['ip_address'],
                    'severity': severity,
                    'message': message,
                    'alert_type': metric_type,
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                alerts_generated.append(alert_data)
                # Mark as notified
                cursor.execute("""
                    UPDATE alerts SET notified_at = NOW() WHERE alert_id = %s
                """, (existing_alert['alert_id'],))
            else:
                # Alert exists and was already notified, just update the value
                cursor.execute("""
                    UPDATE alerts SET value = %s, severity = %s WHERE alert_id = %s
                """, (current_value, severity, existing_alert['alert_id']))

    db.commit()
    cursor.close()
    db.close()
    
    # Send notifications after committing and closing the database connection
    for alert_data in alerts_generated:
        try:
            send_alert_notifications(alert_data['alert_id'], alert_data)
        except Exception as e:
            print(f"Error sending notifications for alert {alert_data['alert_id']}: {e}")
    
    print(f"Generated {len(alerts_generated)} new alerts.")
    return alerts_generated

def generate_alert_message(threshold, current_value, severity):
    """Generate a human-readable alert message."""
    device_name = threshold['hostname'] or threshold['ip_address']
    metric_name = threshold['metric_type']

    if threshold['interface_name']:
        location = f"interface {threshold['interface_name']} on {device_name}"
    else:
        location = f"device {device_name}"

    if threshold['metric_type'] == 'down':
        if current_value == 0:
            current_value = 'Down'
        return f"{severity.upper()}: {threshold['ip_address']} or {location} is {current_value}"
    else:
        unit=''
        if threshold['metric_type'] == 'cpu':
            unit = '%'
        elif threshold['metric_type'] == 'memory':
            unit = '%'
        elif threshold['metric_type'] == 'disk':
            unit = '%'
        elif threshold['metric_type'] == 'interface_traffic':
            unit = ' Mbps'
            metric_name = 'Traffic'
        return f"{severity.upper()}: {metric_name} usage on {location} is {current_value:.1f}{unit}"

def acknowledge_alert(alert_id, user_id):
    """Acknowledge an alert."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        UPDATE alerts
        SET is_acknowledged = TRUE, acknowledged_by = %s, acknowledged_at = NOW()
        WHERE alert_id = %s
    """, (user_id, alert_id))
    db.commit()
    cursor.close()
    db.close()

def resolve_alert(alert_id):
    """Mark an alert as resolved."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        UPDATE alerts
        SET resolved_at = NOW()
        WHERE alert_id = %s
    """, (alert_id,))
    db.commit()
    cursor.close()
    db.close()

def ignore_alert(alert_id, user_id, ignore_duration_minutes=None):
    """Ignore an alert for a specified duration or permanently."""
    db = get_db()
    cursor = db.cursor()

    if ignore_duration_minutes:
        from datetime import timedelta
        ignore_until = datetime.now() + timedelta(minutes=ignore_duration_minutes)
        cursor.execute("""
            UPDATE alerts
            SET is_ignored = TRUE, ignored_by = %s, ignored_at = NOW(), ignore_until = %s
            WHERE alert_id = %s
        """, (user_id, ignore_until, alert_id))
    else:
        cursor.execute("""
            UPDATE alerts
            SET is_ignored = TRUE, ignored_by = %s, ignored_at = NOW()
            WHERE alert_id = %s
        """, (user_id, alert_id))

    db.commit()
    cursor.close()
    db.close()

def get_active_alerts():
    """Get all active (unresolved and not ignored) alerts."""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT a.*, d.hostname, d.ip_address, i.name as interface_name
        FROM alerts a
        JOIN devices d ON a.device_id = d.device_id
        LEFT JOIN interfaces i ON a.interface_id = i.interface_id
        WHERE a.resolved_at IS NULL
        AND (a.is_ignored = FALSE OR (a.is_ignored = TRUE AND a.ignore_until IS NOT NULL AND a.ignore_until < NOW()))
        ORDER BY a.created_at DESC
    """)
    alerts = cursor.fetchall()
    cursor.close()
    db.close()
    return alerts