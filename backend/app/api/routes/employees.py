from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import AccountRecord, SessionRecord
from app.schemas import EmployeeOut, EmployeeCreate, EmployeeUpdate
from app.core.auth import hash_password
from app.core.audit import log_audit_action
from app.utils.helpers import to_employee_out

router = APIRouter(prefix=f"{settings.api_prefix}/employees", tags=["employees"])

@router.get("", response_model=list[EmployeeOut])
def list_employees(db: Session = Depends(get_db), _current_user: AccountRecord = Depends(get_current_user)) -> list[EmployeeOut]:
    accounts = db.scalars(select(AccountRecord).order_by(AccountRecord.created_at.desc())).all()
    return [to_employee_out(account, db) for account in accounts]

@router.post("", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: EmployeeCreate,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> EmployeeOut:
    email = payload.email.lower()
    if db.scalar(select(AccountRecord).where(AccountRecord.email == email)):
        raise HTTPException(status_code=409, detail=f"Account with email {email} already exists")

    try:
        record = AccountRecord(
            email=email,
            password_hash=hash_password(payload.password),
            name=payload.name,
            phone=payload.phone,
            role=payload.role,
            branch=payload.branch,
        )
        db.add(record)
        db.flush()
        log_audit_action(db, "created_employee", "Employee", record.id, payload.name, f"Created employee account {payload.name}")
        db.commit()
        db.refresh(record)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="Unable to create employee. The provided details may already exist.") from exc

    return to_employee_out(record, db)

@router.put("/{employee_id}", response_model=EmployeeOut)
def update_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> EmployeeOut:
    record = db.get(AccountRecord, employee_id)
    if not record:
        raise HTTPException(status_code=404, detail="Employee not found")

    if payload.name is not None:
        record.name = payload.name
    if payload.phone is not None:
        record.phone = payload.phone
    if payload.role is not None:
        record.role = payload.role
    if payload.branch is not None:
        record.branch = payload.branch
    if payload.password:
        record.password_hash = hash_password(payload.password)

    log_audit_action(db, "updated_employee", "Employee", record.id, _current_user.name, f"Updated employee {record.name}")
    db.commit()
    db.refresh(record)
    return to_employee_out(record, db)

@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: AccountRecord = Depends(get_current_user),
) -> None:
    if current_user.id == employee_id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")

    record = db.get(AccountRecord, employee_id)
    if not record:
        raise HTTPException(status_code=404, detail="Employee not found")

    sessions = db.scalars(select(SessionRecord).where(SessionRecord.user_id == employee_id)).all()
    for session in sessions:
        db.delete(session)

    log_audit_action(db, "deleted_employee", "Employee", record.id, current_user.name, f"Deleted employee {record.name}")
    db.delete(record)
    db.commit()