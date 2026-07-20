-- Combined schema (run this on a new database). Order aims to satisfy FK presence.
PRAGMA foreign_keys = ON;

@include: tables/001_qr_codes.sql
@include: tables/002_customer_accounts.sql
@include: tables/003_customers.sql
@include: tables/004_dropoff_requests.sql
@include: tables/005_dropoff_status_history.sql
@include: tables/006_branches.sql
@include: tables/007_jobs.sql
@include: tables/008_profile.sql
@include: tables/009_app_settings.sql
@include: tables/010_accounts.sql
@include: tables/011_bins.sql
@include: tables/012_sessions.sql
@include: tables/013_discounts.sql
@include: tables/014_password_reset_codes.sql
@include: tables/015_audit_logs.sql
@include: tables/016_pricing.sql

-- Note: The @include lines are a convenience for humans. To execute, concatenate the files or use a tool/script to apply each file in order.
