-- Table: dropoff_status_history
CREATE TABLE IF NOT EXISTS dropoff_status_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  request_id INTEGER NOT NULL,
  old_status VARCHAR(40),
  new_status VARCHAR(40) NOT NULL,
  changed_by_staff_id INTEGER,
  note TEXT,
  changed_at DATETIME DEFAULT (CURRENT_TIMESTAMP)
);
