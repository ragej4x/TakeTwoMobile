-- Table: discounts
CREATE TABLE IF NOT EXISTS discounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name VARCHAR(200) NOT NULL,
  code VARCHAR(40) NOT NULL UNIQUE,
  percent REAL NOT NULL,
  max_uses INTEGER,
  times_used INTEGER DEFAULT 0,
  expires_at DATETIME,
  active BOOLEAN DEFAULT 1,
  created_at DATETIME DEFAULT (CURRENT_TIMESTAMP),
  updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP)
);

CREATE INDEX IF NOT EXISTS ix_discounts_code ON discounts(code);
