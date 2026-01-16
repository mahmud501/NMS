-- Database schema for NMS Project
-- Run this script to create all necessary tables

-- Users and Roles
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(device_id),
    FOREIGN KEY (interface_id) REFERENCES interfaces(interface_id),
    FOREIGN KEY (acknowledged_by) REFERENCES users(user_id)
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