import re
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import JobRecord, AccountRecord, BinRecord, DiscountRecord
from app.schemas import ProfileData, EmployeeOut, BinOut, DiscountOut, JobOut
from app.utils.time import now_manila


def normalize_code(raw: str) -> str:
    return re.sub(r"[\s\-]", "", raw).upper()

def to_profile(account: AccountRecord) -> ProfileData:
    return ProfileData(
        name=account.name,
        phone=account.phone,
        email=account.email,
        role=account.role,
        branch=account.branch,
        photoUrl=account.photo_url,
    )

def to_employee_out(account: AccountRecord, db: Session) -> EmployeeOut:
    released_jobs = db.scalars(
        select(JobRecord).where(JobRecord.assigned_to == account.name, JobRecord.released.is_(True))
    ).all()
    return EmployeeOut(
        id=account.id,
        name=account.name,
        email=account.email,
        phone=account.phone,
        role=account.role,
        branch=account.branch,
        photoUrl=account.photo_url,
        joinDate=account.created_at,
        jobsCompleted=len(released_jobs),
        revenue=sum(job.total_payment for job in released_jobs),
        status="Active",
    )

def to_bin_out(bin_record: BinRecord, db: Session) -> BinOut:
    active_jobs = db.scalars(
        select(JobRecord).where(JobRecord.bin == bin_record.name, JobRecord.released.is_(False))
    ).all()
    occupied_count = sum(len(job.shoes or []) for job in active_jobs)
    available_count = max(bin_record.capacity - occupied_count - bin_record.reserved, 0)
    return BinOut(
        id=bin_record.id,
        name=bin_record.name,
        branch=bin_record.branch,
        capacity=bin_record.capacity,
        reserved=bin_record.reserved,
        active=bin_record.active,
        occupiedCount=occupied_count,
        availableCount=available_count,
        createdAt=bin_record.created_at,
        updatedAt=bin_record.updated_at,
    )

def to_discount_out(discount: DiscountRecord) -> DiscountOut:
    return DiscountOut(
        id=discount.id,
        name=discount.name,
        code=discount.code,
        percent=discount.percent,
        maxUses=discount.max_uses,
        timesUsed=discount.times_used,
        expiresAt=discount.expires_at,
        active=discount.active,
    )

def to_job_out(job: JobRecord) -> JobOut:
    return JobOut(
        id=job.id,
        customer=job.customer,
        phone=job.phone,
        email=job.email,
        dateReceived=job.date_received,
        expectedRelease=job.expected_release,
        shoes=job.shoes or [],
        bin=job.bin,
        status=job.status,
        receiveUpdates=job.receive_updates,
        totalPayment=job.total_payment,
        notes=job.notes,
        assignedTo=job.assigned_to,
        branch=job.branch,
        released=job.released,
        signatureDataUrl=job.signature_data_url,
        discountCode=job.discount_code,
        discountName=job.discount_name,
        discountPercent=job.discount_percent,
        discountAmount=job.discount_amount,
        createdAt=job.created_at,
        updatedAt=job.updated_at,
    )

def to_pricing_out(pricing):
    from app.schemas import PricingOut
    return PricingOut(
        id=pricing.id,
        name=pricing.name,
        description=pricing.description,
        price=pricing.price,
        category=pricing.category,
        duration_days=pricing.duration_days,
        is_active=pricing.is_active,
        created_at=pricing.created_at,
        updated_at=pricing.updated_at,
    )

def to_branch_out(branch):
    from app.schemas import BranchOut
    return BranchOut(
        id=branch.id,
        name=branch.name,
        code=branch.code,
        address=branch.address,
        manager=branch.manager,
        active=branch.active,
        createdAt=branch.created_at,
        updatedAt=branch.updated_at,
    )

def generate_job_id(db: Session) -> str:
    date_str = now_manila().strftime("%Y%m%d")
    prefix = f"TK-{date_str}-"
    count_stmt = select(JobRecord.id).where(JobRecord.id.startswith(prefix))
    today_ids = db.scalars(count_stmt).all()
    sequence = len(today_ids) + 1
    return f"{prefix}{sequence:03d}"

def apply_job_update(record: JobRecord, payload) -> None:
    record.customer = payload.customer
    record.phone = payload.phone
    record.email = payload.email
    record.date_received = payload.dateReceived
    record.expected_release = payload.expectedRelease
    record.shoes = [shoe.model_dump() for shoe in payload.shoes]
    record.bin = payload.bin
    record.status = payload.status
    record.receive_updates = payload.receiveUpdates
    record.total_payment = payload.totalPayment
    record.notes = payload.notes
    record.assigned_to = payload.assignedTo
    record.branch = payload.branch
    record.released = payload.released
    record.signature_data_url = payload.signatureDataUrl
    record.discount_code = payload.discountCode
    record.discount_name = payload.discountName
    record.discount_percent = payload.discountPercent
    record.discount_amount = payload.discountAmount

def consume_discount_code(db: Session, code: str | None) -> None:
    from fastapi import HTTPException
    if not code:
        return
    normalized = code.strip().upper()
    discount = db.scalar(select(DiscountRecord).where(DiscountRecord.code == normalized))
    if discount is None:
        raise HTTPException(status_code=400, detail=f"Discount code {normalized} not found")
    if not discount.active:
        raise HTTPException(status_code=400, detail="Discount code is no longer active")
    if discount.expires_at and discount.expires_at < now_manila():
        raise HTTPException(status_code=400, detail="Discount code has expired")
    if discount.max_uses is not None and discount.times_used >= discount.max_uses:
        raise HTTPException(status_code=400, detail="Discount code has reached its usage limit")
    discount.times_used += 1