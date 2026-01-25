import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from modules.db import get_db
import os

def send_email_notification(to_email, subject, body):
    """Send an email notification."""
    try:
        # Email configuration - these should be in environment variables or config
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_username = os.getenv('SMTP_USERNAME', '')
        smtp_password = os.getenv('SMTP_PASSWORD', '')

        if not smtp_username or not smtp_password:
            print("SMTP credentials not configured")
            return False

        # Create message
        msg = MIMEMultipart()
        msg['From'] = smtp_username
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'html'))

        # Send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)
        text = msg.as_string()
        server.sendmail(smtp_username, to_email, text)
        server.quit()

        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def send_alert_notifications(alert_id, alert_data):
    """Send notifications for a new alert to all users who have notifications enabled."""
    db = get_db()
    cursor = db.cursor(dictionary=True)

    try:
        # Get users who want notifications for this severity
        cursor.execute("""
            SELECT u.email, u.username, ns.*
            FROM users u
            JOIN notification_settings ns ON u.user_id = ns.user_id
            WHERE ns.alert_severity = %s AND ns.email_enabled = TRUE
        """, (alert_data['severity'],))

        users = cursor.fetchall()

        subject = f"NMS Alert: {alert_data['severity'].upper()} - {alert_data['device_name']}"
        body = f"""
        <html>
        <body>
            <h2>New {alert_data['severity'].upper()} Alert</h2>
            <p><strong>Device:</strong> {alert_data['device_name']}</p>
            <p><strong>Alert Type:</strong> {alert_data['alert_type'].upper()}</p>
            <p><strong>Message:</strong> {alert_data['message']}</p>
            <p><strong>Time:</strong> {alert_data.get('created_at', 'Unknown')}</p>
            <br>
            <p><a href="{os.getenv('APP_URL', 'http://localhost:5000')}/alerts">View All Alerts</a></p>
        </body>
        </html>
        """

        sent_count = 0
        for user in users:
            if send_email_notification(user['email'], subject, body):
                # Log successful notification
                cursor.execute("""
                    INSERT INTO notifications (alert_id, user_id, notification_type, status)
                    VALUES (%s, %s, 'email', 'sent')
                """, (alert_id, user['user_id']))
                sent_count += 1
            else:
                # Log failed notification
                cursor.execute("""
                    INSERT INTO notifications (alert_id, user_id, notification_type, status, error_message)
                    VALUES (%s, %s, 'email', 'failed', 'SMTP error')
                """, (alert_id, user['user_id']))

        db.commit()
        print(f"Sent {sent_count} email notifications for alert {alert_id}")

    except Exception as e:
        print(f"Error sending alert notifications: {e}")
        db.rollback()
    finally:
        cursor.close()
        db.close()

def create_default_notification_settings():
    """Create default notification settings for all users."""
    db = get_db()
    cursor = db.cursor(dictionary=True)

    try:
        # Get all users
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()

        for user in users:
            # Check if settings already exist
            cursor.execute("SELECT setting_id FROM notification_settings WHERE user_id = %s", (user['user_id'],))
            existing = cursor.fetchone()

            if not existing:
                # Create default settings for warning and critical alerts
                cursor.execute("""
                    INSERT INTO notification_settings (user_id, alert_severity, email_enabled)
                    VALUES (%s, 'warning', TRUE), (%s, 'critical', TRUE)
                """, (user['user_id'], user['user_id']))

        db.commit()
        print("Created default notification settings for all users")

    except Exception as e:
        print(f"Error creating default notification settings: {e}")
        db.rollback()
    finally:
        cursor.close()
        db.close()