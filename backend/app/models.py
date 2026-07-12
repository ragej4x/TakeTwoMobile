from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class BranchRecord(Base):
    __tablename__ = "branches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False, default="")
    address: Mapped[str] = mapped_column(String(500), default="")
    manager: Mapped[str] = mapped_column(String(200), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class ProfileRecord(Base):
    __tablename__ = "profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    name: Mapped[str] = mapped_column(String(200))
    phone: Mapped[str] = mapped_column(String(40))
    email: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(100))
    branch: Mapped[str] = mapped_column(String(120))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class SettingsRecord(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    conn_status: Mapped[str] = mapped_column(String(40), default="connected")
    theme: Mapped[str] = mapped_column(String(40), default="light")
    branch: Mapped[str] = mapped_column(String(120), default="Main Branch")
    selected_printer: Mapped[str] = mapped_column(String(120), default="Brother QL-820NWB")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class AccountRecord(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    role: Mapped[str] = mapped_column(String(100), nullable=False, default="Staff")
    branch: Mapped[str] = mapped_column(String(120), nullable=False, default="Main Branch")
    is_test_account: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    photo_url: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class BinRecord(Base):
    __tablename__ = "bins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(60), unique=True, index=True, nullable=False)
    branch: Mapped[str] = mapped_column(String(120), nullable=False, default="Main Branch")
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=12)
    reserved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class SessionRecord(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DiscountRecord(Base):
    __tablename__ = "discounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    percent: Mapped[float] = mapped_column(Float, nullable=False)  # e.g. 20 for 20% off
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)  # None = unlimited
    times_used: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # None = never expires
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class PasswordResetCodeRecord(Base):
    __tablename__ = "password_reset_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(6), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)



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
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )