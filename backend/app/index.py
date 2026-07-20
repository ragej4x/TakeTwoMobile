from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.api.routes import auth, profile, employees, branches, jobs, bins, discounts, pricing, settings as settings_routes, audit_logs
from app.api.store import dropoff_router, qr_router, staff_router

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@app.get(f"{settings.api_prefix}/health")
def health_check() -> dict:
    return {"status": "ok", "service": settings.app_name}

# Include routers
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(employees.router)
app.include_router(branches.router)
app.include_router(jobs.router)
app.include_router(bins.router)
app.include_router(discounts.router)
app.include_router(pricing.router)
app.include_router(settings_routes.router)
app.include_router(audit_logs.router)
app.include_router(dropoff_router)
app.include_router(qr_router)
app.include_router(staff_router)
