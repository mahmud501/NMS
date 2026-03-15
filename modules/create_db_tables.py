from modules.db import get_db
from modules.utils import hash_user_password
import json


def create_database_tables():

    db=get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS roles (
            role_id INT NOT NULL AUTO_INCREMENT,
            role_name VARCHAR(50) NOT NULL,
            permissions JSON DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (role_id),
            UNIQUE KEY role_name (role_name)

            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INT NOT NULL AUTO_INCREMENT,
            username VARCHAR(50) NOT NULL,
            email VARCHAR(100) NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role_id INT DEFAULT NULL,
            is_active TINYINT(1) DEFAULT 1,
            last_login TIMESTAMP NULL DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (user_id),

            UNIQUE KEY username (username),
            UNIQUE KEY email (email),

            KEY role_id (role_id),

            CONSTRAINT users_ibfk_1
                FOREIGN KEY (role_id)
                REFERENCES roles(role_id)

            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            device_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            hostname VARCHAR(255) NOT NULL,
            ip_address VARCHAR(45) NOT NULL,
            device_type VARCHAR(50) DEFAULT NULL,
            vendor VARCHAR(50) DEFAULT NULL,
            model VARCHAR(100) DEFAULT NULL,
            serial_number VARCHAR(100) DEFAULT NULL,
            os_version VARCHAR(100) DEFAULT NULL,
            location VARCHAR(255) DEFAULT NULL,
            status ENUM('UP','DOWN') DEFAULT 'DOWN',
            last_polled_time DATETIME DEFAULT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            polling_status ENUM('active','inactive') DEFAULT 'active',
            uptime BIGINT DEFAULT NULL,
            description VARCHAR(255) DEFAULT NULL,
            sys_description VARCHAR(255) DEFAULT NULL,
            last_reboot_time DATETIME DEFAULT NULL,

            PRIMARY KEY (device_id),
            UNIQUE KEY unique_device_ip (ip_address),
            KEY hostname_index (hostname)

            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interfaces (
            interface_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            device_id BIGINT UNSIGNED NOT NULL,
            if_index INT DEFAULT NULL,
            name VARCHAR(255) DEFAULT NULL,
            description VARCHAR(255) DEFAULT NULL,
            mac_address VARCHAR(17) DEFAULT NULL,
            ipv4_address VARCHAR(45) DEFAULT NULL,
            subnet_mask VARCHAR(15) DEFAULT NULL,
            speed BIGINT DEFAULT NULL,
            mtu BIGINT DEFAULT 0,
            admin_status ENUM('up','down') DEFAULT 'up',
            oper_status ENUM('up','down') DEFAULT 'down',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

            PRIMARY KEY (interface_id),

            KEY index_iface_dev (device_id),

            CONSTRAINT interfaces_ibfk_1
                FOREIGN KEY (device_id)
                REFERENCES devices(device_id)
                ON DELETE CASCADE

            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interface_stats (
            stat_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            interface_id BIGINT UNSIGNED NOT NULL,
            in_octets BIGINT UNSIGNED DEFAULT 0,
            out_octets BIGINT UNSIGNED DEFAULT 0,
            in_bps BIGINT DEFAULT 0,
            out_bps BIGINT DEFAULT 0,
            in_errors BIGINT UNSIGNED DEFAULT 0,
            out_errors BIGINT UNSIGNED DEFAULT 0,
            timestamp DATETIME NOT NULL,

            PRIMARY KEY (stat_id),

            KEY index_iface_time (interface_id, timestamp),

            CONSTRAINT interface_stats_ibfk_1
                FOREIGN KEY (interface_id)
                REFERENCES interfaces(interface_id)
                ON DELETE CASCADE

            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS device_availability (
            id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            device_id BIGINT UNSIGNED NOT NULL,
            status ENUM('UP','DOWN') NOT NULL,
            latency FLOAT DEFAULT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (id),

            KEY index_avail_dev_time (device_id, timestamp),

            CONSTRAINT device_availability_ibfk_1
                FOREIGN KEY (device_id)
                REFERENCES devices(device_id)
                ON DELETE CASCADE

            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS device_health (
            health_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            device_id BIGINT UNSIGNED NOT NULL,
            cpu_usage_pct DECIMAL(5,2) DEFAULT NULL,
            memory_usage_pct DECIMAL(5,2) DEFAULT NULL,
            disk_usage_pct DECIMAL(5,2) DEFAULT NULL,
            temp_celsius DECIMAL(6,2) DEFAULT NULL,
            uptime_seconds BIGINT UNSIGNED DEFAULT NULL,
            timestamp DATETIME NOT NULL,

            PRIMARY KEY (health_id),

            KEY index_health_dev_time (device_id, timestamp),

            CONSTRAINT device_health_ibfk_1
                FOREIGN KEY (device_id)
                REFERENCES devices(device_id)
                ON DELETE CASCADE

            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS device_inventory (
            inventory_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            device_id BIGINT UNSIGNED NOT NULL,
            component_name VARCHAR(255) DEFAULT NULL,
            description VARCHAR(255) DEFAULT NULL,
            serial_number VARCHAR(100) DEFAULT NULL,
            status VARCHAR(50) DEFAULT NULL,
            discovered_at DATETIME DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (inventory_id),

            KEY index_device_inv (device_id),

            CONSTRAINT device_inventory_ibfk_1
                FOREIGN KEY (device_id)
                REFERENCES devices(device_id)
                ON DELETE CASCADE

            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
    
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alert_thresholds (
        threshold_id INT NOT NULL AUTO_INCREMENT,
        device_id BIGINT UNSIGNED DEFAULT NULL,
        device_status VARCHAR(15) DEFAULT NULL,
        metric_type ENUM('cpu','memory','disk','interface_traffic') DEFAULT NULL,
        interface_id BIGINT UNSIGNED DEFAULT NULL,
        warning_threshold DECIMAL(5,2) DEFAULT NULL,
        critical_threshold DECIMAL(5,2) DEFAULT NULL,
        is_active TINYINT(1) DEFAULT 1,
        created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (threshold_id),
        KEY device_id (device_id),
        KEY interface_id (interface_id),
        CONSTRAINT alert_thresholds_ibfk_1 
            FOREIGN KEY (device_id) REFERENCES devices(device_id),
        CONSTRAINT alert_thresholds_ibfk_2 
            FOREIGN KEY (interface_id) REFERENCES interfaces(interface_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            alert_id INT NOT NULL AUTO_INCREMENT,
            device_id BIGINT UNSIGNED DEFAULT NULL,
            interface_id BIGINT UNSIGNED DEFAULT NULL,
            alert_type ENUM('cpu','memory','disk','interface_traffic','down','syslog') NOT NULL,
            severity ENUM('warning','critical','info') NOT NULL,
            message TEXT NOT NULL,
            value DECIMAL(10,2) DEFAULT NULL,
            threshold DECIMAL(5,2) DEFAULT NULL,
            is_acknowledged TINYINT(1) DEFAULT 0,
            acknowledged_by INT DEFAULT NULL,
            acknowledged_at TIMESTAMP NULL DEFAULT NULL,
            resolved_at TIMESTAMP NULL DEFAULT NULL,
            created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
            notified_at DATETIME DEFAULT NULL,
            is_ignored TINYINT(1) DEFAULT 0,
            ignored_by INT DEFAULT NULL,
            ignored_at TIMESTAMP NULL DEFAULT NULL,
            ignore_until TIMESTAMP NULL DEFAULT NULL,
            threshold_id INT DEFAULT NULL,
            PRIMARY KEY (alert_id),
            KEY device_id (device_id),
            KEY interface_id (interface_id),
            KEY acknowledged_by (acknowledged_by),
            KEY ignored_by (ignored_by),
            KEY fk_alerts_threshold (threshold_id),

            CONSTRAINT alerts_ibfk_1 
                FOREIGN KEY (device_id) REFERENCES devices(device_id),

            CONSTRAINT alerts_ibfk_2 
                FOREIGN KEY (interface_id) REFERENCES interfaces(interface_id),

            CONSTRAINT alerts_ibfk_3 
                FOREIGN KEY (acknowledged_by) REFERENCES users(user_id),

            CONSTRAINT alerts_ibfk_4 
                FOREIGN KEY (ignored_by) REFERENCES users(user_id),

            CONSTRAINT fk_alerts_threshold 
                FOREIGN KEY (threshold_id) REFERENCES alert_thresholds(threshold_id) 
                ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS arp_table (
            arp_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            device_id BIGINT UNSIGNED NOT NULL,
            ip_address VARCHAR(45) NOT NULL,
            mac_address VARCHAR(17) NOT NULL,
            interface_name VARCHAR(255) DEFAULT NULL,
            timestamp DATETIME NOT NULL,
            PRIMARY KEY (arp_id),
            KEY idx_arp_ip (ip_address),
            KEY idx_arp_dev_time (device_id, timestamp),

            CONSTRAINT arp_table_ibfk_1 
                FOREIGN KEY (device_id) REFERENCES devices(device_id) 
                ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cdp_neighbors (
            cdp_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            device_id BIGINT UNSIGNED NOT NULL,
            local_interface VARCHAR(255) DEFAULT NULL,
            neighbor_device VARCHAR(255) DEFAULT NULL,
            neighbor_ip VARCHAR(45) DEFAULT NULL,
            neighbor_port VARCHAR(100) DEFAULT NULL,
            platform VARCHAR(255) DEFAULT NULL,
            timestamp DATETIME NOT NULL,

            PRIMARY KEY (cdp_id),

            KEY idx_cdp_dev_time (device_id, timestamp),

            CONSTRAINT cdp_neighbors_ibfk_1
                FOREIGN KEY (device_id)
                REFERENCES devices(device_id)
                ON DELETE CASCADE

            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notification_settings (
            setting_id INT NOT NULL AUTO_INCREMENT,
            user_id INT DEFAULT NULL,
            alert_severity ENUM('warning','critical','info') DEFAULT NULL,
            email_enabled TINYINT(1) DEFAULT 1,
            sms_enabled TINYINT(1) DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (setting_id),
            KEY notification_settings_ibfk_1 (user_id),

            CONSTRAINT notification_settings_ibfk_1
                FOREIGN KEY (user_id)
                REFERENCES users(user_id)
                ON DELETE CASCADE

            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            notification_id INT NOT NULL AUTO_INCREMENT,
            alert_id INT DEFAULT NULL,
            user_id INT DEFAULT NULL,
            notification_type ENUM('email','sms','webhook') NOT NULL,
            status ENUM('pending','sent','failed') DEFAULT 'pending',
            sent_at TIMESTAMP NULL DEFAULT NULL,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (notification_id),

            KEY user_id (user_id),
            KEY notifications_ibfk_1 (alert_id),

            CONSTRAINT notifications_ibfk_1
                FOREIGN KEY (alert_id)
                REFERENCES alerts(alert_id)
                ON DELETE CASCADE,

            CONSTRAINT notifications_ibfk_2
                FOREIGN KEY (user_id)
                REFERENCES users(user_id)

            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS poller_config (
            config_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
            poll_interval_seconds INT DEFAULT 60,
            retry_count INT DEFAULT 3,
            timeout_seconds INT DEFAULT 5,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

            PRIMARY KEY (config_id)

            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            report_id INT NOT NULL AUTO_INCREMENT,
            report_name VARCHAR(100) NOT NULL,
            report_type VARCHAR(50) DEFAULT NULL,
            parameters JSON DEFAULT NULL,
            generated_by INT DEFAULT NULL,
            file_path VARCHAR(500) DEFAULT NULL,
            status ENUM('pending','completed','failed') DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP NULL DEFAULT NULL,

            PRIMARY KEY (report_id),

            KEY generated_by (generated_by),

            CONSTRAINT reports_ibfk_1
                FOREIGN KEY (generated_by)
                REFERENCES users(user_id)

            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS snmp_profiles (
            snmp_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            device_id BIGINT UNSIGNED NOT NULL,
            snmp_version ENUM('v1','v2c','v3') NOT NULL DEFAULT 'v2c',
            community VARCHAR(100) DEFAULT NULL,
            v3_user VARCHAR(100) DEFAULT NULL,
            auth_protocol ENUM('MD5','SHA','NONE') DEFAULT 'NONE',
            auth_password_hash VARCHAR(255) DEFAULT NULL,
            priv_protocol ENUM('DES','AES','NONE') DEFAULT 'NONE',
            priv_password_hash VARCHAR(255) DEFAULT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

            PRIMARY KEY (snmp_id),

            UNIQUE KEY unique_device_snmp (device_id),

            CONSTRAINT snmp_profiles_ibfk_1
                FOREIGN KEY (device_id)
                REFERENCES devices(device_id)
                ON DELETE CASCADE

            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS syslog_messages (
            log_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            device_id BIGINT UNSIGNED DEFAULT NULL,
            device_ip VARCHAR(50) DEFAULT NULL,
            severity TINYINT UNSIGNED DEFAULT NULL,
            severity_text VARCHAR(50) DEFAULT NULL,
            facility VARCHAR(50) DEFAULT NULL,
            message TEXT,
            raw_message TEXT,
            timestamp DATETIME NOT NULL,

            PRIMARY KEY (log_id),

            KEY device_id (device_id),
            KEY idx_syslog_time (timestamp),
            KEY idx_syslog_device_ip (device_ip),

            CONSTRAINT syslog_messages_ibfk_1
                FOREIGN KEY (device_id)
                REFERENCES devices(device_id)
                ON DELETE SET NULL

            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

    cursor.execute("SHOW TABLES")
    tables=cursor.fetchall()
    print("\n✔ Current tables in database:")
    for table in tables:
        print(" -", list(table.values())[0])

        
    default_roles = [
    {
        "role_name": "admin",
        "permissions": {
            "read": True,
            "write": True,
            "delete": True,
            "view": True
        }
    },
    {
        "role_name": "operator",
        "permissions": {
            "read": True,
            "write": True,
            "delete": False,
            "view": True
        }
    },
    {
        "role_name": "viewer",
        "permissions": {
            "read": True,
            "write": False,
            "delete": False,
            "view": True
        }
    }
    ]

    # Insert roles if not exists
    for role in default_roles:
        cursor.execute("SELECT role_id FROM roles WHERE role_name=%s", (role['role_name'],))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO roles (role_name, permissions) VALUES (%s, %s)",
                (role['role_name'], json.dumps(role['permissions']))
            )
            # print(f"✓ default role '{role['role_name']}' created with permissions")
        else:
            print(f"✓ default role '{role['role_name']}' exists")

    cursor.execute("SELECT role_id FROM roles WHERE role_name='admin'")
    role_id = cursor.fetchone()['role_id']

    cursor.execute("SELECT user_id FROM users WHERE username='admin'")
    if not cursor.fetchone():
        hashed_password = hash_user_password("admin123")
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, role_id) VALUES (%s, %s, %s, %s)",
            ("admin", "admin@example.com", hashed_password, role_id)
        )
        print("✓ default admin user created with username 'admin' and password 'admin123'")
    else:
        print("✓ default admin user exists")

    

    db.commit()
    cursor.close()
    db.close()