# TakeTwo FastAPI Backend
FastAPI backend for the TakeTwo mobile/web frontend.

## Features

- SQLite persistence for jobs, profile, and app settings
- CORS ready for local Vite frontend
- API endpoints for:
  - Cookie-based auth login/logout/session
  - Password reset code request/verify/confirm
  - Test account creation endpoint
  - Jobs CRUD + status/release actions
  - Profile read/update
  - Settings read/update
  - Bin summary view

## Default Test Account

- Email: `admin@taketwo.ph`
- Password: `admin123`

## Run Locally

1. Create and activate a virtual environment.

Windows PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies.

```powershell
pip install -r requirements.txt
```

3. (Optional) Configure environment values.

```powershell
copy .env.example .env
```

4. Start the API.

```powershell
 uvicorn app.index:app --reload --port 8000
```

Open http://127.0.0.1:8000/docs for Swagger UI.

## API Prefix

All endpoints are under `/api` by default.

## Main Endpoints

- `GET /api/health`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/session`
- `POST /api/auth/password-reset/request`
- `POST /api/auth/password-reset/verify`
- `POST /api/auth/password-reset/confirm`
- `POST /api/auth/test-account`
- `GET /api/jobs`
- `POST /api/jobs`
- `GET /api/jobs/{job_id}`
- `PUT /api/jobs/{job_id}`
- `PATCH /api/jobs/{job_id}/status`
- `PATCH /api/jobs/{job_id}/release`
- `DELETE /api/jobs/{job_id}`
- `GET /api/bins`
- `GET /api/profile`
- `PUT /api/profile`
- `GET /api/settings`
- `PUT /api/settings`






## PATH VISUALIZATION

```
taketwo-backend/
│
├── app/
│   ├── __init__.py
│   │
│   ├── main.py                          # FastAPI app setup, CORS, health check
│   ├── config.py                        # Settings & environment variables
│   ├── database.py                      # Database connection & initialization
│   ├── models.py                        # All SQLAlchemy models
│   ├── schemas.py                       # All Pydantic schemas
│   ├── deps.py                          # Dependencies (get_current_user)
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── auth.py                      # Password hashing, session management
│   │   └── audit.py                     # Audit logging helper
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   └── helpers.py                   # Shared helper functions (to_*_out, generate_job_id, etc.)
│   │
│   └── api/
│       ├── __init__.py
│       │
│       └── routes/
│           ├── __init__.py              # Exports all route modules
│           ├── auth.py                  # /auth/* endpoints (login, logout, session, password reset)
│           ├── profile.py               # /profile/* endpoints
│           ├── employees.py             # /employees/* endpoints
│           ├── branches.py              # /branches/* endpoints
│           ├── jobs.py                  # /jobs/* endpoints
│           ├── bins.py                  # /bins/* endpoints
│           ├── discounts.py             # /discounts/* endpoints
│           ├── pricing.py               # /pricing/* endpoints
│           ├── settings.py              # /settings/* endpoints
│           └── audit_logs.py            # /audit-logs/* endpoints
│
├── .env                                 # Environment variables
├── requirements.txt                     # Python dependencies
└── taketwo.db                           # SQLite database (auto-created)
```



## File Descriptions & Dependencies


Core Files (app/)
File	Purpose	Imports From
main.py	FastAPI app setup, CORS, router registration	config, database, all routes
config.py	Settings class with environment variables	dotenv, os
database.py	Database engine, session, Base class, initialization	config, models
models.py	All SQLAlchemy ORM models	database (Base)
schemas.py	All Pydantic request/response schemas	pydantic
deps.py	Authentication dependency (get_current_user)	database, models
Core Helpers (app/core/)
File	Purpose	Imports From
auth.py	Password hashing, session creation/cookies	models (SessionRecord)
audit.py	Audit log creation helper	models (AuditLogRecord)
Utils (app/utils/)
File	Purpose	Imports From
helpers.py	Shared conversion functions (to_*_out), job ID generation, discount validation	models, schemas
API Routes (app/api/routes/)
File	Endpoint Prefix	Purpose
auth.py	/api/auth	Login, logout, session, password reset
profile.py	/api/profile	Get/update user profile
employees.py	/api/employees	CRUD for employee accounts
branches.py	/api/branches	CRUD for branches
jobs.py	/api/jobs	CRUD for jobs, status updates, release
bins.py	/api/bins	CRUD for bins, bin summary
discounts.py	/api/discounts	CRUD for discounts, validate discount
pricing.py	/api/pricing	CRUD for pricing items, categories, bulk create
settings.py	/api/settings	Get/update app settings
audit_logs.py	/api/audit-logs	List audit logs




## IMPORT FLOW



```
main.py
  ├── from app.config import settings
  ├── from app.database import Base, engine
  ├── from app.api.routes import (...)
  │   └── routes/__init__.py
  │       ├── from .auth import router
  │       ├── from .profile import router
  │       ├── from .employees import router
  │       ├── from .branches import router
  │       ├── from .jobs import router
  │       ├── from .bins import router
  │       ├── from .discounts import router
  │       ├── from .pricing import router
  │       ├── from .settings import router
  │       └── from .audit_logs import router
  │
  └── app.include_router(...)

Each route file:
  ├── from app.config import settings
  ├── from app.database import get_db
  ├── from app.deps import get_current_user
  ├── from app.models import (...)
  ├── from app.schemas import (...)
  ├── from app.core.auth import (...)
  ├── from app.core.audit import log_audit_action
  └── from app.utils.helpers import (...)

## Database schema files

All database DDL is now available as individual SQL files under `schema/tables/` and a combined helper file `schema/all_tables.sql`.

- `schema/tables/001_qr_codes.sql` — QR codes table and indexes
- `schema/tables/002_customers.sql` — Customers table
- `schema/tables/003_dropoff_requests.sql` — Drop-off requests
- `schema/tables/004_dropoff_status_history.sql` — Status history for drop-offs
- `schema/tables/005_branches.sql` — Branches table
- `schema/tables/006_jobs.sql` — Jobs table
- `schema/tables/007_profile.sql` — Single-row profile table
- `schema/tables/008_app_settings.sql` — App settings single-row table
- `schema/tables/009_accounts.sql` — Account records and index
- `schema/tables/010_bins.sql` — Bins
- `schema/tables/011_sessions.sql` — Session tokens
- `schema/tables/012_discounts.sql` — Discounts
- `schema/tables/013_password_reset_codes.sql` — Password reset codes
- `schema/tables/014_audit_logs.sql` — Audit logs
- `schema/tables/015_pricing.sql` — Pricing items

To initialize a fresh SQLite database locally, you can concatenate and run the files in order. Example (PowerShell):

```powershell
Get-Content schema\tables\*.sql | Out-File combined.sql -Encoding utf8
sqlite3 taketwo.db < combined.sql
```

Or run the single helper file after concatenating includes manually.

Notes:
- The SQL files are written to be compatible with SQLite and are intentionally conservative (simple types, explicit defaults). If you target PostgreSQL or other RDBMS, adjust types (e.g. `JSON`/`TEXT`) and constraints as needed.
- These files mirror the SQLAlchemy models in `app/models.py`. No schema-altering migrations were generated — if you use Alembic in production, translate these DDL snippets to proper migration scripts.
```