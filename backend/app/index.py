from datetime import datetime, timedelta
import hashlib
import secrets

from fastapi import Cookie, Depends, FastAPI, Header, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from .ai import router as ai_router
from .config import settings
from .database import Base, engine, get_db
from .deps import get_current_user
from .models import (
    AccountRecord,
    DiscountRecord,
    JobRecord,
    PasswordResetCodeRecord,
    ProfileRecord,
    SessionRecord,
    SettingsRecord,
)
from .schemas import (
    AuthResponse,
    BinSummary,
    DiscountCreate,
    DiscountOut,
    DiscountValidateRequest,
    DiscountValidateResponse,
    JobCreate,
    JobOut,
    JobStatusUpdate,
    JobUpdate,
    LoginRequest,
    LogoutResponse,
    PasswordResetConfirmRequest,
    PasswordResetConfirmResponse,
    PasswordResetRequest,
    PasswordResetRequestResponse,
    PasswordResetVerifyRequest,
    PasswordResetVerifyResponse,
    ProfileData,
    SettingsData,
)

ALL_BINS = ["A-01", "A-02", "A-03", "B-01", "B-02", "B-03", "B-04", "C-01", "C-02"]
SESSION_COOKIE_NAME = "taketwo_session"
SESSION_TTL_HOURS = 24
RESET_CODE_TTL_MINUTES = 10

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ai_router, prefix=settings.api_prefix)


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
    expires_at = datetime.utcnow() + timedelta(hours=SESSION_TTL_HOURS)
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


def to_profile(account: AccountRecord) -> ProfileData:
    return ProfileData(
        name=account.name,
        phone=account.phone,
        email=account.email,
        role=account.role,
        branch=account.branch,
        photoUrl=account.photo_url, 
    )


def to_discount_out(discount: DiscountRecord) -> DiscountOut:
    return DiscountOut(
        id=discount.id,
        name=discount.name,
        code=discount.code,
        percent=discount.percent,
        maxUses=discount.max_uses,
        timesUsed=discount.times_used,
        expiresAt=discount.expires_at,
        active=discount.active,
    )


def to_job_out(job: JobRecord) -> JobOut:
    return JobOut(
        id=job.id,
        customer=job.customer,
        phone=job.phone,
        email=job.email,
        dateReceived=job.date_received,
        expectedRelease=job.expected_release,
        shoes=job.shoes or [],
        bin=job.bin,
        status=job.status,
        receiveUpdates=job.receive_updates,
        totalPayment=job.total_payment,
        notes=job.notes,
        assignedTo=job.assigned_to,
        branch=job.branch,
        released=job.released,
        signatureDataUrl=job.signature_data_url,
        discountCode=job.discount_code,
        discountName=job.discount_name,
        discountPercent=job.discount_percent,
        discountAmount=job.discount_amount,
        createdAt=job.created_at,
        updatedAt=job.updated_at,
    )


def apply_job_update(record: JobRecord, payload: JobUpdate | JobCreate) -> None:
    record.customer = payload.customer
    record.phone = payload.phone
    record.email = payload.email
    record.date_received = payload.dateReceived
    record.expected_release = payload.expectedRelease
    record.shoes = [shoe.model_dump() for shoe in payload.shoes]
    record.bin = payload.bin
    record.status = payload.status
    record.receive_updates = payload.receiveUpdates
    record.total_payment = payload.totalPayment
    record.notes = payload.notes
    record.assigned_to = payload.assignedTo
    record.branch = payload.branch
    record.released = payload.released
    record.signature_data_url = payload.signatureDataUrl
    record.discount_code = payload.discountCode
    record.discount_name = payload.discountName
    record.discount_percent = payload.discountPercent
    record.discount_amount = payload.discountAmount


def consume_discount_code(db: Session, code: str | None) -> None:
    """Re-validates a discount code server-side and counts one use against
    it. Called when a job order that references the code is created, so a
    code that expired or hit its limit between the customer-facing check and
    submission doesn't silently slip through."""
    if not code:
        return
    normalized = code.strip().upper()
    discount = db.scalar(select(DiscountRecord).where(DiscountRecord.code == normalized))
    if discount is None:
        raise HTTPException(status_code=400, detail=f"Discount code {normalized} not found")
    if not discount.active:
        raise HTTPException(status_code=400, detail="Discount code is no longer active")
    if discount.expires_at and discount.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Discount code has expired")
    if discount.max_uses is not None and discount.times_used >= discount.max_uses:
        raise HTTPException(status_code=400, detail="Discount code has reached its usage limit")
    discount.times_used += 1


def generate_job_id(db: Session) -> str:
    date_str = datetime.utcnow().strftime("%Y%m%d")
    prefix = f"TK-{date_str}-"
    count_stmt = select(JobRecord.id).where(JobRecord.id.startswith(prefix))
    today_ids = db.scalars(count_stmt).all()
    sequence = len(today_ids) + 1
    return f"{prefix}{sequence:03d}"



@app.get(f"{settings.api_prefix}/health")
def health_check() -> dict:
    return {"status": "ok", "service": settings.app_name}


@app.post(f"{settings.api_prefix}/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> AuthResponse:
    account = db.scalar(select(AccountRecord).where(AccountRecord.email == payload.email.lower()))
    if account is None or not verify_password(payload.password, account.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

    session = create_session(db, account.id)
    set_session_cookie(response, session.token)

    return AuthResponse(token=session.token, profile=to_profile(account))


@app.post(f"{settings.api_prefix}/auth/logout", response_model=LogoutResponse)
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
            db.delete(session)
            db.commit()
    clear_session_cookie(response)
    return LogoutResponse(message="Logged out")


@app.get(f"{settings.api_prefix}/auth/session", response_model=ProfileData)
def auth_session(current_user: AccountRecord = Depends(get_current_user)) -> ProfileData:
    return to_profile(current_user)


@app.post(f"{settings.api_prefix}/auth/password-reset/request", response_model=PasswordResetRequestResponse)
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
        db.add(
            PasswordResetCodeRecord(
                email=email,
                code=code,
                expires_at=expires_at,
                used=False,
            )
        )
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


@app.post(f"{settings.api_prefix}/auth/password-reset/verify", response_model=PasswordResetVerifyResponse)
def verify_password_reset_code(payload: PasswordResetVerifyRequest, db: Session = Depends(get_db)) -> PasswordResetVerifyResponse:
    email = payload.email.lower()
    get_valid_reset_code(db, email, payload.code)
    return PasswordResetVerifyResponse(message="Code verified")


@app.post(f"{settings.api_prefix}/auth/password-reset/confirm", response_model=PasswordResetConfirmResponse)
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

    db.commit()
    return PasswordResetConfirmResponse(message="Password reset successful")




@app.get(f"{settings.api_prefix}/profile", response_model=ProfileData)
def get_profile(current_user: AccountRecord = Depends(get_current_user)) -> ProfileData:
    return to_profile(current_user)


@app.put(f"{settings.api_prefix}/profile", response_model=ProfileData)
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
    db.commit()
    db.refresh(current_user)
    return to_profile(current_user)


@app.get(f"{settings.api_prefix}/settings", response_model=SettingsData)
def get_settings(
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> SettingsData:
    app_settings = db.get(SettingsRecord, 1)
    if app_settings is None:
        raise HTTPException(status_code=404, detail="Settings not found")

    return SettingsData(
        connStatus=app_settings.conn_status,
        theme=app_settings.theme,
        branch=app_settings.branch,
        selectedPrinter=app_settings.selected_printer,
    )


@app.put(f"{settings.api_prefix}/settings", response_model=SettingsData)
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
    db.commit()
    db.refresh(app_settings)
    return payload


@app.get(f"{settings.api_prefix}/jobs", response_model=list[JobOut])
def list_jobs(
    q: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    released: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> list[JobOut]:
    jobs = db.scalars(select(JobRecord).order_by(JobRecord.created_at.desc())).all()

    if q:
        query = q.lower()
        jobs = [
            job
            for job in jobs
            if query in job.id.lower()
            or query in job.customer.lower()
            or query in (job.bin or "").lower()
            or any(query in (shoe.get("itemId", "").lower()) for shoe in (job.shoes or []))
        ]

    if status_filter:
        jobs = [job for job in jobs if job.status == status_filter]

    if released is not None:
        jobs = [job for job in jobs if job.released is released]

    return [to_job_out(job) for job in jobs]


@app.post(f"{settings.api_prefix}/jobs", response_model=JobOut, status_code=status.HTTP_201_CREATED)
def create_job(
    payload: JobCreate,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> JobOut:
    job_id = payload.id or generate_job_id(db)
    if db.get(JobRecord, job_id):
        raise HTTPException(status_code=409, detail=f"Job {job_id} already exists")

    record = JobRecord(id=job_id, customer=payload.customer, date_received=payload.dateReceived, status=payload.status)
    apply_job_update(record, payload)
    consume_discount_code(db, payload.discountCode)
    db.add(record)
    db.commit()
    db.refresh(record)
    return to_job_out(record)


@app.get(f"{settings.api_prefix}/jobs/{{job_id}}", response_model=JobOut)
def get_job(
    job_id: str,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> JobOut:
    record = db.get(JobRecord, job_id)
    if not record:
        raise HTTPException(status_code=404, detail="Job not found")
    return to_job_out(record)


@app.put(f"{settings.api_prefix}/jobs/{{job_id}}", response_model=JobOut)
def update_job(
    job_id: str,
    payload: JobUpdate,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> JobOut:
    record = db.get(JobRecord, job_id)
    if not record:
        raise HTTPException(status_code=404, detail="Job not found")
    apply_job_update(record, payload)
    db.commit()
    db.refresh(record)
    return to_job_out(record)


@app.patch(f"{settings.api_prefix}/jobs/{{job_id}}/status", response_model=JobOut)
def update_job_status(
    job_id: str,
    payload: JobStatusUpdate,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> JobOut:
    record = db.get(JobRecord, job_id)
    if not record:
        raise HTTPException(status_code=404, detail="Job not found")
    record.status = payload.status
    db.commit()
    db.refresh(record)
    return to_job_out(record)


@app.patch(f"{settings.api_prefix}/jobs/{{job_id}}/release", response_model=JobOut)
def mark_job_released(
    job_id: str,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> JobOut:
    record = db.get(JobRecord, job_id)
    if not record:
        raise HTTPException(status_code=404, detail="Job not found")
    record.released = True
    record.bin = ""
    db.commit()
    db.refresh(record)
    return to_job_out(record)


@app.delete(f"{settings.api_prefix}/jobs/{{job_id}}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: str,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> None:
    record = db.get(JobRecord, job_id)
    if not record:
        raise HTTPException(status_code=404, detail="Job not found")
    db.delete(record)
    db.commit()


@app.post(f"{settings.api_prefix}/discounts/validate", response_model=DiscountValidateResponse)
def validate_discount(
    payload: DiscountValidateRequest,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> DiscountValidateResponse:
    """Read-only check — does NOT consume a use. Safe to call as the
    customer/staff types the code in during order creation."""
    code = payload.code.strip().upper()
    if not code:
        return DiscountValidateResponse(valid=False, message="Enter a discount code")

    discount = db.scalar(select(DiscountRecord).where(DiscountRecord.code == code))
    if discount is None:
        return DiscountValidateResponse(valid=False, message="Discount code not found")
    if not discount.active:
        return DiscountValidateResponse(valid=False, message="Discount code is no longer active")
    if discount.expires_at and discount.expires_at < datetime.utcnow():
        return DiscountValidateResponse(valid=False, message="Discount code has expired")
    if discount.max_uses is not None and discount.times_used >= discount.max_uses:
        return DiscountValidateResponse(valid=False, message="Discount code has reached its usage limit")

    return DiscountValidateResponse(valid=True, name=discount.name, percent=discount.percent)


@app.get(f"{settings.api_prefix}/discounts", response_model=list[DiscountOut])
def list_discounts(
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> list[DiscountOut]:
    discounts = db.scalars(select(DiscountRecord).order_by(DiscountRecord.created_at.desc())).all()
    return [to_discount_out(d) for d in discounts]


@app.post(f"{settings.api_prefix}/discounts", response_model=DiscountOut, status_code=status.HTTP_201_CREATED)
def create_discount(
    payload: DiscountCreate,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> DiscountOut:
    code = payload.code.strip().upper()
    if db.scalar(select(DiscountRecord).where(DiscountRecord.code == code)):
        raise HTTPException(status_code=409, detail=f"Discount code {code} already exists")

    record = DiscountRecord(
        name=payload.name,
        code=code,
        percent=payload.percent,
        max_uses=payload.maxUses,
        expires_at=payload.expiresAt,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return to_discount_out(record)


@app.delete(f"{settings.api_prefix}/discounts/{{discount_id}}", status_code=status.HTTP_204_NO_CONTENT)
def delete_discount(
    discount_id: int,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> None:
    record = db.get(DiscountRecord, discount_id)
    if not record:
        raise HTTPException(status_code=404, detail="Discount not found")
    db.delete(record)
    db.commit()


@app.get(f"{settings.api_prefix}/bins", response_model=list[BinSummary])
def get_bins(
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> list[BinSummary]:
    active_jobs = db.scalars(select(JobRecord).where(JobRecord.released.is_(False))).all()
    bins: dict[str, list[JobRecord]] = {name: [] for name in ALL_BINS}

    for job in active_jobs:
        if job.bin in bins:
            bins[job.bin].append(job)

    summaries: list[BinSummary] = []
    for bin_name in ALL_BINS:
        jobs_in_bin = bins[bin_name]
        summaries.append(
            BinSummary(
                bin=bin_name,
                occupied=len(jobs_in_bin) > 0,
                orderCount=len(jobs_in_bin),
                pairCount=sum(len(job.shoes or []) for job in jobs_in_bin),
                jobs=[job.id for job in jobs_in_bin],
            )
        )

    return summaries