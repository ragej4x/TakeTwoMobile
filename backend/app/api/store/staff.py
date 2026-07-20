from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.models import DropoffRequest, DropoffStatusHistory, RequestStatus
from app.schemas import DropoffRequestOut, DropoffRequestReview, DropoffStatusUpdate

router = APIRouter(prefix=f"{settings.api_prefix}/store/staff/dropoff", tags=["store-staff"])


@router.get("/requests", response_model=list[DropoffRequestOut])
def list_requests(
    status: Optional[RequestStatus] = Query(default=None),
    branch_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
) -> list[DropoffRequest]:
    query = db.query(DropoffRequest).options(joinedload(DropoffRequest.qr_code), joinedload(DropoffRequest.customer), joinedload(DropoffRequest.customer_account))
    if status is not None:
        query = query.filter(DropoffRequest.status == status)
    if branch_id is not None:
        query = query.filter(DropoffRequest.branch_id == branch_id)
    return query.order_by(DropoffRequest.submitted_at.desc()).all()


@router.get("/requests/pending", response_model=list[DropoffRequestOut])
def list_pending(db: Session = Depends(get_db)) -> list[DropoffRequest]:
    return (
        db.query(DropoffRequest)
        .options(joinedload(DropoffRequest.qr_code), joinedload(DropoffRequest.customer), joinedload(DropoffRequest.customer_account))
        .filter(DropoffRequest.status == RequestStatus.pending)
        .order_by(DropoffRequest.submitted_at.asc())
        .all()
    )


@router.patch("/requests/{request_id}/review", response_model=DropoffRequestOut)
def review_request(request_id: int, payload: DropoffRequestReview, db: Session = Depends(get_db)) -> DropoffRequest:
    request = db.query(DropoffRequest).filter(DropoffRequest.id == request_id).first()
    if request is None:
        raise HTTPException(status_code=404, detail="Request not found")
    if request.status != RequestStatus.pending:
        raise HTTPException(status_code=409, detail=f"Request is already '{request.status.value}'")

    old_status = request.status
    if payload.approve:
        request.status = RequestStatus.approved
    else:
        request.status = RequestStatus.rejected
        request.rejection_reason = payload.rejection_reason

    request.reviewed_at = datetime.utcnow()
    request.reviewed_by_staff_id = payload.reviewed_by_staff_id

    db.add(
        DropoffStatusHistory(
            request_id=request.id,
            old_status=old_status,
            new_status=request.status,
            changed_by_staff_id=payload.reviewed_by_staff_id,
            note=payload.rejection_reason if not payload.approve else "Approved",
        )
    )
    db.commit()
    db.refresh(request)
    return request


@router.patch("/requests/{request_id}/status", response_model=DropoffRequestOut)
def update_status(request_id: int, payload: DropoffStatusUpdate, db: Session = Depends(get_db)) -> DropoffRequest:
    request = db.query(DropoffRequest).filter(DropoffRequest.id == request_id).first()
    if request is None:
        raise HTTPException(status_code=404, detail="Request not found")

    old_status = request.status
    request.status = payload.status
    if payload.status == RequestStatus.completed:
        request.completed_at = datetime.utcnow()

    db.add(
        DropoffStatusHistory(
            request_id=request.id,
            old_status=old_status,
            new_status=payload.status,
            changed_by_staff_id=payload.changed_by_staff_id,
            note=payload.note,
        )
    )
    db.commit()
    db.refresh(request)
    return request
