from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, EmailStr


class BranchBase(BaseModel):
    organization_id: UUID
    name: str = Field(..., min_length=2, max_length=255)
    code: str = Field(..., min_length=2, max_length=50)
    address: str | None = Field(None, max_length=500)
    phone: str | None = Field(None, max_length=20)
    email: EmailStr | None = None
    capacity: int | None = Field(None, gt=0)
    status: str = Field(default="active")


class BranchCreate(BranchBase):
    pass


class BranchUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    code: str | None = Field(None, min_length=2, max_length=50)
    address: str | None = Field(None, max_length=500)
    phone: str | None = Field(None, max_length=20)
    email: EmailStr | None = None
    capacity: int | None = Field(None, gt=0)
    status: str | None = None


class BranchResponse(BranchBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    class Config:
        from_attributes = True
