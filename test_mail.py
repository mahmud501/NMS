import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


# subject = f"NMS Alert: {alert_data['severity'].upper()} - {alert_data['device_name']}"
subject = f"NMS Alert testing"
body = f"""
    <html>
    <body>
        <h2>Testing email </h2>
        <br>
        <p><a href="{os.getenv('APP_URL', 'http://localhost:5000')}/alerts">View All Alerts</a></p>
    </body>
    </html>
    """
to_email="mahmudulhasanmukta@gmail.com"

def send_email_notification(to_email, subject, body):
    """Send an email notification."""
    try:
        # Email configuration - these should be in environment variables or config
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_username = os.getenv('SMTP_USERNAME', '')
        smtp_password = os.getenv('SMTP_PASSWORD', '')
        print(smtp_username, smtp_password)

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

send_email_notification(to_email,subject,body)