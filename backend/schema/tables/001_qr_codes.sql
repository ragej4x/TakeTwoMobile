-- Table: qr_codes
CREATE TABLE IF NOT EXISTS qr_codes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code VARCHAR(8) NOT NULL UNIQUE,
  is_used BOOLEAN NOT NULL DEFAULT 0,
  branch_id INTEGER,
  created_at DATETIME DEFAULT (CURRENT_TIMESTAMP),
  used_at DATETIME
);

CREATE INDEX IF NOT EXISTS ix_qr_codes_code ON qr_codes(code);
CREATE INDEX IF NOT EXISTS ix_qr_codes_is_used ON qr_codes(is_used);
