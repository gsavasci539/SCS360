from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class SchoolPaymentReview(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    request_id: UUID
    expected_revision: str = Field(pattern=r"^[0-9a-f]{64}$")
    action: Literal["APPLY", "REFUND_RECORDED"]
    reason: str = Field(min_length=10, max_length=1000)
    refund_reference: str | None = Field(default=None, min_length=1, max_length=240)
    refund_amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2, allow_inf_nan=False)
    refund_currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    refunded_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def validate_action(self):
        fields = (self.refund_reference, self.refund_amount, self.refund_currency, self.refunded_at)
        if self.action == "APPLY" and any(value is not None for value in fields):
            raise ValueError("Borç mutabakatına iade alanları gönderilemez")
        if self.action == "REFUND_RECORDED":
            if any(value is None for value in fields):
                raise ValueError("Önceden tamamlanmış tam iadenin referansı, tutarı, para birimi ve tarihi gerekli")
            self.refunded_at = self.refunded_at.astimezone(UTC)
            if self.refunded_at > datetime.now(UTC) + timedelta(minutes=5):
                raise ValueError("İade tarihi gelecekte olamaz")
        return self
