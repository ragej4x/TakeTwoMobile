import enum
from datetime import datetime
from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base
from .utils.time import now_manila


class RequestStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    in_progress = "in_progress"
    ready_for_pickup = "ready_for_pickup"
    completed = "completed"
    cancelled = "cancelled"


class QRCode(Base):
    __tablename__ = "qr_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(8), unique=True, nullable=False, index=True)
    is_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    branch_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_manila)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    request: Mapped["DropoffRequest | None"] = relationship(back_populates="qr_code", uselist=False)


class CustomerAccount(Base):
    __tablename__ = "customer_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(512), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String, nullable=True)
    branch: Mapped[str | None] = mapped_column(String(120), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_manila)

    requests: Mapped[list["DropoffRequest"]] = relationship(back_populates="customer_account")


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_manila)

    requests: Mapped[list["DropoffRequest"]] = relationship(back_populates="customer")


class DropoffRequest(Base):
    __tablename__ = "dropoff_requests"
    __table_args__ = (UniqueConstraint("qr_code_id", name="uq_qr_code_per_request"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    qr_code_id: Mapped[int] = mapped_column(ForeignKey("qr_codes.id"), nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    customer_account_id: Mapped[int | None] = mapped_column(ForeignKey("customer_accounts.id"), nullable=True)

    shoe_brand: Mapped[str | None] = mapped_column(String(100), nullable=True)
    shoe_model: Mapped[str | None] = mapped_column(String(150), nullable=True)
    shoe_color: Mapped[str | None] = mapped_column(String(100), nullable=True)
    service_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    special_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_urls: Mapped[list[str]] = mapped_column(JSON, default=list)
    price_list: Mapped[str | None] = mapped_column(String(255), nullable=True)
    discounts: Mapped[str | None] = mapped_column(String(255), nullable=True)
    number_of_pairs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bin: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sponsored: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    status: Mapped[RequestStatus] = mapped_column(String(40), nullable=False, default=RequestStatus.pending, index=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    branch_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviewed_by_staff_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Set once a job order has been created from this (approved) request.
    # NULL + status == approved means "approved, job not created yet" — this
    # is what makes that state durable across page reloads instead of living
    # only in frontend component state.
    job_id: Mapped[str | None] = mapped_column(ForeignKey("jobs.id"), nullable=True)

    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=now_manila)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_manila, onupdate=now_manila)

    qr_code: Mapped[QRCode] = relationship(back_populates="request")
    customer: Mapped[Customer] = relationship(back_populates="requests")
    customer_account: Mapped[CustomerAccount | None] = relationship(back_populates="requests")


class DropoffStatusHistory(Base):
    __tablename__ = "dropoff_status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("dropoff_requests.id"), nullable=False)
    old_status: Mapped[RequestStatus | None] = mapped_column(String(40), nullable=True)
    new_status: Mapped[RequestStatus] = mapped_column(String(40), nullable=False)
    changed_by_staff_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=now_manila)


class BranchRecord(Base):
    __tablename__ = "branches"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False, default="")
    address: Mapped[str] = mapped_column(String(500), default="")
    manager: Mapped[str] = mapped_column(String(200), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_manila)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_manila, onupdate=now_manila)

class JobRecord(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, index=True)
    customer: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str] = mapped_column(String(40), default="")
    email: Mapped[str] = mapped_column(String(255), default="")
    date_received: Mapped[str] = mapped_column(String(20), nullable=False)
    expected_release: Mapped[str] = mapped_column(String(20), default="")
    shoes: Mapped[list] = mapped_column(JSON, default=list)
    bin: Mapped[str] = mapped_column(String(20), default="")
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    receive_updates: Mapped[bool] = mapped_column(Boolean, default=False)
    total_payment: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[str] = mapped_column(String(2000), default="")
    assigned_to: Mapped[str] = mapped_column(String(200), default="")
    branch: Mapped[str] = mapped_column(String(120), default="")
    released: Mapped[bool] = mapped_column(Boolean, default=False)
    signature_data_url: Mapped[str | None] = mapped_column(String, nullable=True)
    discount_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    discount_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    discount_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    discount_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_manila)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_manila, onupdate=now_manila)

class ProfileRecord(Base):
    __tablename__ = "profile"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    name: Mapped[str] = mapped_column(String(200))
    phone: Mapped[str] = mapped_column(String(40))
    email: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(100))
    branch: Mapped[str] = mapped_column(String(120))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_manila, onupdate=now_manila)

class SettingsRecord(Base):
    __tablename__ = "app_settings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    conn_status: Mapped[str] = mapped_column(String(40), default="connected")
    theme: Mapped[str] = mapped_column(String(40), default="light")
    branch: Mapped[str] = mapped_column(String(120), default="Main Branch")
    selected_printer: Mapped[str] = mapped_column(String(120), default="Brother QL-820NWB")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_manila, onupdate=now_manila)

class AccountRecord(Base):
    __tablename__ = "accounts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    role: Mapped[str] = mapped_column(String(100), nullable=False, default="Staff")
    branch: Mapped[str] = mapped_column(String(120), nullable=False, default="Main Branch")
    photo_url: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_manila)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_manila, onupdate=now_manila)

class BinRecord(Base):
    __tablename__ = "bins"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(60), unique=True, index=True, nullable=False)
    branch: Mapped[str] = mapped_column(String(120), nullable=False, default="Main Branch")
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=12)
    reserved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_manila)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_manila, onupdate=now_manila)

class SessionRecord(Base):
    __tablename__ = "sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_manila)

class DiscountRecord(Base):
    __tablename__ = "discounts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    percent: Mapped[float] = mapped_column(Float, nullable=False)
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    times_used: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_manila)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_manila, onupdate=now_manila)

class PasswordResetCodeRecord(Base):
    __tablename__ = "password_reset_codes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(6), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_manila)

class AuditLogRecord(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    entity_id: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    user_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    details: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_manila)

class PricingRecord(Base):
    __tablename__ = "pricing"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)