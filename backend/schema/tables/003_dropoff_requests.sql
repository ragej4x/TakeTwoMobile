-- Table: dropoff_requests
CREATE TABLE IF NOT EXISTS dropoff_requests (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  qr_code_id INTEGER NOT NULL,
  customer_id INTEGER NOT NULL,
  customer_account_id INTEGER,
  shoe_brand VARCHAR(100),
  shoe_model VARCHAR(150),
  shoe_color VARCHAR(100),
  service_type VARCHAR(100),
  special_instructions TEXT,
  photo_urls JSON,
  bin VARCHAR(20),
  sponsored BOOLEAN NOT NULL DEFAULT FALSE,
  status VARCHAR(40) NOT NULL DEFAULT 'pending',
  rejection_reason TEXT,
  branch_id INTEGER,
  reviewed_by_staff_id INTEGER,
  submitted_at DATETIME DEFAULT (CURRENT_TIMESTAMP),
  reviewed_at DATETIME,
  completed_at DATETIME,
  updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_qr_code_per_request ON dropoff_requests(qr_code_id);
