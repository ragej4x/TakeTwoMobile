from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


Status = Literal[
    "Cleaning Stage",
    "Drying Area",
    "Restoration",
    "Quality Control",
    "Packaging",
    "For Release",
]
ConnStatus = Literal["connected", "offline", "error"]
ThemeName = Literal["light", "dark", "ocean", "mono", "ink"]


class AdditionalService(BaseModel):
    name: str
    price: float = 0.0


class ShoeItem(BaseModel):
    itemId: str
    size: str = ""
    brand: str = ""
    model: str = ""
    color: str = ""
    services: list[str] = Field(default_factory=list)
    additionalServices: list[AdditionalService] = Field(default_factory=list)
    sponsored: bool = False
    damages: list[str] = Field(default_factory=list)
    otherDamage: str = ""
    totalItemPayment: float = 0.0
    photos: dict[str, str] = Field(default_factory=dict)
    afterPhotos: dict[str, str] = Field(default_factory=dict)


class BranchBase(BaseModel):
    name: str
    code: str = ""
    address: str = ""
    manager: str = ""
    active: bool = True


class BranchCreate(BranchBase):
    pass


class BranchUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    address: str | None = None
    manager: str | None = None
    active: bool | None = None


class BranchOut(BranchBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    createdAt: datetime
    updatedAt: datetime


class JobBase(BaseModel):
    customer: str
    phone: str = ""
    email: str = ""
    dateReceived: str
    expectedRelease: str = ""
    shoes: list[ShoeItem] = Field(default_factory=list)
    bin: str = ""
    status: Status = "Cleaning Stage"
    receiveUpdates: bool = False
    totalPayment: float = 0.0
    notes: str = ""
    assignedTo: str = ""
    branch: str = ""
    released: bool = False
    signatureDataUrl: str | None = None
    discountCode: str | None = None
    discountName: str | None = None
    discountPercent: float | None = None
    discountAmount: float | None = None


class JobCreate(JobBase):
    id: str | None = None


class JobUpdate(JobBase):
    pass


class JobOut(JobBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    createdAt: datetime
    updatedAt: datetime


class JobStatusUpdate(BaseModel):
    status: Status


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LogoutResponse(BaseModel):
    message: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetVerifyRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)


class PasswordResetConfirmRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)
    newPassword: str = Field(min_length=4)


class PasswordResetRequestResponse(BaseModel):
    message: str
    expiresInSeconds: int


class PasswordResetVerifyResponse(BaseModel):
    message: str


class PasswordResetConfirmResponse(BaseModel):
    message: str


class ProfileData(BaseModel):
    name: str
    phone: str
    email: str
    role: str
    branch: str
    photoUrl: str | None = None


class SettingsData(BaseModel):
    connStatus: ConnStatus
    theme: ThemeName
    branch: str
    selectedPrinter: str


class AuthResponse(BaseModel):
    token: str
    profile: ProfileData


class BinSummary(BaseModel):
    bin: str
    occupied: bool
    orderCount: int
    pairCount: int
    jobs: list[str]


class DiscountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    percent: float
    maxUses: int | None
    timesUsed: int
    expiresAt: datetime | None
    active: bool


class DiscountCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    code: str = Field(min_length=1, max_length=40)
    percent: float = Field(gt=0, le=100)
    expiresAt: datetime | None = None
    maxUses: int | None = None


class DiscountUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str | None = None
    code: str | None = Field(default=None, min_length=1, max_length=40)
    percent: float | None = Field(default=None, gt=0, le=100)
    expiresAt: datetime | None = None
    maxUses: int | None = None
    active: bool | None = None


class DiscountValidateRequest(BaseModel):
    code: str


class DiscountValidateResponse(BaseModel):
    valid: bool
    name: str | None = None
    percent: float | None = None
    message: str | None = None


class BinBase(BaseModel):
    name: str
    branch: str = "Main Branch"
    capacity: int = Field(default=12, ge=1)
    reserved: int = Field(default=0, ge=0)
    active: bool = True


class BinCreate(BinBase):
    pass


class BinUpdate(BaseModel):
    name: str | None = None
    branch: str | None = None
    capacity: int | None = Field(default=None, ge=1)
    reserved: int | None = Field(default=None, ge=0)
    active: bool | None = None


class BinOut(BinBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    occupiedCount: int = 0
    availableCount: int = 0
    createdAt: datetime
    updatedAt: datetime


class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    phone: str
    role: str
    branch: str
    photoUrl: str | None = None
    joinDate: datetime
    jobsCompleted: int = 0
    revenue: float = 0
    status: str = "Active"


class EmployeeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    phone: str = ""
    role: str = "Staff"
    branch: str = "Main Branch"
    password: str = Field(min_length=4)


class EmployeeUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    role: str | None = None
    branch: str | None = None
    password: str | None = Field(default=None, min_length=4)


#pricing schema


class PricingBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(None, max_length=500)
    price: float = Field(gt=0)
    category: str | None = Field(None, max_length=100)
    duration_days: int | None = Field(None, ge=1, description="Estimated duration in days. None means no expiration/indefinite")
    is_active: bool = True


class PricingCreate(PricingBase):
    pass


class PricingUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=500)
    price: float | None = Field(None, gt=0)
    category: str | None = Field(None, max_length=100)
    duration_days: int | None = Field(None, ge=1, description="Estimated duration in days. None means no expiration/indefinite")
    is_active: bool | None = None


class PricingOut(PricingBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    updated_at: datetime