-- Table: pricing
CREATE TABLE IF NOT EXISTS pricing (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name VARCHAR(200) NOT NULL,
  description VARCHAR(500),
  price REAL NOT NULL,
  category VARCHAR(100),
  duration_days INTEGER,
  is_active BOOLEAN DEFAULT 1,
  created_at DATETIME DEFAULT (CURRENT_TIMESTAMP),
  updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP)
);
