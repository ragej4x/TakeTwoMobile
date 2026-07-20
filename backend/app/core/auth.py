import hashlib
import secrets
from datetime import datetime, timedelta
from fastapi import Response
from sqlalchemy.orm import Session
from app.models import SessionRecord
from app.utils.time import now_manila

SESSION_COOKIE_NAME = "taketwo_session"
SESSION_TTL_HOURS = 24
RESET_CODE_TTL_MINUTES = 10

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000).hex()
    return f"{salt}${digest}"

def verify_password(password: str, password_hash: str) -> bool:
    try:
        salt, stored_digest = password_hash.split("$", 1)
    except ValueError:
        return False
    candidate_digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000).hex()
    return secrets.compare_digest(candidate_digest, stored_digest)

def create_session(db: Session, user_id: int) -> SessionRecord:
    token = secrets.token_urlsafe(32)
    expires_at = now_manila() + timedelta(hours=SESSION_TTL_HOURS)
    session = SessionRecord(token=token, user_id=user_id, expires_at=expires_at)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=SESSION_TTL_HOURS * 3600,
        path="/",
    )

def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")