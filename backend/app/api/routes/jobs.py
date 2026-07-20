from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import AccountRecord, JobRecord
from app.schemas import JobCreate, JobUpdate, JobOut, JobStatusUpdate
from app.core.audit import log_audit_action
from app.utils.helpers import generate_job_id, apply_job_update, consume_discount_code, to_job_out

router = APIRouter(prefix=f"{settings.api_prefix}/jobs", tags=["jobs"])

@router.get("", response_model=list[JobOut])
def list_jobs(
    q: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    released: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> list[JobOut]:
    jobs = db.scalars(select(JobRecord).order_by(JobRecord.created_at.desc())).all()

    if q:
        query = q.lower()
        jobs = [
            job for job in jobs
            if query in job.id.lower() or query in job.customer.lower() or query in (job.bin or "").lower()
        ]

    if status_filter:
        jobs = [job for job in jobs if job.status == status_filter]

    if released is not None:
        jobs = [job for job in jobs if job.released is released]

    return [to_job_out(job) for job in jobs]

@router.post("", response_model=JobOut, status_code=status.HTTP_201_CREATED)
def create_job(
    payload: JobCreate,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> JobOut:
    job_id = payload.id or generate_job_id(db)
    if db.get(JobRecord, job_id):
        raise HTTPException(status_code=409, detail=f"Job {job_id} already exists")

    record = JobRecord(id=job_id, customer=payload.customer, date_received=payload.dateReceived, status=payload.status)
    apply_job_update(record, payload)
    consume_discount_code(db, payload.discountCode)
    db.add(record)
    log_audit_action(db, "created_job", "Job", record.id, _current_user.name, f"Created job {record.id}")
    db.commit()
    db.refresh(record)
    return to_job_out(record)

@router.get("/{job_id}", response_model=JobOut)
def get_job(
    job_id: str,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> JobOut:
    record = db.get(JobRecord, job_id)
    if not record:
        raise HTTPException(status_code=404, detail="Job not found")
    return to_job_out(record)

@router.put("/{job_id}", response_model=JobOut)
def update_job(
    job_id: str,
    payload: JobUpdate,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> JobOut:
    record = db.get(JobRecord, job_id)
    if not record:
        raise HTTPException(status_code=404, detail="Job not found")
    apply_job_update(record, payload)
    log_audit_action(db, "updated_job", "Job", record.id, _current_user.name, f"Updated job {record.id}")
    db.commit()
    db.refresh(record)
    return to_job_out(record)

@router.patch("/{job_id}/status", response_model=JobOut)
def update_job_status(
    job_id: str,
    payload: JobStatusUpdate,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> JobOut:
    record = db.get(JobRecord, job_id)
    if not record:
        raise HTTPException(status_code=404, detail="Job not found")
    record.status = payload.status
    log_audit_action(db, "updated_job_status", "Job", record.id, _current_user.name, f"Updated job status to {payload.status}")
    db.commit()
    db.refresh(record)
    return to_job_out(record)

@router.patch("/{job_id}/release", response_model=JobOut)
def mark_job_released(
    job_id: str,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> JobOut:
    record = db.get(JobRecord, job_id)
    if not record:
        raise HTTPException(status_code=404, detail="Job not found")
    record.released = True
    record.bin = ""
    log_audit_action(db, "released_job", "Job", record.id, _current_user.name, f"Released job {record.id}")
    db.commit()
    db.refresh(record)
    return to_job_out(record)

@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: str,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> None:
    record = db.get(JobRecord, job_id)
    if not record:
        raise HTTPException(status_code=404, detail="Job not found")
    log_audit_action(db, "deleted_job", "Job", record.id, _current_user.name, f"Deleted job {record.id}")
    db.delete(record)
    db.commit()