from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, EmailStr


class StudentBase(BaseModel):
    organization_id: UUID
    branch_id: UUID
    class_id: UUID | None = None
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=100)
    date_of_birth: datetime | None = None
    gender: str | None = Field(None, max_length=10)
    photo_url: str | None = Field(None, max_length=500)
    enrollment_date: datetime
    address: str | None = Field(None, max_length=500)
    notes: str | None = Field(None, max_length=1000)
    status: str = Field(default="active")


class StudentCreate(StudentBase):
    parent_ids: list[UUID] = []


class StudentUpdate(BaseModel):
    class_id: UUID | None = None
    first_name: str | None = Field(None, min_length=2, max_length=100)
    last_name: str | None = Field(None, min_length=2, max_length=100)
    date_of_birth: datetime | None = None
    gender: str | None = Field(None, max_length=10)
    photo_url: str | None = Field(None, max_length=500)
    address: str | None = Field(None, max_length=500)
    notes: str | None = Field(None, max_length=1000)
    status: str | None = None
    parent_ids: list[UUID] | None = None


class StudentResponse(StudentBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    class Config:
        from_attributes = True
