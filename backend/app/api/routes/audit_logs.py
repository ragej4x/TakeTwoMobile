from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_optional_current_user
from app.models import AccountRecord, AuditLogRecord
from app.schemas import AuditLogOut

router = APIRouter(prefix=f"{settings.api_prefix}/audit-logs", tags=["audit-logs"])

@router.get("", response_model=list[AuditLogOut])
def list_audit_logs(
    db: Session = Depends(get_db),
    _current_user: AccountRecord | None = Depends(get_optional_current_user),
) -> list[AuditLogOut]:
    logs = db.scalars(select(AuditLogRecord).order_by(AuditLogRecord.created_at.desc())).all()
    return [
        AuditLogOut(
            id=log.id,
            action=log.action,
            entityType=log.entity_type,
            entityId=log.entity_id,
            userName=log.user_name,
            details=log.details,
            createdAt=log.created_at,
        )
        for log in logs
    ]