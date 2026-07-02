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
uvicorn app.main:app --reload --port 8000
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
