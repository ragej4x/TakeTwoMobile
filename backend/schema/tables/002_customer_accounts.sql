-- Table: customer_accounts
CREATE TABLE IF NOT EXISTS customer_accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  full_name VARCHAR(255) NOT NULL,
  phone_number VARCHAR(20) NOT NULL,
  email VARCHAR(255),
  password_hash VARCHAR(512),
  photo_url TEXT,
  branch VARCHAR(120),
  address VARCHAR(255),
  created_at DATETIME DEFAULT (CURRENT_TIMESTAMP)
);

CREATE INDEX IF NOT EXISTS ix_customer_accounts_phone_number ON customer_accounts(phone_number);
