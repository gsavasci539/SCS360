from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ChatMessage(BaseModel):
    id: UUID
    conversation_id: Optional[UUID] = None
    sender_id: UUID
    sender_role: Optional[str] = None  # 'PARENT', 'TEACHER', 'SYSTEM'
    recipient_id: UUID
    class_id: Optional[UUID] = None
    content: str
    attachment_url: Optional[str] = None
    is_read: bool = False
    sent_at: datetime

    class Config:
        from_attributes = True


class ChatMessageCreate(BaseModel):
    conversation_id: Optional[UUID] = None
    recipient_id: UUID
    class_id: Optional[UUID] = None
    content: str
    attachment_url: Optional[str] = None


class ChatMessageUpdate(BaseModel):
    is_read: Optional[bool] = None