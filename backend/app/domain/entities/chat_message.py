from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ChatMessage(BaseModel):
    id: UUID
    sender_id: UUID
    receiver_id: UUID
    class_id: Optional[UUID] = None
    content: str
    attachment_url: Optional[str] = None
    is_read: bool = False
    sent_at: datetime

    class Config:
        from_attributes = True


class ChatMessageCreate(BaseModel):
    receiver_id: UUID
    class_id: Optional[UUID] = None
    content: str
    attachment_url: Optional[str] = None


class ChatMessageUpdate(BaseModel):
    is_read: Optional[bool] = None