from time import strftime

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for PDF generation
from matplotlib import pyplot as plt
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
    doc = SimpleDocTemplate(filename, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    normal_style = styles['Normal']
    story = []
    page_width = landscape(A4)[0] - 20
    col_width = page_width / len(data[0])

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
                Paragraph(str(row['hostname'] or 'Unknown'), normal_style),
                row['ip_address'], 
                f"{row['avg_cpu']:.1f}%" if row['avg_cpu'] else 'N/A',
                f"{row['max_cpu']:.1f}%" if row['max_cpu'] else 'N/A',
                f"{row['avg_memory']:.1f}%" if row['avg_memory'] else 'N/A',
                f"{row['max_memory']:.1f}%" if row['max_memory'] else 'N/A',
                f"{row['avg_disk']:.1f}%" if row['avg_disk'] else 'N/A', 
                f"{row['max_disk']:.1f}%" if row['max_disk'] else 'N/A', 
            ])
    elif report_type == 'device_timeline':
        table_data = [["Device", "Status", "Start", "End", "Duration"]]

        for row in data:
            table_data.append([
                row["device"],
                row["status"],
                row["start"].strftime("%Y-%m-%d %H:%M:%S"),
                row["end"].strftime("%Y-%m-%d %H:%M:%S"),
                str(row["duration"])
            ])


    # Create table
    table = Table(table_data, colWidths=[col_width]*len(data[0]), repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
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

def generate_device_timeline(device_id=None, start_date=None, end_date=None):
    if not start_date:
        start_date = datetime.now() - timedelta(days=30)
    if not end_date:
        end_date = datetime.now()

    db = get_db()
    cursor = db.cursor(dictionary=True)

    query = """
        SELECT d.hostname, d.ip_address, da.status, da.timestamp
        FROM device_availability da
        JOIN devices d ON d.device_id = da.device_id
        WHERE da.timestamp BETWEEN %s AND %s
    """

    params = [start_date, end_date]

    if device_id:
        query += " AND d.device_id = %s"
        params.append(device_id)

    query += " ORDER BY d.hostname, da.timestamp"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    cursor.close()
    db.close()

    return rows

def build_timeline(rows, report_end_time):
    timeline = []

    if not rows:
        return timeline

    current_device = None
    current_status = None
    start_time = None

    for row in rows:
        device = row["ip_address"] or row["hostname"] or "Unknown Device"
        status = row["status"]
        timestamp = row["timestamp"]

        # First row initialization
        if current_device is None:
            current_device = device
            current_status = status
            start_time = timestamp
            continue

        # Device changed → close previous device timeline
        if device != current_device:
            if start_time:
                timeline.append({
                    "device": current_device,
                    "status": current_status,
                    "start": start_time,
                    "end": timestamp,
                    "duration": timestamp - start_time
                })

            # reset for new device
            current_device = device
            current_status = status
            start_time = timestamp
            continue

        # Same device → check status change
        if status != current_status:
            if start_time:
                timeline.append({
                    "device": current_device,
                    "status": current_status,
                    "start": start_time,
                    "end": timestamp,
                    "duration": timestamp - start_time
                })

            current_status = status
            start_time = timestamp

    # Final segment
    if current_device and start_time and report_end_time:
        timeline.append({
            "device": current_device,
            "status": current_status,
            "start": start_time,
            "end": report_end_time,
            "duration": report_end_time - start_time
        })

    return timeline

def generate_device_pdf(timeline, data, filename):
    doc = SimpleDocTemplate(filename)
    story = []

    plt_timestamps = []
    plt_status = []
    for row in data:
        plt_timestamps.append(row['timestamp'])
        plt_status.append(1 if row["status"].lower() == "up" else 0)
    plt.figure(figsize=(10, 4))
    plt.plot(plt_timestamps, plt_status, label="Status (1=Up, 0=Down)")
    plt.grid(True)
    plt.xlabel("Time")
    plt.ylabel("Status")
    plt.ylim(ymin=-0.1, ymax=1.1)
    plt.title("Device Availability Timeline")
    plt.legend()
    plt.xticks(rotation=45)
    chart_path = "temp_timeline_chart.png"
    plt.tight_layout()
    plt.savefig(chart_path)
    plt.close()
    
    styles = getSampleStyleSheet()
    story.append(Paragraph("Device Availability Report", styles["Title"]))

    if os.path.exists(chart_path):
        story.append(Image(chart_path, width=500, height=200))
        story.append(Spacer(1, 20))

    table_data = [["Device", "Status", "Start", "End", "Duration"]]

    for row in timeline:
        table_data.append([
            row["device"],
            row["status"],
            row["start"].strftime("%Y-%m-%d %H:%M:%S"),
            row["end"].strftime("%Y-%m-%d %H:%M:%S"),
            str(row["duration"])
        ])

    table = Table(table_data, repeatRows=1)

    table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 1, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.grey),
        ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
    ]))

    story.append(table)
    doc.build(story)

def generate_device_performance(device_id=None, start_date=None, end_date=None):
    if not start_date:
        start_date = datetime.now() - timedelta(days=7)
    if not end_date:
        end_date = datetime.now()

    db = get_db()
    cursor = db.cursor(dictionary=True)

    query = """
        SELECT d.hostname, d.ip_address, dh.timestamp,
               dh.cpu_usage_pct as cpu_usage,
               dh.memory_usage_pct as memory_usage,
               dh.disk_usage_pct as disk_usage
        FROM device_health dh
        JOIN devices d ON d.device_id = dh.device_id
        WHERE dh.timestamp BETWEEN %s AND %s
    """
    params = [start_date, end_date]

    if device_id:
        query += " AND d.device_id = %s"
        params.append(device_id)

    query += " ORDER BY d.hostname, dh.timestamp"

    cursor.execute(query, params)
    data = cursor.fetchall()
    cursor.close()
    db.close()

    return data

def generate_device_performance_pdf(data, filename, start_date=None, end_date=None):
    doc = SimpleDocTemplate(filename)
    story = []

    # Prepare data for graph
    plt_timestamps = []
    plt_cpu = []
    plt_memory = []
    plt_disk = []

    for row in data:
        plt_timestamps.append(row['timestamp'])
        plt_cpu.append(row['cpu_usage'] or 0)
        plt_memory.append(row['memory_usage'] or 0)
        plt_disk.append(row['disk_usage'] or 0)

    # Create plot
    plt.figure(figsize=(10, 4))
    plt.plot(plt_timestamps, plt_cpu, label="CPU %")
    plt.plot(plt_timestamps, plt_memory, label="Memory %")
    plt.plot(plt_timestamps, plt_disk, label="Disk %")
    plt.grid(True)

    plt.xlabel("Time")
    plt.ylabel("Usage (%)")
    plt.title("Device Performance Over Time")
    plt.legend()
    plt.xticks(rotation=45)

    # Save image
    chart_path = "temp_chart.png"
    plt.tight_layout()
    plt.savefig(chart_path)
    plt.close()



    styles = getSampleStyleSheet()
    title_text = "Device Performance Report"
    if start_date and end_date:
        title_text += f" ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})"
    story.append(Paragraph(title_text, styles["Title"]))

    if os.path.exists(chart_path):
        story.append(Spacer(1, 10))
        story.append(Image(chart_path, width=500, height=200))
        story.append(Spacer(1, 20))

    table_data = [["Device", "IP Address", "Time", "CPU %", "Memory %", "Disk %"]]

    for row in data:
        table_data.append([
            row['hostname'] or 'Unknown',
            row['ip_address'],
            row['timestamp'].strftime("%Y-%m-%d %H:%M:%S"),
            f"{row['cpu_usage']:.1f}%" if row['cpu_usage'] is not None else 'N/A',
            f"{row['memory_usage']:.1f}%" if row['memory_usage'] is not None else 'N/A',
            f"{row['disk_usage']:.1f}%" if row['disk_usage'] is not None else 'N/A'
        ])

    table = Table(table_data, repeatRows=1)

    table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 1, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.grey),
        ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
    ]))

    story.append(table)
    doc.build(story)
    if os.path.exists(chart_path):
        os.remove(chart_path)