from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ChatConversation(BaseModel):
    id: UUID
    student_id: UUID
    parent_id: UUID
    teacher_id: UUID
    subject_context: str
    last_message: Optional[str] = None
    last_message_at: Optional[datetime] = None
    parent_unread_count: int = 0
    teacher_unread_count: int = 0
    created_via: str = "CHATBOT"
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatConversationCreate(BaseModel):
    student_id: UUID
    teacher_id: UUID
    teacher_name: str
    initial_message: str
    created_via: str = "CHATBOT"


class ChatConversationResponse(BaseModel):
    success: bool
    conversation_id: UUID
    participant_name: str
    participant_role: str
    last_message: str
    last_message_time: str
    status: str
