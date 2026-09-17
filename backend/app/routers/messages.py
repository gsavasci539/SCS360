from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.permissions import PermissionChecker
from app.core.responses import success_response, paginate
from app.domain.entities.user import User
from app.domain.entities.chat_message import ChatMessage, ChatMessageCreate, ChatMessageUpdate
from app.core.tenant import TenantContext

router = APIRouter(prefix="/api/messages", tags=["Messages"])


def message_to_dict(message: ChatMessage) -> dict:
    return {
        "id": str(message.id),
        "sender_id": str(message.sender_id),
        "receiver_id": str(message.receiver_id),
        "class_id": str(message.class_id) if message.class_id else None,
        "content": message.content,
        "attachment_url": message.attachment_url,
        "is_read": message.is_read,
        "sent_at": message.sent_at.isoformat() if message.sent_at else None
    }


@router.get("/conversations")
async def get_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("messaging.read"))
):
    """Get user's conversations (list of people they've messaged)"""
    from app.infrastructure.models.models import ChatMessage as ChatMessageModel
    from app.infrastructure.models.models import User as UserModel
    
    # Get all unique conversation partners
    result = await db.execute(
        select(ChatMessageModel.sender_id, ChatMessageModel.receiver_id)
        .where(
            or_(
                ChatMessageModel.sender_id == current_user.id,
                ChatMessageModel.receiver_id == current_user.id
            )
        )
        .distinct()
    )
    
    conversations = result.all()
    partner_ids = set()
    for sender_id, receiver_id in conversations:
        if sender_id != current_user.id:
            partner_ids.add(sender_id)
        if receiver_id != current_user.id:
            partner_ids.add(receiver_id)
    
    # Get user details for each partner
    partners = []
    if partner_ids:
        result = await db.execute(
            select(UserModel).where(UserModel.id.in_(partner_ids))
        )
        users = result.scalars().all()
        
        for user in users:
            # Get last message with this user
            last_message_result = await db.execute(
                select(ChatMessageModel)
                .where(
                    or_(
                        and_(
                            ChatMessageModel.sender_id == current_user.id,
                            ChatMessageModel.receiver_id == user.id
                        ),
                        and_(
                            ChatMessageModel.sender_id == user.id,
                            ChatMessageModel.receiver_id == current_user.id
                        )
                    )
                )
                .order_by(desc(ChatMessageModel.sent_at))
                .limit(1)
            )
            last_message = last_message_result.scalar_one_or_none()
            
            # Get unread count
            unread_result = await db.execute(
                select(ChatMessageModel)
                .where(
                    and_(
                        ChatMessageModel.sender_id == user.id,
                        ChatMessageModel.receiver_id == current_user.id,
                        ChatMessageModel.is_read == False
                    )
                )
            )
            unread_count = len(unread_result.scalars().all())
            
            partners.append({
                "user_id": str(user.id),
                "name": f"{user.first_name} {user.last_name}",
                "email": user.email,
                "last_message": message_to_dict(ChatMessage.model_validate(last_message)) if last_message else None,
                "unread_count": unread_count
            })
    
    return success_response(partners)


@router.get("/conversation/{partner_id}")
async def get_conversation_messages(
    partner_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    before_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("messaging.read"))
):
    """Get messages between current user and a specific partner"""
    from app.infrastructure.models.models import ChatMessage as ChatMessageModel
    
    query = select(ChatMessageModel).where(
        or_(
            and_(
                ChatMessageModel.sender_id == current_user.id,
                ChatMessageModel.receiver_id == partner_id
            ),
            and_(
                ChatMessageModel.sender_id == partner_id,
                ChatMessageModel.receiver_id == current_user.id
            )
        )
    )
    
    if before_id:
        query = query.where(ChatMessageModel.id < before_id)
    
    query = query.order_by(desc(ChatMessageModel.sent_at)).limit(limit)
    
    result = await db.execute(query)
    messages = result.scalars().all()
    
    # Mark received messages as read
    received_messages = [m for m in messages if m.receiver_id == current_user.id and not m.is_read]
    for msg in received_messages:
        msg.is_read = True
    
    await db.commit()
    
    # Return in chronological order
    messages.reverse()
    
    return success_response([message_to_dict(ChatMessage.model_validate(m)) for m in messages])


@router.post("/send")
async def send_message(
    message: ChatMessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("messaging.send"))
):
    """Send a message to another user"""
    from app.infrastructure.models.models import ChatMessage as ChatMessageModel
    
    new_message = ChatMessageModel(
        sender_id=current_user.id,
        receiver_id=message.receiver_id,
        class_id=message.class_id,
        content=message.content,
        attachment_url=message.attachment_url,
        is_read=False,
        sent_at=datetime.now()
    )
    
    db.add(new_message)
    await db.commit()
    await db.refresh(new_message)
    
    return success_response(message_to_dict(ChatMessage.model_validate(new_message)), "Message sent")


@router.put("/{message_id}/read")
async def mark_message_read(
    message_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("messaging.read"))
):
    """Mark a message as read"""
    from app.infrastructure.models.models import ChatMessage as ChatMessageModel
    
    result = await db.execute(
        select(ChatMessageModel).where(ChatMessageModel.id == message_id)
    )
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    if message.receiver_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only mark messages sent to you as read")
    
    message.is_read = True
    await db.commit()
    
    return success_response(message_to_dict(ChatMessage.model_validate(message)), "Message marked as read")


@router.delete("/{message_id}")
async def delete_message(
    message_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("messaging.write"))
):
    """Delete a message"""
    from app.infrastructure.models.models import ChatMessage as ChatMessageModel
    
    result = await db.execute(
        select(ChatMessageModel).where(ChatMessageModel.id == message_id)
    )
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    if message.sender_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own messages")
    
    await db.delete(message)
    await db.commit()
    
    return success_response({"message": "Message deleted successfully"})


@router.post("/conversation/{partner_id}/mark-all-read")
async def mark_conversation_read(
    partner_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("messaging.read"))
):
    """Mark all messages from a partner as read"""
    from app.infrastructure.models.models import ChatMessage as ChatMessageModel
    
    result = await db.execute(
        select(ChatMessageModel).where(
            and_(
                ChatMessageModel.sender_id == partner_id,
                ChatMessageModel.receiver_id == current_user.id,
                ChatMessageModel.is_read == False
            )
        )
    )
    messages = result.scalars().all()
    
    marked_count = 0
    for msg in messages:
        msg.is_read = True
        marked_count += 1
    
    await db.commit()
    
    return success_response({
        "marked_count": marked_count,
        "partner_id": str(partner_id)
    }, f"{marked_count} mesaj okundu olarak işaretlendi")