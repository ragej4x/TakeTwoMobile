-- Table: audit_logs
CREATE TABLE IF NOT EXISTS audit_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  action VARCHAR(200) NOT NULL DEFAULT '',
  entity_type VARCHAR(100) NOT NULL DEFAULT '',
  entity_id VARCHAR(120) NOT NULL DEFAULT '',
  user_name VARCHAR(200) NOT NULL DEFAULT '',
  details VARCHAR(2000) NOT NULL DEFAULT '',
  created_at DATETIME DEFAULT (CURRENT_TIMESTAMP)
);

CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs(created_at);
