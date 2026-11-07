"""Pydantic schemas for chatbot intent detection."""

from datetime import date as date_type
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ChatbotIntent(BaseModel):
    """Structured intent output from LLM."""
    
    intent: str = Field(
        description="The detected intent category",
        examples=["ATTENDANCE", "GRADES", "PAYMENTS", "GENERAL"]
    )
    
    student_id: Optional[str] = Field(
        default=None,
        description="Student ID if explicitly mentioned (only if user provides it)",
        examples=["123e4567-e89b-12d3-a456-426614174000"]
    )
    
    teacher_id: Optional[str] = Field(
        default=None,
        description="Teacher ID if explicitly mentioned",
        examples=["123e4567-e89b-12d3-a456-426614174000"]
    )
    
    subject: Optional[str] = Field(
        default=None,
        description="Subject if relevant (e.g., 'matematik', 'türkçe')",
        examples=["matematik", "türkçe", "fen"]
    )
    
    period: Optional[str] = Field(
        default=None,
        description="Time period (today, this_week, this_month, last_month, etc.)",
        examples=["today", "this_week", "this_month", "last_month"]
    )
    
    operation: Optional[str] = Field(
        default=None,
        description="Specific operation (status, list, summary, etc.)",
        examples=["status", "list", "summary", "count"]
    )
    
    search_text: Optional[str] = Field(
        default=None,
        description="Any search text or name mentioned",
        examples=["Ahmet", "Ali"]
    )
    
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence score for intent detection"
    )


class DateRange(BaseModel):
    """Date range for queries."""
    
    start_date: date_type
    end_date: date_type
    description: str


class ResolvedIntent(BaseModel):
    """Fully resolved intent with backend-validated entities."""
    
    intent: str
    student_id: Optional[UUID] = None
    teacher_id: Optional[UUID] = None
    subject: Optional[str] = None
    date_range: Optional[DateRange] = None
    operation: Optional[str] = None
    search_text: Optional[str] = None
    confidence: float = 0.5
    raw_intent: ChatbotIntent


class ChatbotContext(BaseModel):
    """Context for chatbot intent resolution."""
    
    user_id: UUID
    organization_id: Optional[UUID] = None
    role: str
    accessible_students: list[dict] = Field(default_factory=list)
    accessible_teachers: list[dict] = Field(default_factory=list)
    current_date: date_type
    conversation_history: list[dict] = Field(default_factory=list)
