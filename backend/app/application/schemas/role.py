from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class RoleBase(BaseModel):
    organization_id: UUID | None = None
    name: str = Field(..., min_length=2, max_length=100)
    description: str | None = Field(None, max_length=500)
    is_system: bool = False


class RoleCreate(RoleBase):
    pass


class RoleUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=100)
    description: str | None = Field(None, max_length=500)


class RoleResponse(RoleBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
