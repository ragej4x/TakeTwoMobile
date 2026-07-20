from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import AccountRecord, SettingsRecord
from app.schemas import SettingsData
from app.core.audit import log_audit_action

router = APIRouter(prefix=f"{settings.api_prefix}/settings", tags=["settings"])

@router.get("", response_model=SettingsData)
def get_settings(db: Session = Depends(get_db), _current_user: AccountRecord = Depends(get_current_user)) -> SettingsData:
    app_settings = db.get(SettingsRecord, 1)
    if app_settings is None:
        raise HTTPException(status_code=404, detail="Settings not found")

    return SettingsData(
        connStatus=app_settings.conn_status,
        theme=app_settings.theme,
        branch=app_settings.branch,
        selectedPrinter=app_settings.selected_printer,
    )

@router.put("", response_model=SettingsData)
def update_settings(
    payload: SettingsData,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> SettingsData:
    app_settings = db.get(SettingsRecord, 1)
    if app_settings is None:
        raise HTTPException(status_code=404, detail="Settings not found")

    app_settings.conn_status = payload.connStatus
    app_settings.theme = payload.theme
    app_settings.branch = payload.branch
    app_settings.selected_printer = payload.selectedPrinter
    log_audit_action(db, "updated_settings", "Settings", app_settings.id, _current_user.name, "Updated application settings")
    db.commit()
    db.refresh(app_settings)
    return payload