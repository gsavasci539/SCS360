from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.permissions import PermissionChecker
from app.core.responses import success_response, paginate
from app.domain.entities.user import User
from app.core.tenant import TenantContext

router = APIRouter(prefix="/api/outbox", tags=["Outbox"])


class OutboxMessage(BaseModel):
    id: UUID
    recipient: str
    subject: str
    type: str
    sent_at: datetime
    status: str


# In-memory storage for outbox messages (temporary solution)
outbox_storage = [
    {
        "id": UUID("123e4567-e89b-12d3-a456-426614174000"),
        "recipient": "veli@example.com",
        "subject": "Öğrenci Devamsızlık Bildirimi",
        "type": "E-posta",
        "sent_at": datetime.now(),
        "status": "Gönderildi"
    },
    {
        "id": UUID("123e4567-e89b-12d3-a456-426614174001"),
        "recipient": "+905551234567",
        "subject": "Ödeme Hatırlatma",
        "type": "SMS",
        "sent_at": datetime.now(),
        "status": "Gönderildi"
    }
]


def message_to_dict(message: dict) -> dict:
    return {
        "id": str(message.get("id")),
        "recipient": message.get("recipient"),
        "subject": message.get("subject"),
        "type": message.get("type"),
        "sent_at": message.get("sent_at").isoformat() if message.get("sent_at") else None,
        "status": message.get("status")
    }


@router.get("/")
async def list_outbox_messages(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("student.read"))
):
    """List outbox messages with pagination"""
    filtered_messages = outbox_storage
    
    if search:
        search_lower = search.lower()
        filtered_messages = [
            m for m in outbox_storage
            if search_lower in m.get("recipient", "").lower()
            or search_lower in m.get("subject", "").lower()
            or search_lower in m.get("type", "").lower()
        ]
    
    total = len(filtered_messages)
    start = (page - 1) * page_size
    end = start + page_size
    paginated_messages = filtered_messages[start:end]
    
    return paginate(
        [message_to_dict(m) for m in paginated_messages],
        total,
        page,
        page_size
    )


@router.get("/{message_id}")
async def get_outbox_message(
    message_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("student.read"))
):
    """Get a specific outbox message"""
    message = next((m for m in outbox_storage if m.get("id") == message_id), None)
    if not message:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Outbox message not found")
    
    return success_response(message_to_dict(message))


@router.delete("/{message_id}")
async def delete_outbox_message(
    message_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("notification.write"))
):
    """Delete an outbox message"""
    global outbox_storage
    message = next((m for m in outbox_storage if m.get("id") == message_id), None)
    if not message:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Outbox message not found")
    
    outbox_storage = [m for m in outbox_storage if m.get("id") != message_id]
    return success_response({"message": "Outbox message deleted successfully"})
