from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import AccountRecord, BinRecord, JobRecord
from app.schemas import BinCreate, BinUpdate, BinOut, BinSummary
from app.core.audit import log_audit_action
from app.utils.helpers import to_bin_out

ALL_BINS = ["A-01", "A-02", "A-03", "B-01", "B-02", "B-03", "B-04", "C-01", "C-02"]
router = APIRouter(prefix=f"{settings.api_prefix}/bins", tags=["bins"])

@router.get("", response_model=list[BinOut])
def list_bins(db: Session = Depends(get_db), _current_user: AccountRecord = Depends(get_current_user)) -> list[BinOut]:
    bins = db.scalars(select(BinRecord).order_by(BinRecord.created_at.desc())).all()
    return [to_bin_out(bin_record, db) for bin_record in bins]

@router.post("", response_model=BinOut, status_code=status.HTTP_201_CREATED)
def create_bin(
    payload: BinCreate,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> BinOut:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Bin name is required")

    if db.scalar(select(BinRecord).where(BinRecord.name == name)):
        raise HTTPException(status_code=409, detail=f"Bin {name} already exists")

    record = BinRecord(
        name=name,
        branch=payload.branch.strip() or "Main Branch",
        capacity=payload.capacity,
        reserved=payload.reserved,
        active=payload.active,
    )
    db.add(record)
    db.flush()
    log_audit_action(db, "created_bin", "Bin", record.id, _current_user.name, f"Created bin {record.name}")
    db.commit()
    db.refresh(record)
    return to_bin_out(record, db)

@router.put("/{bin_id}", response_model=BinOut)
def update_bin(
    bin_id: int,
    payload: BinUpdate,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> BinOut:
    record = db.get(BinRecord, bin_id)
    if not record:
        raise HTTPException(status_code=404, detail="Bin not found")

    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="Bin name is required")
        if name != record.name and db.scalar(select(BinRecord).where(BinRecord.name == name)):
            raise HTTPException(status_code=409, detail=f"Bin {name} already exists")
        record.name = name

    if payload.branch is not None:
        record.branch = payload.branch.strip() or "Main Branch"
    if payload.capacity is not None:
        record.capacity = payload.capacity
    if payload.reserved is not None:
        record.reserved = payload.reserved
    if payload.active is not None:
        record.active = payload.active

    log_audit_action(db, "updated_bin", "Bin", record.id, _current_user.name, f"Updated bin {record.name}")
    db.commit()
    db.refresh(record)
    return to_bin_out(record, db)

@router.delete("/{bin_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bin(
    bin_id: int,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> None:
    record = db.get(BinRecord, bin_id)
    if not record:
        raise HTTPException(status_code=404, detail="Bin not found")
    log_audit_action(db, "deleted_bin", "Bin", record.id, _current_user.name, f"Deleted bin {record.name}")
    db.delete(record)
    db.commit()

@router.get("/summary", response_model=list[BinSummary])
def get_bins_summary(
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> list[BinSummary]:
    active_jobs = db.scalars(select(JobRecord).where(JobRecord.released.is_(False))).all()
    bin_names = [record.name for record in db.scalars(select(BinRecord).where(BinRecord.active.is_(True))).all()]
    if not bin_names:
        bin_names = ALL_BINS

    bins: dict[str, list[JobRecord]] = {name: [] for name in bin_names}
    for job in active_jobs:
        if job.bin in bins:
            bins[job.bin].append(job)

    summaries: list[BinSummary] = []
    for bin_name in bin_names:
        jobs_in_bin = bins[bin_name]
        summaries.append(
            BinSummary(
                bin=bin_name,
                occupied=len(jobs_in_bin) > 0,
                orderCount=len(jobs_in_bin),
                pairCount=sum(len(job.shoes or []) for job in jobs_in_bin),
                jobs=[job.id for job in jobs_in_bin],
            )
        )

    return summaries    