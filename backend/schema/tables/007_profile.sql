-- Table: profile
CREATE TABLE IF NOT EXISTS profile (
  id INTEGER PRIMARY KEY DEFAULT 1,
  name VARCHAR(200),
  phone VARCHAR(40),
  email VARCHAR(255),
  role VARCHAR(100),
  branch VARCHAR(120),
  updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP)
);
