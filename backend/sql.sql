-- Adds discount support to an existing database.
-- Safe to run multiple times (IF NOT EXISTS guards).

ALTER TABLE jobs ADD COLUMN IF NOT EXISTS discount_code VARCHAR(40);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS discount_name VARCHAR(200);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS discount_percent FLOAT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS discount_amount FLOAT;

CREATE TABLE IF NOT EXISTS discounts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    code VARCHAR(40) NOT NULL UNIQUE,
    percent FLOAT NOT NULL,
    max_uses INTEGER,
    times_used INTEGER NOT NULL DEFAULT 0,
    expires_at TIMESTAMP,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_discounts_code ON discounts (code);