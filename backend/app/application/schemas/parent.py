from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, EmailStr, field_validator
from app.infrastructure.models.models import ParentRelationType


class ParentBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    organization_id: UUID
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=100)
    relation_type: ParentRelationType = ParentRelationType.GUARDIAN
    phone: str | None = Field(None, min_length=10, max_length=20)
    sms_phone: str | None = Field(None, min_length=10, max_length=20)
    whatsapp_phone: str | None = Field(None, min_length=10, max_length=20)
    email: EmailStr | None = None
    address: str | None = Field(None, max_length=500)
    receive_notifications: bool = True


class ParentCreate(ParentBase):
    pass


class ParentUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    first_name: str | None = Field(None, min_length=2, max_length=100)
    last_name: str | None = Field(None, min_length=2, max_length=100)
    relation_type: ParentRelationType | None = None
    phone: str | None = Field(None, min_length=10, max_length=20)
    sms_phone: str | None = Field(None, min_length=10, max_length=20)
    whatsapp_phone: str | None = Field(None, min_length=10, max_length=20)
    email: EmailStr | None = None
    address: str | None = Field(None, max_length=500)
    receive_notifications: bool | None = None

    @field_validator("first_name", "last_name", "relation_type", "receive_notifications")
    @classmethod
    def required_when_provided(cls, value):
        if value is None:
            raise ValueError("Alan boş olamaz")
        return value


class ParentResponse(ParentBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    class Config:
        from_attributes = True
