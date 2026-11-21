from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=4096)


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=4096)


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    last_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    email: EmailStr = Field(max_length=255)
    phone: Annotated[str, StringConstraints(strip_whitespace=True, max_length=20)] | None = None
    current_password: str | None = Field(default=None, min_length=1, max_length=4096)


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str = Field(min_length=1, max_length=4096)
    new_password: str = Field(min_length=8, max_length=4096)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
