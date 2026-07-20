-- Table: branches
CREATE TABLE IF NOT EXISTS branches (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name VARCHAR(200) NOT NULL UNIQUE,
  code VARCHAR(40) NOT NULL UNIQUE,
  address VARCHAR(500),
  manager VARCHAR(200),
  active BOOLEAN DEFAULT 1,
  created_at DATETIME DEFAULT (CURRENT_TIMESTAMP),
  updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP)
);

CREATE INDEX IF NOT EXISTS ix_branches_name ON branches(name);
CREATE INDEX IF NOT EXISTS ix_branches_code ON branches(code);
