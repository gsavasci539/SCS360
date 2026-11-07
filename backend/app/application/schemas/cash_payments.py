"""Validated requests for the canonical cash/externally collected ledger."""
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CashPaymentCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, allow_inf_nan=False, extra="forbid")
    debt_id: UUID
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    payment_method: Literal["CASH", "CREDIT_CARD", "BANK_TRANSFER", "EFT", "OTHER"]
    notes: str | None = Field(default=None, max_length=2000)
    request_id: UUID | None = Field(default=None, description="Aynı tahsilatı yeniden denerken aynı UUID'yi kullanın.")

    @field_validator("notes")
    @classmethod
    def empty_notes(cls, value):
        return value or None


class CashPaymentCancel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    cancel_reason: str | None = Field(default=None, max_length=2000)

    @field_validator("cancel_reason")
    @classmethod
    def empty_reason(cls, value):
        return value or None
