from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class ClassBase(BaseModel):
    organization_id: UUID
    branch_id: UUID
    name: str = Field(..., min_length=2, max_length=255)
    code: str = Field(..., min_length=2, max_length=50)
    capacity: int | None = Field(None, gt=0)
    teacher_id: UUID | None = None
    academic_year: str | None = Field(None, max_length=20)
    status: str = Field(default="active")


class ClassCreate(ClassBase):
    pass


class ClassUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    code: str | None = Field(None, min_length=2, max_length=50)
    capacity: int | None = Field(None, gt=0)
    teacher_id: UUID | None = None
    academic_year: str | None = Field(None, max_length=20)
    status: str | None = None


class ClassResponse(ClassBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    class Config:
        from_attributes = True
