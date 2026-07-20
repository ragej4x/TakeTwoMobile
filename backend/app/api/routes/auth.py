from datetime import datetime, timedelta
import secrets
from fastapi import APIRouter, Depends, Response, Header, Cookie, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user, SESSION_COOKIE_NAME
from app.models import AccountRecord, SessionRecord, PasswordResetCodeRecord
from app.schemas import (
    LoginRequest, AuthResponse, ProfileData, LogoutResponse,
    PasswordResetRequest, PasswordResetRequestResponse,
    PasswordResetVerifyRequest, PasswordResetVerifyResponse,
    PasswordResetConfirmRequest, PasswordResetConfirmResponse,
)
from app.core.auth import hash_password, verify_password, create_session, set_session_cookie, clear_session_cookie, RESET_CODE_TTL_MINUTES
from app.core.audit import log_audit_action
from app.utils.helpers import to_profile

router = APIRouter(prefix=f"{settings.api_prefix}/auth", tags=["auth"])

@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> AuthResponse:
    email = payload.email.lower()
    account = db.scalar(select(AccountRecord).where(AccountRecord.email == email))
    if account is None or not verify_password(payload.password, account.password_hash):
        log_audit_action(
            db, "failed_login", "Auth",
            account.id if account else email,
            account.name if account else email,
            f"Failed login attempt for {email}",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

    log_audit_action(db, "logged_in", "Auth", account.id, account.name, f"{account.name} logged in")
    session = create_session(db, account.id)
    set_session_cookie(response, session.token)

    return AuthResponse(token=session.token, profile=to_profile(account))

@router.post("/logout", response_model=LogoutResponse)
def logout(
    response: Response,
    authorization: str | None = Header(default=None),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db: Session = Depends(get_db),
) -> LogoutResponse:
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    if not token:
        token = session_token

    if token:
        session = db.scalar(select(SessionRecord).where(SessionRecord.token == token))
        if session is not None:
            account = db.get(AccountRecord, session.user_id)
            log_audit_action(
                db, "logged_out", "Auth", session.user_id,
                account.name if account else "Unknown",
                f"{account.name if account else 'Unknown user'} logged out",
            )
            db.delete(session)
            db.commit()
    clear_session_cookie(response)
    return LogoutResponse(message="Logged out")

@router.get("/session", response_model=ProfileData)
def auth_session(current_user: AccountRecord = Depends(get_current_user)) -> ProfileData:
    return to_profile(current_user)

@router.post("/password-reset/request", response_model=PasswordResetRequestResponse)
def request_password_reset(payload: PasswordResetRequest, db: Session = Depends(get_db)) -> PasswordResetRequestResponse:
    email = payload.email.lower()
    account = db.scalar(select(AccountRecord).where(AccountRecord.email == email))

    if account is not None:
        existing_codes = db.scalars(
            select(PasswordResetCodeRecord).where(
                PasswordResetCodeRecord.email == email,
                PasswordResetCodeRecord.used.is_(False),
            )
        ).all()
        for existing in existing_codes:
            existing.used = True

        code = f"{secrets.randbelow(1000000):06d}"
        expires_at = datetime.utcnow() + timedelta(minutes=RESET_CODE_TTL_MINUTES)
        db.add(PasswordResetCodeRecord(email=email, code=code, expires_at=expires_at, used=False))
        log_audit_action(db, "requested_password_reset", "Auth", account.id, account.name, f"Password reset requested for {email}")
        db.commit()
        print(f"[TakeTwo Reset Code] email={email} code={code} expires_at={expires_at.isoformat()}Z")

    return PasswordResetRequestResponse(
        message="If the account exists, a reset code has been sent.",
        expiresInSeconds=RESET_CODE_TTL_MINUTES * 60,
    )

def get_valid_reset_code(db: Session, email: str, code: str) -> PasswordResetCodeRecord:
    reset_code = db.scalar(
        select(PasswordResetCodeRecord)
        .where(
            PasswordResetCodeRecord.email == email,
            PasswordResetCodeRecord.code == code,
            PasswordResetCodeRecord.used.is_(False),
        )
        .order_by(PasswordResetCodeRecord.created_at.desc())
    )

    if reset_code is None or reset_code.expires_at <= datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset code")
    return reset_code

@router.post("/password-reset/verify", response_model=PasswordResetVerifyResponse)
def verify_password_reset_code(payload: PasswordResetVerifyRequest, db: Session = Depends(get_db)) -> PasswordResetVerifyResponse:
    email = payload.email.lower()
    get_valid_reset_code(db, email, payload.code)
    return PasswordResetVerifyResponse(message="Code verified")

@router.post("/password-reset/confirm", response_model=PasswordResetConfirmResponse)
def confirm_password_reset(payload: PasswordResetConfirmRequest, db: Session = Depends(get_db)) -> PasswordResetConfirmResponse:
    email = payload.email.lower()
    account = db.scalar(select(AccountRecord).where(AccountRecord.email == email))
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    reset_code = get_valid_reset_code(db, email, payload.code)
    account.password_hash = hash_password(payload.newPassword)
    reset_code.used = True

    other_codes = db.scalars(
        select(PasswordResetCodeRecord).where(
            PasswordResetCodeRecord.email == email,
            PasswordResetCodeRecord.used.is_(False),
            PasswordResetCodeRecord.id != reset_code.id,
        )
    ).all()
    for code_entry in other_codes:
        code_entry.used = True

    log_audit_action(db, "reset_password", "Auth", account.id, account.name, f"Password reset completed for {email}")
    db.commit()
    return PasswordResetConfirmResponse(message="Password reset successful")

