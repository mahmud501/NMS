import time
from modules.db import get_db
from modules.snmp_poller import snmp_get
from datetime import datetime
from modules.utils import decrypt_password

def check_alerts():
    """
    Check all active alert thresholds and generate alerts if conditions are met.
    """
    db = get_db()
    cursor = db.cursor(dictionary=True)

    # Get all active thresholds
    cursor.execute("""
        SELECT t.*, d.ip_address, d.hostname, i.name as interface_name
        FROM alert_thresholds t
        JOIN devices d ON t.device_id = d.device_id
        LEFT JOIN interfaces i ON t.interface_id = i.interface_id
        WHERE t.is_active = TRUE
    """)
    thresholds = cursor.fetchall()

    alerts_generated = 0

    for threshold in thresholds:
        device_id = threshold['device_id']
        metric_type = threshold['metric_type']
        interface_id = threshold['interface_id']

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
        elif metric_type == 'availability':
            cursor.execute("""
                SELECT CASE WHEN status = 'up' THEN 100 ELSE 0 END as value
                FROM device_availability
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
            cursor.execute("""
                SELECT alert_id FROM alerts
                WHERE device_id = %s AND interface_id = %s AND alert_type = %s
                AND resolved_at IS NULL
                ORDER BY created_at DESC
                LIMIT 1
            """, (device_id, interface_id, metric_type))

            existing_alert = cursor.fetchone()

            if not existing_alert:
                # Create new alert
                message = generate_alert_message(threshold, current_value, severity)
                cursor.execute("""
                    INSERT INTO alerts (device_id, interface_id, alert_type, severity, message, value, threshold)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (device_id, interface_id, metric_type, severity, message, current_value, threshold_value))
                alerts_generated += 1

    db.commit()
    db.close()
    print(f"Generated {alerts_generated} new alerts.")

def generate_alert_message(threshold, current_value, severity):
    """Generate a human-readable alert message."""
    device_name = threshold['hostname'] or threshold['ip_address']
    metric_name = threshold['metric_type'].upper()

    if threshold['interface_name']:
        location = f"interface {threshold['interface_name']} on {device_name}"
    else:
        location = f"device {device_name}"

    if threshold['metric_type'] == 'cpu':
        unit = '%'
    elif threshold['metric_type'] == 'memory':
        unit = '%'
    elif threshold['metric_type'] == 'disk':
        unit = '%'
    elif threshold['metric_type'] == 'availability':
        unit = '%'
        current_value = 100 if current_value > 0 else 0
    elif threshold['metric_type'] == 'interface_traffic':
        unit = ' Mbps'
        metric_name = 'Traffic'

    return f"{severity.upper()}: {metric_name} usage on {location} is {current_value:.1f}{unit}"

def get_active_alerts():
    """Get all active (unresolved) alerts."""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT a.*, d.hostname, d.ip_address, i.name as interface_name
        FROM alerts a
        JOIN devices d ON a.device_id = d.device_id
        LEFT JOIN interfaces i ON a.interface_id = i.interface_id
        WHERE a.resolved_at IS NULL
        ORDER BY a.created_at DESC
    """)
    alerts = cursor.fetchall()
    cursor.close()
    db.close()
    return alerts

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