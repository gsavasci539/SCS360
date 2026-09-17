from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class AnnouncementBase(BaseModel):
    organization_id: UUID
    branch_id: UUID | None = None
    title: str = Field(..., min_length=2, max_length=255)
    content: str = Field(..., min_length=10)
    audience: str = Field(..., min_length=2, max_length=50)
    channels: str = Field(..., min_length=2, max_length=100)
    scheduled_for: datetime | None = None
    status: str = Field(default="draft")


class AnnouncementCreate(AnnouncementBase):
    pass


class AnnouncementUpdate(BaseModel):
    title: str | None = Field(None, min_length=2, max_length=255)
    content: str | None = Field(None, min_length=10)
    audience: str | None = Field(None, min_length=2, max_length=50)
    channels: str | None = Field(None, min_length=2, max_length=100)
    scheduled_for: datetime | None = None
    status: str | None = None


class AnnouncementResponse(AnnouncementBase):
    id: UUID
    sent_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    class Config:
        from_attributes = True
