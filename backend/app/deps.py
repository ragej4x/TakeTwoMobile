from datetime import datetime

from fastapi import Cookie, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .models import AccountRecord, SessionRecord

SESSION_COOKIE_NAME = "taketwo_session"


def get_current_user(
    authorization: str | None = Header(default=None),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db: Session = Depends(get_db),
) -> AccountRecord:
    # Prefer a Bearer token from the Authorization header. This is what the
    # mobile/web client actually uses now, since it works regardless of
    # cookie/SameSite quirks (WebViews, cross-host dev setups, etc).
    # The session cookie is kept as a fallback for convenience (e.g. Swagger UI).
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    if not token:
        token = session_token

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    session = db.scalar(select(SessionRecord).where(SessionRecord.token == token))
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

    if session.expires_at <= datetime.utcnow():
        db.delete(session)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

    user = db.get(AccountRecord, session.user_id)
    if user is None:
        db.delete(session)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalid")

    return user


def get_optional_current_user(
    authorization: str | None = Header(default=None),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db: Session = Depends(get_db),
) -> AccountRecord | None:
    try:
        return get_current_user(authorization=authorization, session_token=session_token, db=db)
    except HTTPException:
        return None