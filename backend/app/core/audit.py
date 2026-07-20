from sqlalchemy.orm import Session
from app.models import AuditLogRecord

def log_audit_action(
    db: Session,
    action: str,
    entity_type: str,
    entity_id: str | int,
    user_name: str,
    details: str,
) -> None:
    db.add(
        AuditLogRecord(
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            user_name=user_name or "System",
            details=details,
        )
    )