from datetime import datetime, timedelta
import hashlib
import secrets

from fastapi import Cookie, Depends, FastAPI, Header, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .ai import router as ai_router
from .config import settings
from .database import Base, engine, get_db
from .deps import get_current_user
from .models import (
    AccountRecord,
    AuditLogRecord,
    BinRecord,
    BranchRecord,
    DiscountRecord,
    JobRecord,
    PasswordResetCodeRecord,
    ProfileRecord,
    SessionRecord,
    SettingsRecord,
    PricingRecord
)
from .schemas import (
    AuditLogOut,
    AuthResponse,
    BinCreate,
    BinOut,
    BinSummary,
    BinUpdate,
    BranchCreate,
    BranchOut,
    BranchUpdate,
    DiscountCreate,
    DiscountOut,
    DiscountUpdate,
    DiscountValidateRequest,
    DiscountValidateResponse,
    EmployeeCreate,
    EmployeeOut,
    EmployeeUpdate,
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
    PricingCreate,  
    PricingOut,
    PricingUpdate,
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


def employee_job_stats(db: Session, name: str) -> tuple[int, float]:
    released_jobs = db.scalars(
        select(JobRecord).where(JobRecord.assigned_to == name, JobRecord.released.is_(True))
    ).all()
    return len(released_jobs), sum(job.total_payment for job in released_jobs)


def to_employee_out(account: AccountRecord, db: Session) -> EmployeeOut:
    jobs_completed, revenue = employee_job_stats(db, account.name)
    return EmployeeOut(
        id=account.id,
        name=account.name,
        email=account.email,
        phone=account.phone,
        role=account.role,
        branch=account.branch,
        photoUrl=account.photo_url,
        joinDate=account.created_at,
        jobsCompleted=jobs_completed,
        revenue=revenue,
        status="Active",
    )


def to_branch_out(branch: BranchRecord) -> BranchOut:
    return BranchOut(
        id=branch.id,
        name=branch.name,
        code=branch.code,
        address=branch.address,
        manager=branch.manager,
        active=branch.active,
        createdAt=branch.created_at,
        updatedAt=branch.updated_at,
    )


def to_bin_out(bin_record: BinRecord, db: Session) -> BinOut:
    active_jobs = db.scalars(
        select(JobRecord).where(JobRecord.bin == bin_record.name, JobRecord.released.is_(False))
    ).all()
    occupied_count = sum(len(job.shoes or []) for job in active_jobs)
    available_count = max(bin_record.capacity - occupied_count - bin_record.reserved, 0)
    return BinOut(
        id=bin_record.id,
        name=bin_record.name,
        branch=bin_record.branch,
        capacity=bin_record.capacity,
        reserved=bin_record.reserved,
        active=bin_record.active,
        occupiedCount=occupied_count,
        availableCount=available_count,
        createdAt=bin_record.created_at,
        updatedAt=bin_record.updated_at,
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


@app.get(f"{settings.api_prefix}/health")
def health_check() -> dict:
    return {"status": "ok", "service": settings.app_name}


@app.post(f"{settings.api_prefix}/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> AuthResponse:
    email = payload.email.lower()
    account = db.scalar(select(AccountRecord).where(AccountRecord.email == email))
    if account is None or not verify_password(payload.password, account.password_hash):
        log_audit_action(
            db,
            "failed_login",
            "Auth",
            account.id if account else email,
            account.name if account else email,
            f"Failed login attempt for {email}",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

    log_audit_action(
        db,
        "logged_in",
        "Auth",
        account.id,
        account.name,
        f"{account.name} logged in",
    )
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
            account = db.get(AccountRecord, session.user_id)
            log_audit_action(
                db,
                "logged_out",
                "Auth",
                session.user_id,
                account.name if account else "Unknown",
                f"{account.name if account else 'Unknown user'} logged out",
            )
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
        log_audit_action(
            db,
            "requested_password_reset",
            "Auth",
            account.id,
            account.name,
            f"Password reset requested for {email}",
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

    log_audit_action(
        db,
        "reset_password",
        "Auth",
        account.id,
        account.name,
        f"Password reset completed for {email}",
    )
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
    log_audit_action(
        db,
        "updated_profile",
        "Profile",
        current_user.id,
        current_user.name,
        "Updated profile information",
    )
    db.commit()
    db.refresh(current_user)
    return to_profile(current_user)


@app.get(f"{settings.api_prefix}/employees", response_model=list[EmployeeOut])
def list_employees(
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> list[EmployeeOut]:
    accounts = db.scalars(select(AccountRecord).order_by(AccountRecord.created_at.desc())).all()
    return [to_employee_out(account, db) for account in accounts]


@app.post(f"{settings.api_prefix}/employees", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: EmployeeCreate,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> EmployeeOut:
    email = payload.email.lower()
    if db.scalar(select(AccountRecord).where(AccountRecord.email == email)):
        raise HTTPException(status_code=409, detail=f"Account with email {email} already exists")

    try:
        record = AccountRecord(
            email=email,
            password_hash=hash_password(payload.password),
            name=payload.name,
            phone=payload.phone,
            role=payload.role,
            branch=payload.branch,
        )
        db.add(record)
        db.flush()
        log_audit_action(
            db,
            "created_employee",
            "Employee",
            record.id,
            payload.name,
            f"Created employee account {payload.name}",
        )
        db.commit()
        db.refresh(record)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="Unable to create employee. The provided details may already exist.") from exc

    return to_employee_out(record, db)


@app.put(f"{settings.api_prefix}/employees/{{employee_id}}", response_model=EmployeeOut)
def update_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> EmployeeOut:
    record = db.get(AccountRecord, employee_id)
    if not record:
        raise HTTPException(status_code=404, detail="Employee not found")

    if payload.name is not None:
        record.name = payload.name
    if payload.phone is not None:
        record.phone = payload.phone
    if payload.role is not None:
        record.role = payload.role
    if payload.branch is not None:
        record.branch = payload.branch
    if payload.password:
        record.password_hash = hash_password(payload.password)

    log_audit_action(
        db,
        "updated_employee",
        "Employee",
        record.id,
        _current_user.name,
        f"Updated employee {record.name}",
    )
    db.commit()
    db.refresh(record)
    return to_employee_out(record, db)


@app.delete(f"{settings.api_prefix}/employees/{{employee_id}}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: AccountRecord = Depends(get_current_user),
) -> None:
    if current_user.id == employee_id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")

    record = db.get(AccountRecord, employee_id)
    if not record:
        raise HTTPException(status_code=404, detail="Employee not found")

    sessions = db.scalars(select(SessionRecord).where(SessionRecord.user_id == employee_id)).all()
    for session in sessions:
        db.delete(session)

    log_audit_action(
        db,
        "deleted_employee",
        "Employee",
        record.id,
        current_user.name,
        f"Deleted employee {record.name}",
    )
    db.delete(record)
    db.commit()


@app.get(f"{settings.api_prefix}/branches", response_model=list[BranchOut])
def list_branches(
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> list[BranchOut]:
    branches = db.scalars(select(BranchRecord).order_by(BranchRecord.created_at.desc())).all()
    return [to_branch_out(branch) for branch in branches]


@app.post(f"{settings.api_prefix}/branches", response_model=BranchOut, status_code=status.HTTP_201_CREATED)
def create_branch(
    payload: BranchCreate,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> BranchOut:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Branch name is required")

    code = payload.code.strip().upper()
    if code and db.scalar(select(BranchRecord).where(BranchRecord.code == code)):
        raise HTTPException(status_code=409, detail=f"Branch code {code} already exists")
    if db.scalar(select(BranchRecord).where(BranchRecord.name == name)):
        raise HTTPException(status_code=409, detail=f"Branch {name} already exists")

    record = BranchRecord(name=name, code=code, address=payload.address or "", manager=payload.manager or "", active=payload.active)
    db.add(record)
    db.flush()
    log_audit_action(
        db,
        "created_branch",
        "Branch",
        record.id,
        _current_user.name,
        f"Created branch {record.name}",
    )
    db.commit()
    db.refresh(record)
    return to_branch_out(record)


@app.put(f"{settings.api_prefix}/branches/{{branch_id}}", response_model=BranchOut)
def update_branch(
    branch_id: int,
    payload: BranchUpdate,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> BranchOut:
    record = db.get(BranchRecord, branch_id)
    if not record:
        raise HTTPException(status_code=404, detail="Branch not found")

    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="Branch name is required")
        if name != record.name and db.scalar(select(BranchRecord).where(BranchRecord.name == name)):
            raise HTTPException(status_code=409, detail=f"Branch {name} already exists")
        record.name = name

    if payload.code is not None:
        code = payload.code.strip().upper()
        if code and code != record.code and db.scalar(select(BranchRecord).where(BranchRecord.code == code)):
            raise HTTPException(status_code=409, detail=f"Branch code {code} already exists")
        record.code = code

    if payload.address is not None:
        record.address = payload.address or ""
    if payload.manager is not None:
        record.manager = payload.manager or ""
    if payload.active is not None:
        record.active = payload.active

    log_audit_action(
        db,
        "updated_branch",
        "Branch",
        record.id,
        _current_user.name,
        f"Updated branch {record.name}",
    )
    db.commit()
    db.refresh(record)
    return to_branch_out(record)


@app.delete(f"{settings.api_prefix}/branches/{{branch_id}}", status_code=status.HTTP_204_NO_CONTENT)
def delete_branch(
    branch_id: int,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> None:
    record = db.get(BranchRecord, branch_id)
    if not record:
        raise HTTPException(status_code=404, detail="Branch not found")
    log_audit_action(
        db,
        "deleted_branch",
        "Branch",
        record.id,
        _current_user.name,
        f"Deleted branch {record.name}",
    )
    db.delete(record)
    db.commit()


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
    log_audit_action(
        db,
        "updated_settings",
        "Settings",
        app_settings.id,
        _current_user.name,
        "Updated application settings",
    )
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
    log_audit_action(
        db,
        "created_job",
        "Job",
        record.id,
        _current_user.name,
        f"Created job {record.id}",
    )
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
    log_audit_action(
        db,
        "updated_job",
        "Job",
        record.id,
        _current_user.name,
        f"Updated job {record.id}",
    )
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
    log_audit_action(
        db,
        "updated_job_status",
        "Job",
        record.id,
        _current_user.name,
        f"Updated job status to {payload.status}",
    )
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
    log_audit_action(
        db,
        "released_job",
        "Job",
        record.id,
        _current_user.name,
        f"Released job {record.id}",
    )
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
    log_audit_action(
        db,
        "deleted_job",
        "Job",
        record.id,
        _current_user.name,
        f"Deleted job {record.id}",
    )
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
    db.flush()
    log_audit_action(
        db,
        "created_discount",
        "Discount",
        record.id,
        _current_user.name,
        f"Created discount {record.code}",
    )
    db.commit()
    db.refresh(record)
    return to_discount_out(record)


@app.patch(f"{settings.api_prefix}/discounts/{{discount_id}}", response_model=DiscountOut)
def update_discount(
    discount_id: int,
    payload: DiscountUpdate,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> DiscountOut:
    record = db.get(DiscountRecord, discount_id)
    if not record:
        raise HTTPException(status_code=404, detail="Discount not found")

    data = payload.model_dump(exclude_unset=True)

    if "code" in data and data["code"] is not None:
        code = data["code"].strip().upper()
        if code != record.code and db.scalar(select(DiscountRecord).where(DiscountRecord.code == code)):
            raise HTTPException(status_code=409, detail=f"Discount code {code} already exists")
        record.code = code

    if "name" in data:
        record.name = data["name"]
    if "percent" in data:
        record.percent = data["percent"]
    if "expiresAt" in data:
        record.expires_at = data["expiresAt"]
    if "maxUses" in data:
        record.max_uses = data["maxUses"]
    if "active" in data:
        record.active = data["active"]

    log_audit_action(
        db,
        "updated_discount",
        "Discount",
        record.id,
        _current_user.name,
        f"Updated discount {record.code}",
    )
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
    log_audit_action(
        db,
        "deleted_discount",
        "Discount",
        record.id,
        _current_user.name,
        f"Deleted discount {record.code}",
    )
    db.delete(record)
    db.commit()


@app.get(f"{settings.api_prefix}/audit-logs", response_model=list[AuditLogOut])
def list_audit_logs(
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
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


@app.get(f"{settings.api_prefix}/bins", response_model=list[BinOut])
def list_bins(
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> list[BinOut]:
    bins = db.scalars(select(BinRecord).order_by(BinRecord.created_at.desc())).all()
    return [to_bin_out(bin_record, db) for bin_record in bins]


@app.post(f"{settings.api_prefix}/bins", response_model=BinOut, status_code=status.HTTP_201_CREATED)
def create_bin(
    payload: BinCreate,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> BinOut:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Bin name is required")

    if db.scalar(select(BinRecord).where(BinRecord.name == name)):
        raise HTTPException(status_code=409, detail=f"Bin {name} already exists")

    record = BinRecord(
        name=name,
        branch=payload.branch.strip() or "Main Branch",
        capacity=payload.capacity,
        reserved=payload.reserved,
        active=payload.active,
    )
    db.add(record)
    db.flush()
    log_audit_action(
        db,
        "created_bin",
        "Bin",
        record.id,
        _current_user.name,
        f"Created bin {record.name}",
    )
    db.commit()
    db.refresh(record)
    return to_bin_out(record, db)


@app.put(f"{settings.api_prefix}/bins/{{bin_id}}", response_model=BinOut)
def update_bin(
    bin_id: int,
    payload: BinUpdate,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> BinOut:
    record = db.get(BinRecord, bin_id)
    if not record:
        raise HTTPException(status_code=404, detail="Bin not found")

    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="Bin name is required")
        if name != record.name and db.scalar(select(BinRecord).where(BinRecord.name == name)):
            raise HTTPException(status_code=409, detail=f"Bin {name} already exists")
        record.name = name

    if payload.branch is not None:
        record.branch = payload.branch.strip() or "Main Branch"
    if payload.capacity is not None:
        record.capacity = payload.capacity
    if payload.reserved is not None:
        record.reserved = payload.reserved
    if payload.active is not None:
        record.active = payload.active

    log_audit_action(
        db,
        "updated_bin",
        "Bin",
        record.id,
        _current_user.name,
        f"Updated bin {record.name}",
    )
    db.commit()
    db.refresh(record)
    return to_bin_out(record, db)


@app.delete(f"{settings.api_prefix}/bins/{{bin_id}}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bin(
    bin_id: int,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> None:
    record = db.get(BinRecord, bin_id)
    if not record:
        raise HTTPException(status_code=404, detail="Bin not found")
    log_audit_action(
        db,
        "deleted_bin",
        "Bin",
        record.id,
        _current_user.name,
        f"Deleted bin {record.name}",
    )
    db.delete(record)
    db.commit()


@app.get(f"{settings.api_prefix}/bins/summary", response_model=list[BinSummary])
def get_bins_summary(
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> list[BinSummary]:
    active_jobs = db.scalars(select(JobRecord).where(JobRecord.released.is_(False))).all()
    bin_names = [record.name for record in db.scalars(select(BinRecord).where(BinRecord.active.is_(True))).all()]
    if not bin_names:
        bin_names = ALL_BINS

    bins: dict[str, list[JobRecord]] = {name: [] for name in bin_names}
    for job in active_jobs:
        if job.bin in bins:
            bins[job.bin].append(job)

    summaries: list[BinSummary] = []
    for bin_name in bin_names:
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





# Helper function to convert PricingRecord to PricingOut
def to_pricing_out(pricing: PricingRecord) -> PricingOut:
    return PricingOut(
        id=pricing.id,
        name=pricing.name,
        description=pricing.description,
        price=pricing.price,
        category=pricing.category,
        duration_days=pricing.duration_days,
        is_active=pricing.is_active,
        created_at=pricing.created_at,
        updated_at=pricing.updated_at,
    )


# Pricing Endpoints

# Fix the pricing endpoints - use string concatenation instead of f-strings for paths with parameters

@app.get(settings.api_prefix + "/pricing", response_model=list[PricingOut])
def list_pricing(
    category: str | None = Query(default=None, description="Filter by category"),
    is_active: bool | None = Query(default=None, description="Filter by active status"),
    search: str | None = Query(default=None, description="Search in name and description"),
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> list[PricingOut]:
    """List all pricing items with optional filters"""
    query = select(PricingRecord)
    
    if category:
        query = query.where(PricingRecord.category == category)
    if is_active is not None:
        query = query.where(PricingRecord.is_active == is_active)
    if search:
        search_term = f"%{search}%"
        query = query.where(
            (PricingRecord.name.ilike(search_term)) | 
            (PricingRecord.description.ilike(search_term))
        )
    
    pricing_items = db.scalars(query.order_by(PricingRecord.created_at.desc())).all()
    return [to_pricing_out(item) for item in pricing_items]


@app.get(settings.api_prefix + "/pricing/categories", response_model=list[str])
def list_pricing_categories(
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> list[str]:
    """Get all unique pricing categories"""
    categories = db.scalars(
        select(PricingRecord.category)
        .distinct()
        .where(PricingRecord.category.isnot(None))
        .order_by(PricingRecord.category)
    ).all()
    return [cat for cat in categories if cat and cat.strip()]


@app.post(settings.api_prefix + "/pricing", response_model=PricingOut, status_code=status.HTTP_201_CREATED)
def create_pricing(
    payload: PricingCreate,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> PricingOut:
    """Create a new pricing item"""
    # Check if pricing with same name exists
    existing = db.scalar(
        select(PricingRecord).where(PricingRecord.name == payload.name)
    )
    if existing:
        raise HTTPException(
            status_code=409, 
            detail=f"Pricing item with name '{payload.name}' already exists"
        )
    
    record = PricingRecord(
        name=payload.name,
        description=payload.description,
        price=payload.price,
        category=payload.category,
        duration_days=payload.duration_days,
        is_active=payload.is_active,
    )
    db.add(record)
    db.flush()
    log_audit_action(
        db,
        "created_pricing",
        "Pricing",
        record.id,
        _current_user.name,
        f"Created pricing item {record.name}",
    )
    db.commit()
    db.refresh(record)
    return to_pricing_out(record)


@app.get(settings.api_prefix + "/pricing/{pricing_id}", response_model=PricingOut)
def get_pricing(
    pricing_id: int,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> PricingOut:
    """Get a specific pricing item by ID"""
    record = db.get(PricingRecord, pricing_id)
    if not record:
        raise HTTPException(status_code=404, detail="Pricing item not found")
    return to_pricing_out(record)


@app.put(settings.api_prefix + "/pricing/{pricing_id}", response_model=PricingOut)
def update_pricing(
    pricing_id: int,
    payload: PricingUpdate,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> PricingOut:
    """Update an existing pricing item"""
    record = db.get(PricingRecord, pricing_id)
    if not record:
        raise HTTPException(status_code=404, detail="Pricing item not found")
    
    # Check for name conflicts if name is being updated
    if payload.name is not None and payload.name != record.name:
        existing = db.scalar(
            select(PricingRecord).where(PricingRecord.name == payload.name)
        )
        if existing:
            raise HTTPException(
                status_code=409, 
                detail=f"Pricing item with name '{payload.name}' already exists"
            )
        record.name = payload.name
    
    # Update fields if provided
    if payload.description is not None:
        record.description = payload.description
    if payload.price is not None:
        record.price = payload.price
    if payload.category is not None:
        record.category = payload.category
    if payload.duration_days is not None:
        record.duration_days = payload.duration_days
    if payload.is_active is not None:
        record.is_active = payload.is_active
    
    record.updated_at = datetime.utcnow()
    log_audit_action(
        db,
        "updated_pricing",
        "Pricing",
        record.id,
        _current_user.name,
        f"Updated pricing item {record.name}",
    )
    db.commit()
    db.refresh(record)
    return to_pricing_out(record)


@app.patch(settings.api_prefix + "/pricing/{pricing_id}/toggle", response_model=PricingOut)
def toggle_pricing_active(
    pricing_id: int,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> PricingOut:
    """Toggle the active status of a pricing item"""
    record = db.get(PricingRecord, pricing_id)
    if not record:
        raise HTTPException(status_code=404, detail="Pricing item not found")
    
    record.is_active = not record.is_active
    record.updated_at = datetime.utcnow()
    log_audit_action(
        db,
        "toggled_pricing",
        "Pricing",
        record.id,
        _current_user.name,
        f"Toggled pricing item {record.name}",
    )
    db.commit()
    db.refresh(record)
    return to_pricing_out(record)


@app.delete(settings.api_prefix + "/pricing/{pricing_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pricing(
    pricing_id: int,
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> None:
    """Delete a pricing item"""
    record = db.get(PricingRecord, pricing_id)
    if not record:
        raise HTTPException(status_code=404, detail="Pricing item not found")
    
    log_audit_action(
        db,
        "deleted_pricing",
        "Pricing",
        record.id,
        _current_user.name,
        f"Deleted pricing item {record.name}",
    )
    db.delete(record)
    db.commit()


@app.post(settings.api_prefix + "/pricing/bulk", response_model=list[PricingOut], status_code=status.HTTP_201_CREATED)
def bulk_create_pricing(
    items: list[PricingCreate],
    db: Session = Depends(get_db),
    _current_user: AccountRecord = Depends(get_current_user),
) -> list[PricingOut]:
    """Create multiple pricing items at once (useful for initial setup)"""
    created_items = []
    errors = []
    
    for idx, item in enumerate(items):
        # Check if pricing with same name exists
        existing = db.scalar(
            select(PricingRecord).where(PricingRecord.name == item.name)
        )
        if existing:
            errors.append(f"Item '{item.name}' already exists (index {idx})")
            continue
            
        record = PricingRecord(
            name=item.name,
            description=item.description,
            price=item.price,
            category=item.category,
            duration_days=item.duration_days,
            is_active=item.is_active,
        )
        db.add(record)
        created_items.append(record)
    
    if not created_items and errors:
        raise HTTPException(
            status_code=400, 
            detail=f"No items created: {', '.join(errors)}"
        )

    db.flush()
    for item in created_items:
        log_audit_action(
            db,
            "created_pricing",
            "Pricing",
            item.id,
            _current_user.name,
            f"Created pricing item {item.name} (bulk)",
        )

    db.commit()
    
    # Refresh all created items
    for item in created_items:
        db.refresh(item)
    
    return [to_pricing_out(item) for item in created_items]