from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, EmailStr


class UserBase(BaseModel):
    organization_id: UUID
    email: EmailStr
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=100)
    phone: str | None = Field(None, max_length=20)
    is_active: bool = True
    status: str = Field(default="active")


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    first_name: str | None = Field(None, min_length=2, max_length=100)
    last_name: str | None = Field(None, min_length=2, max_length=100)
    phone: str | None = Field(None, max_length=20)
    is_active: bool | None = None
    status: str | None = None
    password: str | None = Field(None, min_length=8)


class UserResponse(UserBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
