import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import os
from datetime import datetime, timedelta
from modules.db import get_db

def generate_availability_report(start_date=None, end_date=None):
    """Generate availability report for all devices."""
    if not start_date:
        start_date = datetime.now() - timedelta(days=30)
    if not end_date:
        end_date = datetime.now()

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # Get device availability data
    cursor.execute("""
        SELECT d.hostname, d.ip_address,
               COUNT(CASE WHEN da.status = 'up' THEN 1 END) as up_count,
               COUNT(*) as total_count,
               AVG(da.latency) as avg_latency
        FROM devices d
        LEFT JOIN device_availability da ON d.device_id = da.device_id
        WHERE da.timestamp BETWEEN %s AND %s
        GROUP BY d.device_id, d.hostname, d.ip_address
        ORDER BY d.hostname
    """, (start_date, end_date))

    data = cursor.fetchall()
    cursor.close()
    db.close()

    # Calculate availability percentage
    for row in data:
        if row['total_count'] > 0:
            row['availability_pct'] = (row['up_count'] / row['total_count']) * 100
        else:
            row['availability_pct'] = 0

    return data

def generate_performance_report(device_id=None, start_date=None, end_date=None):
    """Generate performance report for devices."""
    if not start_date:
        start_date = datetime.now() - timedelta(days=7)
    if not end_date:
        end_date = datetime.now()

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # Get device health data
    query = """
        SELECT d.hostname, d.ip_address,
               AVG(dh.cpu_usage_pct) as avg_cpu,
               MAX(dh.cpu_usage_pct) as max_cpu,
               AVG(dh.memory_usage_pct) as avg_memory,
               MAX(dh.memory_usage_pct) as max_memory,
               AVG(dh.disk_usage_pct) as avg_disk,
               MAX(dh.disk_usage_pct) as max_disk,
               COUNT(*) as samples
        FROM devices d
        LEFT JOIN device_health dh ON d.device_id = dh.device_id
        WHERE dh.timestamp BETWEEN %s AND %s
    """
    params = [start_date, end_date]

    if device_id:
        query += " AND d.device_id = %s"
        params.append(device_id)

    query += " GROUP BY d.device_id, d.hostname, d.ip_address ORDER BY d.hostname"

    cursor.execute(query, params)
    data = cursor.fetchall()
    cursor.close()
    db.close()

    return data

def create_pdf_report(report_type, data, filename):
    """Create a PDF report from data."""
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title = f"{report_type.title()} Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    story.append(Paragraph(title, styles['Title']))
    story.append(Spacer(1, 12))

    if report_type == 'availability':
        # Create table for availability report
        table_data = [['Device', 'IP Address', 'Availability %', 'Avg Latency (ms)', 'Total Checks']]

        for row in data:
            table_data.append([
                row['hostname'] or 'Unknown',
                row['ip_address'],
                f"{row['availability_pct']:.1f}%",
                f"{row.get('avg_latency', 0):.1f}" if row.get('avg_latency') else 'N/A',
                row['total_count']
            ])

    elif report_type == 'performance':
        # Create table for performance report
        table_data = [['Device', 'IP Address', 'Avg CPU %', 'Max CPU %', 'Avg Memory %', 'Max Memory %', 'Avg Disk %', 'Max Disk %']]

        for row in data:
            table_data.append([
                row['hostname'] or 'Unknown',
                row['ip_address'],
                f"{row['avg_cpu']:.1f}%" if row['avg_cpu'] else 'N/A',
                f"{row['max_cpu']:.1f}%" if row['max_cpu'] else 'N/A',
                f"{row['avg_memory']:.1f}%" if row['avg_memory'] else 'N/A',
                f"{row['max_memory']:.1f}%" if row['max_memory'] else 'N/A',
                f"{row['avg_disk']:.1f}%" if row['avg_disk'] else 'N/A',
                f"{row['max_disk']:.1f}%" if row['max_disk'] else 'N/A'
            ])

    # Create table
    table = Table(table_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    story.append(table)
    doc.build(story)

def save_report_to_db(report_name, report_type, parameters, generated_by, file_path):
    """Save report metadata to database."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO reports (report_name, report_type, parameters, generated_by, file_path, status, completed_at)
        VALUES (%s, %s, %s, %s, %s, 'completed', NOW())
    """, (report_name, report_type, str(parameters), generated_by, file_path))
    db.commit()
    cursor.close()
    db.close()