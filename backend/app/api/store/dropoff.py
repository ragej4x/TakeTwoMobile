from datetime import datetime
from uuid import uuid4

from app.utils.time import now_manila

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel

from app import models
from app.database import get_db
from app.models import DropoffRequest, DropoffStatusHistory, QRCode, RequestStatus, JobRecord
from app.schemas import DropoffRequestCreate, DropoffRequestOut
from app.utils.helpers import normalize_code
from app.config import settings


router = APIRouter(prefix=f"{settings.api_prefix}/store/dropoff", tags=["store-dropoff"])


@router.get("/requests", response_model=list[DropoffRequestOut])
def list_dropoff_requests(
    status: RequestStatus | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[DropoffRequest]:
    """List drop-off requests, ordered by most recent first.

    Previously this endpoint accepted no `status` param at all — callers like
    the mobile app's `?status=pending` were silently ignored and got every
    request back regardless of state. Now it actually filters when given one.
    """
    query = db.query(DropoffRequest).options(
        joinedload(DropoffRequest.qr_code),
        joinedload(DropoffRequest.customer),
        joinedload(DropoffRequest.customer_account),
    )
    if status is not None:
        query = query.filter(DropoffRequest.status == status)
    return query.order_by(DropoffRequest.submitted_at.desc()).all()


@router.post("/requests", response_model=DropoffRequestOut, status_code=201)

def create_dropoff_request(payload: DropoffRequestCreate, db: Session = Depends(get_db)) -> DropoffRequest:
    code = normalize_code(payload.code)
    if len(code) != 8:
        raise HTTPException(status_code=400, detail="Invalid code format.")

    qr_code = db.query(QRCode).filter(QRCode.code == code).first()
    if qr_code is None:
        raise HTTPException(status_code=404, detail="This code is not registered.")
    if qr_code.is_used:
        raise HTTPException(status_code=409, detail="This code has already been used for a drop-off.")

    customer = (
        db.query(models.Customer)
        .filter(models.Customer.phone_number == payload.customer.phone_number)
        .first()
    )
    if customer is None:
        customer = models.Customer(**payload.customer.model_dump())
        db.add(customer)
        db.flush()

    customer_account = None
    if payload.customer.email:
        customer_account = (
            db.query(models.CustomerAccount)
            .filter(models.CustomerAccount.email == payload.customer.email)
            .first()
        )

    request = DropoffRequest(
        qr_code_id=qr_code.id,
        customer_id=customer.id,
        customer_account_id=customer_account.id if customer_account else None,
        shoe_brand=payload.shoe_brand,
        shoe_model=payload.shoe_model,
        shoe_color=payload.shoe_color,
        service_type=payload.service_type,
        special_instructions=payload.special_instructions,
        photo_urls=payload.photo_urls,
        price_list=payload.price_list,
        discounts=payload.discounts,
        number_of_pairs=payload.number_of_pairs,
        bin=payload.bin,
        sponsored=payload.sponsored,
        status=RequestStatus.pending,
    )
    db.add(request)

    qr_code.is_used = True
    qr_code.used_at = now_manila()

    db.commit()
    db.refresh(request)

    db.add(DropoffStatusHistory(request_id=request.id, old_status=None, new_status=RequestStatus.pending, note="Customer submitted drop-off request"))
    db.commit()

    return (
        db.query(DropoffRequest)
        .options(joinedload(DropoffRequest.qr_code), joinedload(DropoffRequest.customer), joinedload(DropoffRequest.customer_account))
        .filter(DropoffRequest.id == request.id)
        .first()
    )


@router.get("/requests/{request_id}", response_model=DropoffRequestOut)
def get_dropoff_request(request_id: int, db: Session = Depends(get_db)) -> DropoffRequest:
    request = (
        db.query(DropoffRequest)
        .options(joinedload(DropoffRequest.qr_code), joinedload(DropoffRequest.customer), joinedload(DropoffRequest.customer_account))
        .filter(DropoffRequest.id == request_id)
        .first()
    )
    if request is None:
        raise HTTPException(status_code=404, detail="Request not found")
    return request


class ApproveDropoffRequest(BaseModel):
    price_list: str | None = None
    discounts: str | None = None
    number_of_pairs: int | None = None
    bin: str | None = None
    sponsored: bool | None = None


@router.post("/requests/{request_id}/approve", response_model=DropoffRequestOut)
def approve_dropoff_request(
    request_id: int,
    payload: ApproveDropoffRequest,
    db: Session = Depends(get_db),
) -> DropoffRequest:
    """Approve a drop-off request and create a corresponding job."""
    request = db.query(DropoffRequest).filter(DropoffRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    if request.status != RequestStatus.pending:
        raise HTTPException(status_code=400, detail=f"Cannot approve a {request.status} request")

    # Update dropoff request with any edited details
    if payload.price_list is not None:
        request.price_list = payload.price_list
    if payload.discounts is not None:
        request.discounts = payload.discounts
    if payload.number_of_pairs is not None:
        request.number_of_pairs = payload.number_of_pairs
    if payload.bin is not None:
        request.bin = payload.bin
    if payload.sponsored is not None:
        request.sponsored = payload.sponsored
    request.status = RequestStatus.approved
    request.reviewed_at = datetime.utcnow()

    # Record status history
    db.add(
        DropoffStatusHistory(
            request_id=request.id,
            old_status=RequestStatus.pending,
            new_status=RequestStatus.approved,
            note="Approved for mobile processing",
        )
    )

    db.commit()
    db.refresh(request)

    return (
        db.query(DropoffRequest)
        .options(joinedload(DropoffRequest.qr_code), joinedload(DropoffRequest.customer), joinedload(DropoffRequest.customer_account))
        .filter(DropoffRequest.id == request.id)
        .first()
    )


class RejectDropoffRequest(BaseModel):
    rejection_reason: str | None = None


@router.post("/requests/{request_id}/reject")
def reject_dropoff_request(
    request_id: int,
    payload: RejectDropoffRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Reject a drop-off request."""
    request = db.query(DropoffRequest).filter(DropoffRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    if request.status != RequestStatus.pending:
        raise HTTPException(status_code=400, detail=f"Cannot reject a {request.status} request")

    request.status = RequestStatus.rejected
    request.rejection_reason = payload.rejection_reason or "Rejected by staff"
    request.reviewed_at = datetime.utcnow()

    db.add(
        DropoffStatusHistory(
            request_id=request.id,
            old_status=RequestStatus.pending,
            new_status=RequestStatus.rejected,
            note=payload.rejection_reason or "Rejected by staff",
        )
    )

    db.commit()

    return {"message": "Drop-off request rejected"}


class LinkJobRequest(BaseModel):
    job_id: str


@router.post("/requests/{request_id}/link-job", response_model=DropoffRequestOut)
def link_job_to_dropoff_request(
    request_id: int,
    payload: LinkJobRequest,
    db: Session = Depends(get_db),
) -> DropoffRequest:
    """Record that a job order was created from this (approved) request.

    Called by the frontend right after `createJob` succeeds for a request
    that came from StoreApprovalsPage's "Create Job" button. Persisting this
    is what lets an approved-but-not-yet-jobbed request survive a page
    reload — without it, the frontend has no durable way to distinguish
    "approved, still needs a job" from "approved, job already made", and
    ends up re-offering the approve/reject actions for an already-approved
    request (which the backend correctly rejects, but the frontend has no
    good recovery for that case if it can't tell the two apart).
    """
    request = db.query(DropoffRequest).filter(DropoffRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    if request.status != RequestStatus.approved:
        raise HTTPException(status_code=400, detail=f"Cannot link a job to a {request.status} request")

    request.job_id = payload.job_id
    db.commit()
    db.refresh(request)

    return (
        db.query(DropoffRequest)
        .options(joinedload(DropoffRequest.qr_code), joinedload(DropoffRequest.customer), joinedload(DropoffRequest.customer_account))
        .filter(DropoffRequest.id == request.id)
        .first()
    )