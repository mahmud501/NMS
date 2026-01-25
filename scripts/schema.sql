-- Devices and Interfaces
CREATE TABLE IF NOT EXISTS devices (
    device_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    ip_address VARCHAR(45) NOT NULL,
    hostname VARCHAR(255) NULL,
    vendor VARCHAR(100) NULL,
    model VARCHAR(100) NULL,
    serial_number VARCHAR(100) NULL,
    os_version VARCHAR(100) NULL,
    sys_description TEXT NULL,
    description TEXT NULL,
    location VARCHAR(255) NULL,
    status ENUM('up', 'down', 'unknown') DEFAULT 'unknown',
    uptime BIGINT UNSIGNED NULL,
    last_polled_time TIMESTAMP NULL,
    last_reboot_time TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_ip_address (ip_address),
    INDEX idx_status (status),
    INDEX idx_vendor (vendor)
);

CREATE TABLE IF NOT EXISTS interfaces (
    interface_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    device_id BIGINT UNSIGNED NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT NULL,
    mac_address VARCHAR(17) NULL,
    admin_status ENUM('up', 'down') DEFAULT 'up',
    oper_status ENUM('up', 'down', 'unknown') DEFAULT 'unknown',
    speed BIGINT UNSIGNED NULL,
    mtu INT UNSIGNED NULL,
    last_change TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE,
    INDEX idx_device_id (device_id),
    INDEX idx_oper_status (oper_status),
    INDEX idx_admin_status (admin_status)
);

-- Device Health Monitoring
CREATE TABLE IF NOT EXISTS device_health (
    health_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    device_id BIGINT UNSIGNED NOT NULL,
    cpu_usage_pct DECIMAL(5,2) NULL,
    memory_usage_pct DECIMAL(5,2) NULL,
    disk_usage_pct DECIMAL(5,2) NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE,
    INDEX idx_device_timestamp (device_id, timestamp),
    INDEX idx_timestamp (timestamp)
);

-- Interface Statistics
CREATE TABLE IF NOT EXISTS interface_stats (
    stat_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    interface_id BIGINT UNSIGNED NOT NULL,
    in_octets BIGINT UNSIGNED DEFAULT 0,
    out_octets BIGINT UNSIGNED DEFAULT 0,
    in_packets BIGINT UNSIGNED DEFAULT 0,
    out_packets BIGINT UNSIGNED DEFAULT 0,
    in_errors BIGINT UNSIGNED DEFAULT 0,
    out_errors BIGINT UNSIGNED DEFAULT 0,
    in_bps DECIMAL(15,2) DEFAULT 0,
    out_bps DECIMAL(15,2) DEFAULT 0,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (interface_id) REFERENCES interfaces(interface_id) ON DELETE CASCADE,
    INDEX idx_interface_timestamp (interface_id, timestamp),
    INDEX idx_timestamp (timestamp)
);

-- Interface IP Addresses
CREATE TABLE IF NOT EXISTS interface_ips (
    ip_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    interface_id BIGINT UNSIGNED NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    subnet_mask VARCHAR(45) NULL,
    ip_version TINYINT DEFAULT 4,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (interface_id) REFERENCES interfaces(interface_id) ON DELETE CASCADE,
    INDEX idx_interface_id (interface_id),
    INDEX idx_ip_address (ip_address)
);

-- ARP Table
CREATE TABLE IF NOT EXISTS arp_table (
    arp_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    device_id BIGINT UNSIGNED NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    mac_address VARCHAR(17) NOT NULL,
    interface_name VARCHAR(255) NULL,
    arp_type ENUM('dynamic', 'static') DEFAULT 'dynamic',
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE,
    INDEX idx_device_ip (device_id, ip_address),
    INDEX idx_last_seen (last_seen)
);

-- Network Neighbors (LLDP/CDP)
CREATE TABLE IF NOT EXISTS neighbors (
    neighbor_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    device_id BIGINT UNSIGNED NOT NULL,
    local_interface VARCHAR(255) NOT NULL,
    remote_device VARCHAR(255) NULL,
    remote_interface VARCHAR(255) NULL,
    protocol ENUM('LLDP', 'CDP', 'Unknown') DEFAULT 'Unknown',
    capabilities TEXT NULL,
    platform VARCHAR(255) NULL,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE,
    INDEX idx_device_local (device_id, local_interface),
    INDEX idx_last_seen (last_seen)
);
CREATE TABLE IF NOT EXISTS roles (
    role_id INT AUTO_INCREMENT PRIMARY KEY,
    role_name VARCHAR(50) UNIQUE NOT NULL,
    permissions JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role_id INT,
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(role_id)
);

-- Alerts and Thresholds
CREATE TABLE IF NOT EXISTS alert_thresholds (
    threshold_id INT AUTO_INCREMENT PRIMARY KEY,
    device_id bigint unsigned,
    metric_type ENUM('cpu', 'memory', 'disk', 'interface_traffic', 'availability') NOT NULL,
    interface_id bigint unsigned NULL,
    warning_threshold DECIMAL(5,2),
    critical_threshold DECIMAL(5,2),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(device_id),
    FOREIGN KEY (interface_id) REFERENCES interfaces(interface_id)
);

CREATE TABLE IF NOT EXISTS alerts (
    alert_id INT AUTO_INCREMENT PRIMARY KEY,
    device_id BIGINT UNSIGNED,
    interface_id BIGINT UNSIGNED NULL,
    alert_type ENUM('cpu', 'memory', 'disk', 'interface_traffic', 'availability', 'syslog') NOT NULL,
    severity ENUM('warning', 'critical', 'info') NOT NULL,
    message TEXT NOT NULL,
    value DECIMAL(10,2) NULL,
    threshold DECIMAL(5,2) NULL,
    is_acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by INT NULL,
    acknowledged_at TIMESTAMP NULL,
    resolved_at TIMESTAMP NULL,
    is_ignored BOOLEAN DEFAULT FALSE,
    ignored_by INT NULL,
    ignored_at TIMESTAMP NULL,
    ignore_until TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(device_id),
    FOREIGN KEY (interface_id) REFERENCES interfaces(interface_id),
    FOREIGN KEY (acknowledged_by) REFERENCES users(user_id),
    FOREIGN KEY (ignored_by) REFERENCES users(user_id)
);

-- Notifications
CREATE TABLE IF NOT EXISTS notification_settings (
    setting_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    alert_severity ENUM('warning', 'critical', 'info'),
    email_enabled BOOLEAN DEFAULT TRUE,
    sms_enabled BOOLEAN DEFAULT FALSE,
    webhook_url VARCHAR(500) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS notifications (
    notification_id INT AUTO_INCREMENT PRIMARY KEY,
    alert_id INT,
    user_id INT,
    notification_type ENUM('email', 'sms', 'webhook') NOT NULL,
    status ENUM('pending', 'sent', 'failed') DEFAULT 'pending',
    sent_at TIMESTAMP NULL,
    error_message TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Reports
CREATE TABLE IF NOT EXISTS reports (
    report_id INT AUTO_INCREMENT PRIMARY KEY,
    report_name VARCHAR(100) NOT NULL,
    report_type ENUM('availability', 'performance', 'syslog', 'custom') NOT NULL,
    parameters JSON,
    generated_by INT,
    file_path VARCHAR(500) NULL,
    status ENUM('pending', 'completed', 'failed') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    FOREIGN KEY (generated_by) REFERENCES users(user_id)
);

-- Insert default roles
INSERT IGNORE INTO roles (role_name, permissions) VALUES
('admin', '{"all": true}'),
('operator', '{"read": true, "write": true, "delete": false}'),
('viewer', '{"read": true, "write": false, "delete": false}');

-- Insert default admin user (password: admin123)
INSERT IGNORE INTO users (username, email, password_hash, role_id) VALUES
('admin', 'admin@nms.local', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6fM9q7F8e6', 1);