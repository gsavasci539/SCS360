from datetime import datetime
from uuid import UUID
from decimal import Decimal
from pydantic import BaseModel


class ReceiptResponse(BaseModel):
    id: UUID
    organization_id: UUID
    branch_id: UUID
    payment_id: UUID
    receipt_number: str
    student_name: str
    amount: Decimal
    payment_method: str
    payment_date: datetime
    notes: str | None
    created_at: datetime

    class Config:
        from_attributes = True
