from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import AccountRecord
from app.schemas import ProfileData
from app.core.audit import log_audit_action
from app.utils.helpers import to_profile

router = APIRouter(prefix=f"{settings.api_prefix}/profile", tags=["profile"])

@router.get("", response_model=ProfileData)
def get_profile(current_user: AccountRecord = Depends(get_current_user)) -> ProfileData:
    return to_profile(current_user)

@router.put("", response_model=ProfileData)
def update_profile(
    payload: ProfileData,
    db: Session = Depends(get_db),
    current_user: AccountRecord = Depends(get_current_user),
) -> ProfileData:
    current_user.name = payload.name
    current_user.phone = payload.phone
    current_user.email = payload.email.lower()
    current_user.role = payload.role
    current_user.branch = payload.branch
    current_user.photo_url = payload.photoUrl
    log_audit_action(db, "updated_profile", "Profile", current_user.id, current_user.name, "Updated profile information")
    db.commit()
    db.refresh(current_user)
    return to_profile(current_user)