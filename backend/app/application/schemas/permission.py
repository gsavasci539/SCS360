from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class PermissionResponse(BaseModel):
    id: UUID
    name: str = Field(..., min_length=2, max_length=100)
    description: str | None = Field(None, max_length=500)
    module: str = Field(..., min_length=2, max_length=50)
    created_at: datetime

    class Config:
        from_attributes = True
