-- Table: accounts
CREATE TABLE IF NOT EXISTS accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(512) NOT NULL,
  name VARCHAR(200) NOT NULL,
  phone VARCHAR(40) DEFAULT '',
  role VARCHAR(100) DEFAULT 'Staff',
  branch VARCHAR(120) DEFAULT 'Main Branch',
  photo_url TEXT,
  created_at DATETIME DEFAULT (CURRENT_TIMESTAMP),
  updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP)
);

CREATE INDEX IF NOT EXISTS ix_accounts_email ON accounts(email);
