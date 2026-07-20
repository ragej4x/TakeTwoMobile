-- ============================================================
-- Smart Shoe Drop-Off System — PostgreSQL Schema
-- ============================================================

-- ---------- Enums ----------
CREATE TYPE request_status AS ENUM (
    'pending',          -- submitted by customer, awaiting staff review
    'approved',         -- staff approved, job accepted
    'rejected',         -- staff rejected the request
    'in_progress',      -- cleaning/restoration underway
    'ready_for_pickup', -- finished, waiting for customer
    'completed',        -- picked up by customer
    'cancelled'         -- cancelled by staff or customer
);

-- ---------- QR / Sticker Codes ----------
-- One row per physical sticker printed. `code` is a fully random 8-character
-- opaque string (see qr_utils.py) — it does NOT encode the date, a sequence
-- number, or anything else guessable. Knowing one valid code gives no
-- information about any other. If you want the print date for staff
-- reference, use created_at — don't derive it from the code.
CREATE TABLE qr_codes (
    id             SERIAL PRIMARY KEY,
    code           VARCHAR(8) UNIQUE NOT NULL,   -- e.g. 'XK4P7QRT'
    is_used        BOOLEAN NOT NULL DEFAULT FALSE,
    branch_id      INT,                            -- which branch printed/owns this sticker
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    used_at        TIMESTAMPTZ
);

CREATE INDEX idx_qr_codes_code ON qr_codes (code);
CREATE INDEX idx_qr_codes_is_used ON qr_codes (is_used);

-- ---------- Registered Customer Accounts ----------
-- Accounts created for customers who sign in / have a profile.
CREATE TABLE customer_accounts (
    id             SERIAL PRIMARY KEY,
    full_name      VARCHAR(255) NOT NULL,
    phone_number   VARCHAR(20) NOT NULL,
    email          VARCHAR(255),
    password_hash  VARCHAR(512),
    photo_url      VARCHAR(255),
    branch         VARCHAR(255),
    address        VARCHAR(255),
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_customer_accounts_phone ON customer_accounts (phone_number);

-- ---------- Customers ----------
-- Lightweight — created/looked-up at drop-off time, no login required.
CREATE TABLE customers (
    id             SERIAL PRIMARY KEY,
    full_name      VARCHAR(255) NOT NULL,
    phone_number   VARCHAR(20) NOT NULL,
    email          VARCHAR(255),
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_customers_phone ON customers (phone_number);

-- ---------- Drop-off Requests ----------
-- The core object: one shoe box/bag = one QR code = one request.
CREATE TABLE dropoff_requests (
    id                    SERIAL PRIMARY KEY,
    qr_code_id            INT NOT NULL REFERENCES qr_codes(id) ON DELETE RESTRICT,
    customer_id           INT NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    customer_account_id   INT REFERENCES customer_accounts(id) ON DELETE SET NULL,

    shoe_brand            VARCHAR(100),
    shoe_model            VARCHAR(150),
    shoe_color             VARCHAR(100),
    service_type           VARCHAR(100),          -- e.g. 'basic_clean', 'deep_clean', 'restoration'
    special_instructions    TEXT,
    photo_urls              TEXT[] DEFAULT '{}',   -- customer-submitted reference photos (Supabase URLs)
    bin                     VARCHAR(20),
    sponsored               BOOLEAN NOT NULL DEFAULT FALSE,

    status                 request_status NOT NULL DEFAULT 'pending',
    rejection_reason        TEXT,
    
    branch_id               INT,
    reviewed_by_staff_id     INT,                  -- FK to your existing staff/employees table
    submitted_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    reviewed_at               TIMESTAMPTZ,
    completed_at               TIMESTAMPTZ,
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_qr_code_per_request UNIQUE (qr_code_id)
);

CREATE INDEX idx_dropoff_requests_status ON dropoff_requests (status);
CREATE INDEX idx_dropoff_requests_customer ON dropoff_requests (customer_id);
CREATE INDEX idx_dropoff_requests_submitted_at ON dropoff_requests (submitted_at DESC);

-- keep updated_at fresh
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_dropoff_requests_updated_at
BEFORE UPDATE ON dropoff_requests
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ---------- Status History (optional but useful for auditing) ----------
CREATE TABLE dropoff_status_history (
    id            SERIAL PRIMARY KEY,
    request_id    INT NOT NULL REFERENCES dropoff_requests(id) ON DELETE CASCADE,
    old_status    request_status,
    new_status    request_status NOT NULL,
    changed_by_staff_id INT,
    note          TEXT,
    changed_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_status_history_request ON dropoff_status_history (request_id);