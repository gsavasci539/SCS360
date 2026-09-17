from datetime import datetime
from uuid import UUID
from decimal import Decimal
from pydantic import BaseModel, Field


class PaymentBase(BaseModel):
    organization_id: UUID
    branch_id: UUID
    student_id: UUID
    debt_id: UUID
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    payment_method: str = Field(..., min_length=2, max_length=50)
    payment_date: datetime
    notes: str | None = Field(None, max_length=500)
    status: str = Field(default="completed")


class PaymentCreate(PaymentBase):
    pass


class PaymentUpdate(BaseModel):
    amount: Decimal | None = Field(None, gt=0, decimal_places=2)
    payment_method: str | None = Field(None, min_length=2, max_length=50)
    payment_date: datetime | None = None
    notes: str | None = Field(None, max_length=500)
    status: str | None = None


class PaymentResponse(PaymentBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    class Config:
        from_attributes = True
