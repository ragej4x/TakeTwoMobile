-- Adds discount support to an existing database.
-- Safe to run multiple times (IF NOT EXISTS guards).

ALTER TABLE jobs ADD COLUMN IF NOT EXISTS discount_code VARCHAR(40);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS discount_name VARCHAR(200);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS discount_percent FLOAT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS discount_amount FLOAT;

CREATE TABLE IF NOT EXISTS accounts (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(512) NOT NULL,
    name VARCHAR(200) NOT NULL,
    phone VARCHAR(40) NOT NULL DEFAULT '',
    role VARCHAR(100) NOT NULL DEFAULT 'Staff',
    branch VARCHAR(120) NOT NULL DEFAULT 'Main Branch',
    is_test_account BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    photo_url VARCHAR
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_accounts_email ON accounts (email);

CREATE TABLE IF NOT EXISTS bins (
    id SERIAL PRIMARY KEY,
    name VARCHAR(60) NOT NULL UNIQUE,
    branch VARCHAR(120) NOT NULL DEFAULT 'Main Branch',
    capacity INTEGER NOT NULL DEFAULT 12,
    reserved INTEGER NOT NULL DEFAULT 0,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_bins_name ON bins (name);

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

CREATE TABLE IF NOT EXISTS pricing (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description VARCHAR(500),
    price FLOAT NOT NULL,
    category VARCHAR(100),
    duration_days INTEGER,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    action VARCHAR(200) NOT NULL DEFAULT '',
    entity_type VARCHAR(100) NOT NULL DEFAULT '',
    entity_id VARCHAR(120) NOT NULL DEFAULT '',
    user_name VARCHAR(200) NOT NULL DEFAULT '',
    details VARCHAR(2000) NOT NULL DEFAULT '',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs (created_at DESC);

CREATE TABLE IF NOT EXISTS branches (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL UNIQUE,
    code VARCHAR(40) NOT NULL UNIQUE,
    address VARCHAR(500) NOT NULL DEFAULT '',
    manager VARCHAR(200) NOT NULL DEFAULT '',
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_branches_name ON branches (name);
CREATE INDEX IF NOT EXISTS ix_branches_code ON branches (code);






