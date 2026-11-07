from decimal import Decimal
from typing import Literal
from uuid import UUID, uuid4

from pydantic import AwareDatetime, BaseModel, ConfigDict, EmailStr, Field, field_validator


class PlanWrite(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    code: str = Field(min_length=2, max_length=50, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=2, max_length=120)
    branch_limit: int = Field(ge=1, le=2147483647)
    student_limit: int = Field(ge=1, le=2147483647)
    user_limit: int = Field(ge=1, le=2147483647)
    price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    currency: Literal["TRY", "USD", "EUR"] = "TRY"
    period_months: Literal[1, 12] = 1
    is_active: bool = True

    @field_validator("code", mode="after")
    @classmethod
    def normalized_code(cls, value):
        return value.upper()


class TenantProvision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=2, max_length=255)
    owner_email: EmailStr
    owner_password: str = Field(min_length=8, max_length=4096)
    owner_first_name: str = Field(min_length=1, max_length=100)
    owner_last_name: str = Field(min_length=1, max_length=100)
    plan_id: UUID
    period_start: AwareDatetime | None = None
    period_end: AwareDatetime | None = None
    request_id: UUID = Field(default_factory=uuid4)


class MembershipWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan_id: UUID
    period_start: AwareDatetime
    period_end: AwareDatetime
    admin_status: Literal["ACTIVE", "SUSPENDED"] = "ACTIVE"
    owner_user_id: UUID | None = None


class TenantStatusWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_active: bool


class PublicSignup(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=2, max_length=255)
    owner_email: EmailStr
    owner_password: str = Field(min_length=8, max_length=4096)
    owner_first_name: str = Field(min_length=1, max_length=100)
    owner_last_name: str = Field(min_length=1, max_length=100)
    plan_id: UUID
    request_id: UUID


class SubscriptionInvoiceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan_id: UUID
    request_id: UUID = Field(default_factory=uuid4)


class VerifiedReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    payment_reference: str = Field(min_length=1, max_length=240)
    amount: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    currency: Literal["TRY", "USD", "EUR"]
    paid_at: AwareDatetime | None = None


class SubscriptionCheckoutStart(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    request_id: UUID
    identity_number: str = Field(min_length=1, max_length=50)
    phone: str = Field(min_length=5, max_length=30)
    address: str = Field(min_length=5, max_length=500)
    city: str = Field(min_length=1, max_length=100)
    country: str = Field(min_length=1, max_length=100)


class SubscriptionPaymentReview(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    request_id: UUID
    action: Literal["APPLY", "REFUND_RECORDED"]
    reason: str = Field(min_length=10, max_length=1000)
    period_start: AwareDatetime | None = None
    period_end: AwareDatetime | None = None
    refund_reference: str | None = Field(default=None, min_length=1, max_length=240)
