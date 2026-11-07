from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AiChatAuditLog(BaseModel):
    id: UUID
    session_id: str
    user_id: UUID
    organization_id: UUID
    user_query: str
    ai_response: str
    detected_intent: Optional[str] = None
    topic_category: Optional[str] = None
    sentiment: Literal["POSITIVE", "NEUTRAL", "QUESTION", "CRITICAL"] = "NEUTRAL"
    quality_rating: int = Field(default=0, ge=1, le=5)
    feedback_status: Literal["VERIFIED", "CORRECTED", "NEEDS_REVIEW"] = "NEEDS_REVIEW"
    corrected_response: Optional[str] = None
    token_count: int = 0
    latency_ms: int = 0
    is_fine_tuning_ready: bool = False
    meta_data: Optional[dict] = None
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AiChatAuditLogCreate(BaseModel):
    session_id: str
    user_id: UUID
    organization_id: UUID
    user_query: str
    ai_response: str
    detected_intent: Optional[str] = None
    topic_category: Optional[str] = None
    sentiment: Literal["POSITIVE", "NEUTRAL", "QUESTION", "CRITICAL"] = "NEUTRAL"
    token_count: int = 0
    latency_ms: int = 0
    meta_data: Optional[dict] = None


class AiChatAuditLogUpdate(BaseModel):
    quality_rating: Optional[int] = Field(default=None, ge=1, le=5)
    feedback_status: Optional[Literal["VERIFIED", "CORRECTED", "NEEDS_REVIEW"]] = None
    corrected_response: Optional[str] = None
    is_fine_tuning_ready: Optional[bool] = None


class FeedbackPayload(BaseModel):
    quality_rating: int = Field(ge=1, le=5)
    feedback_status: Literal["VERIFIED", "CORRECTED", "NEEDS_REVIEW"]
    corrected_response: Optional[str] = None
    is_fine_tuning_ready: bool = False


class AiChatAuditLogResponse(AiChatAuditLog):
    sender_name: Optional[str] = None
    sender_role: Optional[str] = None
    
    # Backward compatibility: expose meta_data as metadata
    @property
    def metadata(self):
        return self.meta_data


class AuditLogListResponse(BaseModel):
    success: bool
    logs: list[AiChatAuditLogResponse]
    total: int
    page: int
    page_size: int


class ExportFormat(str):
    JSONL = "jsonl"
    ALPACA = "alpaca"
    LLAMA = "llama"
    CSV = "csv"
