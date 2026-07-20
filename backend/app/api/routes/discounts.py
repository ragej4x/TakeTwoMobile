from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import AccountRecord, DiscountRecord
from app.schemas import DiscountCreate, DiscountUpdate, DiscountOut, DiscountValidateRequest, DiscountValidateResponse
from app.core.audit import log_audit_action
from app.utils.helpers import to_discount_out

router = APIRouter(prefix=f"{settings.api_prefix}/discounts", tags=["discounts"])

@router.post("/validate", response_model=DiscountValidateResponse)
def validate_discount(
    payload: DiscountValidateRequest,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> DiscountValidateResponse:
    code = payload.code.strip().upper()
    if not code:
        return DiscountValidateResponse(valid=False, message="Enter a discount code")

    discount = db.scalar(select(DiscountRecord).where(DiscountRecord.code == code))
    if discount is None:
        return DiscountValidateResponse(valid=False, message="Discount code not found")
    if not discount.active:
        return DiscountValidateResponse(valid=False, message="Discount code is no longer active")
    if discount.expires_at and discount.expires_at < datetime.utcnow():
        return DiscountValidateResponse(valid=False, message="Discount code has expired")
    if discount.max_uses is not None and discount.times_used >= discount.max_uses:
        return DiscountValidateResponse(valid=False, message="Discount code has reached its usage limit")

    return DiscountValidateResponse(valid=True, name=discount.name, percent=discount.percent)

@router.get("", response_model=list[DiscountOut])
def list_discounts(db: Session = Depends(get_db), _current_user: AccountRecord = Depends(get_current_user)) -> list[DiscountOut]:
    discounts = db.scalars(select(DiscountRecord).order_by(DiscountRecord.created_at.desc())).all()
    return [to_discount_out(d) for d in discounts]

@router.post("", response_model=DiscountOut, status_code=status.HTTP_201_CREATED)
def create_discount(
    payload: DiscountCreate,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> DiscountOut:
    code = payload.code.strip().upper()
    if db.scalar(select(DiscountRecord).where(DiscountRecord.code == code)):
        raise HTTPException(status_code=409, detail=f"Discount code {code} already exists")

    record = DiscountRecord(
        name=payload.name,
        code=code,
        percent=payload.percent,
        max_uses=payload.maxUses,
        expires_at=payload.expiresAt,
    )
    db.add(record)
    db.flush()
    log_audit_action(db, "created_discount", "Discount", record.id, _current_user.name, f"Created discount {record.code}")
    db.commit()
    db.refresh(record)
    return to_discount_out(record)

@router.patch("/{discount_id}", response_model=DiscountOut)
def update_discount(
    discount_id: int,
    payload: DiscountUpdate,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> DiscountOut:
    record = db.get(DiscountRecord, discount_id)
    if not record:
        raise HTTPException(status_code=404, detail="Discount not found")

    data = payload.model_dump(exclude_unset=True)

    if "code" in data and data["code"] is not None:
        code = data["code"].strip().upper()
        if code != record.code and db.scalar(select(DiscountRecord).where(DiscountRecord.code == code)):
            raise HTTPException(status_code=409, detail=f"Discount code {code} already exists")
        record.code = code

    if "name" in data:
        record.name = data["name"]
    if "percent" in data:
        record.percent = data["percent"]
    if "expiresAt" in data:
        record.expires_at = data["expiresAt"]
    if "maxUses" in data:
        record.max_uses = data["maxUses"]
    if "active" in data:
        record.active = data["active"]

    log_audit_action(db, "updated_discount", "Discount", record.id, _current_user.name, f"Updated discount {record.code}")
    db.commit()
    db.refresh(record)
    return to_discount_out(record)

@router.delete("/{discount_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_discount(
    discount_id: int,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> None:
    record = db.get(DiscountRecord, discount_id)
    if not record:
        raise HTTPException(status_code=404, detail="Discount not found")
    log_audit_action(db, "deleted_discount", "Discount", record.id, _current_user.name, f"Deleted discount {record.code}")
    db.delete(record)
    db.commit()