from datetime import datetime
from uuid import UUID
from decimal import Decimal
from pydantic import BaseModel, Field


class DebtBase(BaseModel):
    organization_id: UUID
    branch_id: UUID
    student_id: UUID
    debt_type: str = Field(..., min_length=2, max_length=50)
    description: str | None = Field(None, max_length=500)
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    due_date: datetime | None = None
    academic_year: str | None = Field(None, max_length=20)
    status: str = Field(default="pending")


class DebtCreate(DebtBase):
    pass


class DebtUpdate(BaseModel):
    debt_type: str | None = Field(None, min_length=2, max_length=50)
    description: str | None = Field(None, max_length=500)
    amount: Decimal | None = Field(None, gt=0, decimal_places=2)
    due_date: datetime | None = None
    academic_year: str | None = Field(None, max_length=20)
    status: str | None = None


class DebtResponse(DebtBase):
    id: UUID
    paid_amount: Decimal
    remaining_amount: Decimal
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    class Config:
        from_attributes = True
