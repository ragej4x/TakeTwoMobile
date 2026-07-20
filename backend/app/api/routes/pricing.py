from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import AccountRecord, PricingRecord
from app.schemas import PricingCreate, PricingUpdate, PricingOut
from app.core.audit import log_audit_action
from app.utils.helpers import to_pricing_out

router = APIRouter(prefix=f"{settings.api_prefix}/pricing", tags=["pricing"])

@router.get("/public", response_model=list[PricingOut])
def list_public_pricing(
    category: str | None = Query(default=None, description="Filter by category"),
    is_active: bool | None = Query(default=None, description="Filter by active status"),
    search: str | None = Query(default=None, description="Search in name and description"),
    db: Session = Depends(get_db),
) -> list[PricingOut]:
    query = select(PricingRecord)
    
    if category:
        query = query.where(PricingRecord.category == category)
    if is_active is not None:
        query = query.where(PricingRecord.is_active == is_active)
    if search:
        search_term = f"%{search}%"
        query = query.where(
            (PricingRecord.name.ilike(search_term)) | 
            (PricingRecord.description.ilike(search_term))
        )
    
    pricing_items = db.scalars(query.order_by(PricingRecord.created_at.desc())).all()
    return [to_pricing_out(item) for item in pricing_items]

@router.get("", response_model=list[PricingOut])
def list_pricing(
    category: str | None = Query(default=None, description="Filter by category"),
    is_active: bool | None = Query(default=None, description="Filter by active status"),
    search: str | None = Query(default=None, description="Search in name and description"),
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> list[PricingOut]:
    query = select(PricingRecord)
    
    if category:
        query = query.where(PricingRecord.category == category)
    if is_active is not None:
        query = query.where(PricingRecord.is_active == is_active)
    if search:
        search_term = f"%{search}%"
        query = query.where(
            (PricingRecord.name.ilike(search_term)) | 
            (PricingRecord.description.ilike(search_term))
        )
    
    pricing_items = db.scalars(query.order_by(PricingRecord.created_at.desc())).all()
    return [to_pricing_out(item) for item in pricing_items]

@router.get("/categories", response_model=list[str])
def list_pricing_categories(
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> list[str]:
    categories = db.scalars(
        select(PricingRecord.category)
        .distinct()
        .where(PricingRecord.category.isnot(None))
        .order_by(PricingRecord.category)
    ).all()
    return [cat for cat in categories if cat and cat.strip()]

@router.post("", response_model=PricingOut, status_code=status.HTTP_201_CREATED)
def create_pricing(
    payload: PricingCreate,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> PricingOut:
    existing = db.scalar(select(PricingRecord).where(PricingRecord.name == payload.name))
    if existing:
        raise HTTPException(status_code=409, detail=f"Pricing item with name '{payload.name}' already exists")
    
    record = PricingRecord(
        name=payload.name,
        description=payload.description,
        price=payload.price,
        category=payload.category,
        duration_days=payload.duration_days,
        is_active=payload.is_active,
    )
    db.add(record)
    db.flush()
    log_audit_action(db, "created_pricing", "Pricing", record.id, _current_user.name, f"Created pricing item {record.name}")
    db.commit()
    db.refresh(record)
    return to_pricing_out(record)

@router.get("/{pricing_id}", response_model=PricingOut)
def get_pricing(
    pricing_id: int,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> PricingOut:
    record = db.get(PricingRecord, pricing_id)
    if not record:
        raise HTTPException(status_code=404, detail="Pricing item not found")
    return to_pricing_out(record)

@router.put("/{pricing_id}", response_model=PricingOut)
def update_pricing(
    pricing_id: int,
    payload: PricingUpdate,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> PricingOut:
    record = db.get(PricingRecord, pricing_id)
    if not record:
        raise HTTPException(status_code=404, detail="Pricing item not found")
    
    if payload.name is not None and payload.name != record.name:
        existing = db.scalar(select(PricingRecord).where(PricingRecord.name == payload.name))
        if existing:
            raise HTTPException(status_code=409, detail=f"Pricing item with name '{payload.name}' already exists")
        record.name = payload.name
    
    if payload.description is not None:
        record.description = payload.description
    if payload.price is not None:
        record.price = payload.price
    if payload.category is not None:
        record.category = payload.category
    if payload.duration_days is not None:
        record.duration_days = payload.duration_days
    if payload.is_active is not None:
        record.is_active = payload.is_active
    
    record.updated_at = datetime.utcnow()
    log_audit_action(db, "updated_pricing", "Pricing", record.id, _current_user.name, f"Updated pricing item {record.name}")
    db.commit()
    db.refresh(record)
    return to_pricing_out(record)

@router.patch("/{pricing_id}/toggle", response_model=PricingOut)
def toggle_pricing_active(
    pricing_id: int,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> PricingOut:
    record = db.get(PricingRecord, pricing_id)
    if not record:
        raise HTTPException(status_code=404, detail="Pricing item not found")
    
    record.is_active = not record.is_active
    record.updated_at = datetime.utcnow()
    log_audit_action(db, "toggled_pricing", "Pricing", record.id, _current_user.name, f"Toggled pricing item {record.name}")
    db.commit()
    db.refresh(record)
    return to_pricing_out(record)

@router.delete("/{pricing_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pricing(
    pricing_id: int,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> None:
    record = db.get(PricingRecord, pricing_id)
    if not record:
        raise HTTPException(status_code=404, detail="Pricing item not found")
    
    log_audit_action(db, "deleted_pricing", "Pricing", record.id, _current_user.name, f"Deleted pricing item {record.name}")
    db.delete(record)
    db.commit()

@router.post("/bulk", response_model=list[PricingOut], status_code=status.HTTP_201_CREATED)
def bulk_create_pricing(
    items: list[PricingCreate],
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> list[PricingOut]:
    created_items = []
    errors = []
    
    for idx, item in enumerate(items):
        existing = db.scalar(select(PricingRecord).where(PricingRecord.name == item.name))
        if existing:
            errors.append(f"Item '{item.name}' already exists (index {idx})")
            continue
            
        record = PricingRecord(
            name=item.name,
            description=item.description,
            price=item.price,
            category=item.category,
            duration_days=item.duration_days,
            is_active=item.is_active,
        )
        db.add(record)
        created_items.append(record)
    
    if not created_items and errors:
        raise HTTPException(status_code=400, detail=f"No items created: {', '.join(errors)}")

    db.flush()
    for item in created_items:
        log_audit_action(db, "created_pricing", "Pricing", item.id, _current_user.name, f"Created pricing item {item.name} (bulk)")

    db.commit()
    for item in created_items:
        db.refresh(item)
    
    return [to_pricing_out(item) for item in created_items]