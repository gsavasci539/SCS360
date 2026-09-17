from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class AttendanceBase(BaseModel):
    organization_id: UUID
    branch_id: UUID
    class_id: UUID
    student_id: UUID
    date: datetime
    status: str = Field(..., min_length=2, max_length=20)
    notes: str | None = Field(None, max_length=500)


class AttendanceCreate(AttendanceBase):
    pass


class AttendanceUpdate(BaseModel):
    status: str | None = Field(None, min_length=2, max_length=20)
    notes: str | None = Field(None, max_length=500)


class AttendanceResponse(AttendanceBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
