from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import AccountRecord, BranchRecord
from app.schemas import BranchCreate, BranchUpdate, BranchOut
from app.core.audit import log_audit_action
from app.utils.helpers import to_branch_out

router = APIRouter(prefix=f"{settings.api_prefix}/branches", tags=["branches"])

@router.get("", response_model=list[BranchOut])
def list_branches(db: Session = Depends(get_db), _current_user: AccountRecord = Depends(get_current_user)) -> list[BranchOut]:
    branches = db.scalars(select(BranchRecord).order_by(BranchRecord.created_at.desc())).all()
    return [to_branch_out(branch) for branch in branches]

@router.post("", response_model=BranchOut, status_code=status.HTTP_201_CREATED)
def create_branch(
    payload: BranchCreate,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> BranchOut:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Branch name is required")

    code = payload.code.strip().upper()
    if code and db.scalar(select(BranchRecord).where(BranchRecord.code == code)):
        raise HTTPException(status_code=409, detail=f"Branch code {code} already exists")
    if db.scalar(select(BranchRecord).where(BranchRecord.name == name)):
        raise HTTPException(status_code=409, detail=f"Branch {name} already exists")

    record = BranchRecord(name=name, code=code, address=payload.address or "", manager=payload.manager or "", active=payload.active)
    db.add(record)
    db.flush()
    log_audit_action(db, "created_branch", "Branch", record.id, _current_user.name, f"Created branch {record.name}")
    db.commit()
    db.refresh(record)
    return to_branch_out(record)

@router.put("/{branch_id}", response_model=BranchOut)
def update_branch(
    branch_id: int,
    payload: BranchUpdate,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> BranchOut:
    record = db.get(BranchRecord, branch_id)
    if not record:
        raise HTTPException(status_code=404, detail="Branch not found")

    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="Branch name is required")
        if name != record.name and db.scalar(select(BranchRecord).where(BranchRecord.name == name)):
            raise HTTPException(status_code=409, detail=f"Branch {name} already exists")
        record.name = name

    if payload.code is not None:
        code = payload.code.strip().upper()
        if code and code != record.code and db.scalar(select(BranchRecord).where(BranchRecord.code == code)):
            raise HTTPException(status_code=409, detail=f"Branch code {code} already exists")
        record.code = code

    if payload.address is not None:
        record.address = payload.address or ""
    if payload.manager is not None:
        record.manager = payload.manager or ""
    if payload.active is not None:
        record.active = payload.active

    log_audit_action(db, "updated_branch", "Branch", record.id, _current_user.name, f"Updated branch {record.name}")
    db.commit()
    db.refresh(record)
    return to_branch_out(record)

@router.delete("/{branch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_branch(
    branch_id: int,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> None:
    record = db.get(BranchRecord, branch_id)
    if not record:
        raise HTTPException(status_code=404, detail="Branch not found")
    log_audit_action(db, "deleted_branch", "Branch", record.id, _current_user.name, f"Deleted branch {record.name}")
    db.delete(record)
    db.commit()