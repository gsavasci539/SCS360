from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class NotificationJobResponse(BaseModel):
    id: UUID
    organization_id: UUID
    channel: str
    recipient_type: str
    recipient_id: UUID
    subject: str | None
    body: str
    status: str
    scheduled_for: datetime | None
    sent_at: datetime | None
    failed_at: datetime | None
    error_message: str | None
    retry_count: int
    max_retries: int
    provider_response: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
