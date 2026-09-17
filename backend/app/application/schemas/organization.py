from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, EmailStr


class OrganizationBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    tax_number: str = Field(..., min_length=10, max_length=50)
    tax_office: str = Field(..., min_length=2, max_length=100)
    address: str | None = Field(None, max_length=500)
    phone: str | None = Field(None, max_length=20)
    email: EmailStr | None = None
    logo_url: str | None = Field(None, max_length=500)
    status: str = Field(default="active")


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    tax_number: str | None = Field(None, min_length=10, max_length=50)
    tax_office: str | None = Field(None, min_length=2, max_length=100)
    address: str | None = Field(None, max_length=500)
    phone: str | None = Field(None, max_length=20)
    email: EmailStr | None = None
    logo_url: str | None = Field(None, max_length=500)
    status: str | None = None


class OrganizationResponse(OrganizationBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    class Config:
        from_attributes = True
