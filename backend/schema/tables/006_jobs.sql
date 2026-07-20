-- Table: jobs
CREATE TABLE IF NOT EXISTS jobs (
  id VARCHAR(40) PRIMARY KEY,
  customer VARCHAR(200) NOT NULL,
  phone VARCHAR(40),
  email VARCHAR(255),
  date_received VARCHAR(20) NOT NULL,
  expected_release VARCHAR(20),
  shoes JSON,
  bin VARCHAR(20),
  status VARCHAR(40) NOT NULL,
  receive_updates BOOLEAN DEFAULT 0,
  total_payment REAL DEFAULT 0.0,
  notes VARCHAR(2000),
  assigned_to VARCHAR(200),
  branch VARCHAR(120),
  released BOOLEAN DEFAULT 0,
  signature_data_url TEXT,
  discount_code VARCHAR(40),
  discount_name VARCHAR(200),
  discount_percent REAL,
  discount_amount REAL,
  created_at DATETIME DEFAULT (CURRENT_TIMESTAMP),
  updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP)
);

CREATE INDEX IF NOT EXISTS ix_jobs_created_at ON jobs(created_at);
