"""Write-only merchant credentials; reading this DTO cannot reveal a secret."""
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class SchoolPaymentMerchantUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    expected_revision: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    enabled: bool
    environment: Literal["SANDBOX", "LIVE"]
    api_key: SecretStr | None = Field(default=None, max_length=2048)
    secret_key: SecretStr | None = Field(default=None, max_length=2048)
    replace_account: bool = False
    provider: Literal["iyzico", "paytr", "craftgate", "sipay"] | None = None
    credentials: dict[str, Annotated[SecretStr, Field(max_length=2048)]] | None = Field(default=None, max_length=8)

    @field_validator("api_key", "secret_key", mode="before")
    @classmethod
    def preserve_omitted_secrets(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value
