from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import QRCode
from app.schemas import QRCodeCheckResponse, QRCodeGenerateRequest, QRCodeOut
from app.utils.helpers import normalize_code
import secrets
import string

router = APIRouter(prefix=f"{settings.api_prefix}/store/qr", tags=["store-qr"])


@router.get("/{code}/check", response_model=QRCodeCheckResponse)
def check_code(code: str, db: Session = Depends(get_db)) -> QRCodeCheckResponse:
    normalized = normalize_code(code)
    if len(normalized) != 8:
        raise HTTPException(status_code=400, detail="Invalid code format.")

    existing = db.query(QRCode).filter(QRCode.code == normalized).first()
    if existing is None:
        raise HTTPException(status_code=404, detail="This code is not registered. Check the sticker and try again.")

    return QRCodeCheckResponse(code=existing.code, is_valid=True, is_used=existing.is_used)


@router.post("/generate", response_model=list[QRCodeOut])
def generate_codes(payload: QRCodeGenerateRequest, db: Session = Depends(get_db)) -> list[QRCode]:
    alphabet = string.ascii_uppercase + string.digits
    created: list[QRCode] = []
    seen_this_batch: set[str] = set()

    while len(created) < payload.count:
        code_str = "".join(secrets.choice(alphabet) for _ in range(8))
        if code_str in seen_this_batch:
            continue
        if db.query(QRCode.id).filter(QRCode.code == code_str).first():
            continue

        seen_this_batch.add(code_str)
        qr = QRCode(code=code_str, branch_id=payload.branch_id)
        db.add(qr)
        created.append(qr)

    db.commit()
    for qr in created:
        db.refresh(qr)
    return created


@router.get("/", response_model=list[QRCodeOut])
def list_qr_codes(db: Session = Depends(get_db)) -> list[QRCode]:
    """List generated QR codes, most recent first."""
    codes = db.query(QRCode).order_by(QRCode.created_at.desc()).all()
    return codes
