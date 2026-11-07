from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ChatAction(BaseModel):
    """Clickable action button for chatbot responses."""
    label: str
    action_tag: str


class ChatMessage(BaseModel):
    """Chat message model for frontend and backend communication."""
    id: str
    text: str
    is_user: bool
    timestamp: str
    sender_role: Literal["SUPERADMIN", "OWNER", "ADMIN", "MANAGER", "TEACHER", "FINANCE", "PARENT", "CANTEEN"]
    actions: Optional[list[ChatAction]] = None
    sentiment: Optional[Literal["POSITIVE", "NEUTRAL", "QUESTION", "CRITICAL"]] = None


class StudentTeacherAssignment(BaseModel):
    id: UUID
    student_id: UUID
    teacher_id: UUID
    subject_name: str
    is_primary_adviser: bool = False
    office_hours: Optional[str] = "08:30 - 17:30"
    academic_year: Optional[str] = "2025-2026"
    created_at: datetime

    class Config:
        from_attributes = True


class TeacherInfo(BaseModel):
    teacher_id: UUID
    full_name: str
    subject: str
    role_description: str
    avatar_color_hex: str
    is_online: bool
    office_hours: str


class StudentTeachersResponse(BaseModel):
    success: bool
    student_id: str
    student_name: str
    class_name: str
    teachers: list[TeacherInfo]


class ChatbotHistoryMessage(BaseModel):
    """A bounded, display-only turn supplied by the current browser session."""

    role: Literal["user", "assistant"]
    content: str = Field(max_length=2000)
    intent: Optional[str] = Field(default=None, max_length=64)


class ChatbotQueryRequest(BaseModel):
    query: str
    role: str
    student_id: Optional[str] = None
    conversation_history: list[ChatbotHistoryMessage] = Field(default_factory=list, max_length=6)


class ChatbotQueryResponse(BaseModel):
    success: bool
    intent: str
    response_markdown: str
    suggested_actions: list[dict]
