from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, EmailStr


class ParentBase(BaseModel):
    organization_id: UUID
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=10, max_length=20)
    email: EmailStr | None = None
    address: str | None = Field(None, max_length=500)
    relationship: str | None = Field(None, max_length=50)
    is_primary: bool = False
    notification_email: bool = True
    notification_sms: bool = False
    notification_whatsapp: bool = False
    status: str = Field(default="active")


class ParentCreate(ParentBase):
    pass


class ParentUpdate(BaseModel):
    first_name: str | None = Field(None, min_length=2, max_length=100)
    last_name: str | None = Field(None, min_length=2, max_length=100)
    phone: str | None = Field(None, min_length=10, max_length=20)
    email: EmailStr | None = None
    address: str | None = Field(None, max_length=500)
    relationship: str | None = Field(None, max_length=50)
    is_primary: bool | None = None
    notification_email: bool | None = None
    notification_sms: bool | None = None
    notification_whatsapp: bool | None = None
    status: str | None = None


class ParentResponse(ParentBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    class Config:
        from_attributes = True
