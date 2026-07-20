-- Table: app_settings
CREATE TABLE IF NOT EXISTS app_settings (
  id INTEGER PRIMARY KEY DEFAULT 1,
  conn_status VARCHAR(40) DEFAULT 'connected',
  theme VARCHAR(40) DEFAULT 'light',
  branch VARCHAR(120) DEFAULT 'Main Branch',
  selected_printer VARCHAR(120) DEFAULT 'Brother QL-820NWB',
  updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP)
);
