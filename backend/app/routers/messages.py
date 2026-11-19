from __future__ import annotations
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.exc import IntegrityError
from collections import defaultdict
from typing import Optional
from uuid import UUID
from datetime import UTC, datetime

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.permissions import PermissionChecker
from app.core.responses import success_response, paginate
from app.domain.entities.user import User
from app.domain.entities.chat_message import ChatMessage, ChatMessageCreate
from app.core.tenant import TenantContext
from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException, ValidationException
from app.core.student_access import require_student_access
from app.application.services.message_contacts import recipient_query, require_recipient
from app.infrastructure.models.models import ChatMessage as ChatMessageModel, User as UserModel, Role, UserRole

router = APIRouter(prefix="/api/messages", tags=["Messages"])


def message_to_dict(message: ChatMessage) -> dict:
    return {
        "id": str(message.id),
        "conversation_id": str(message.conversation_id) if message.conversation_id else None,
        "sender_id": str(message.sender_id),
        "sender_role": message.sender_role,
        "recipient_id": str(message.recipient_id),
        "class_id": str(message.class_id) if message.class_id else None,
        "content": message.content,
        "attachment_url": message.attachment_url,
        "is_read": message.is_read,
        "sent_at": message.sent_at.isoformat() if message.sent_at else None
    }


@router.get("/recipients")
async def list_message_recipients(
    branch_id: UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("messaging.send")),
):
    query = await recipient_query(db, tenant, branch_id)
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    users = UserModel.__table__.c
    rows = (await db.execute(query.order_by(users.first_name, users.last_name, users.id)
                            .offset((page - 1) * page_size).limit(page_size))).all()
    roles, links = Role.__table__.c, UserRole.__table__.c
    names = defaultdict(list)
    if rows:
        result = await db.execute(select(links.user_id, roles.name)
            .join(Role.__table__, roles.id == links.role_id).where(
                links.user_id.in_([row.id for row in rows]), roles.deleted_at.is_(None),
                or_(roles.organization_id.is_(None), roles.organization_id == tenant.organization_id),
            ).order_by(roles.name, roles.id))
        for user_id, name in result:
            names[user_id].append(name)
    return success_response(paginate([
        {"id": str(user.id), "name": f"{user.first_name} {user.last_name}",
         "roles": names[user.id]}
        for user in rows
    ], total or 0, page, page_size))


@router.get("/sent/{message_id}")
async def get_sent_message(
    message_id: UUID,
    branch_id: UUID | None = None,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("messaging.send")),
):
    message = await db.scalar(select(ChatMessageModel).where(
        ChatMessageModel.id == message_id, ChatMessageModel.sender_id == tenant.user_id,
    ))
    if message is None:
        raise NotFoundException("Gönderilen mesaj bulunamadı")
    await require_recipient(db, tenant, message.recipient_id, branch_id)
    return success_response(message_to_dict(ChatMessage.model_validate(message)))


@router.get("/conversations")
async def get_conversations(
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("messaging.read"))
):
    """Get user's conversations (list of people they've messaged)"""
    from app.infrastructure.models.models import ChatMessage as ChatMessageModel
    from app.infrastructure.models.models import User as UserModel
    
    # Get all unique conversation partners
    result = await db.execute(
        select(ChatMessageModel.sender_id, ChatMessageModel.recipient_id)
        .where(
            or_(
                ChatMessageModel.sender_id == current_user.id,
                ChatMessageModel.recipient_id == current_user.id
            )
        )
        .distinct()
    )
    
    conversations = result.all()
    partner_ids = set()
    for sender_id, recipient_id in conversations:
        if sender_id != current_user.id:
            partner_ids.add(sender_id)
        if recipient_id != current_user.id:
            partner_ids.add(recipient_id)
    
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
                            ChatMessageModel.recipient_id == user.id
                        ),
                        and_(
                            ChatMessageModel.sender_id == user.id,
                            ChatMessageModel.recipient_id == current_user.id
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
                        ChatMessageModel.recipient_id == current_user.id,
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
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("messaging.read"))
):
    """Get messages between current user and a specific partner"""
    from app.infrastructure.models.models import ChatMessage as ChatMessageModel
    
    participants = or_(
        and_(ChatMessageModel.sender_id == current_user.id, ChatMessageModel.recipient_id == partner_id),
        and_(ChatMessageModel.sender_id == partner_id, ChatMessageModel.recipient_id == current_user.id),
    )
    query = select(ChatMessageModel).where(participants)
    
    if before_id:
        before = await db.scalar(select(ChatMessageModel).where(participants, ChatMessageModel.id == before_id))
        if before is None:
            raise HTTPException(status_code=404, detail="Mesaj bulunamadı")
        query = query.where(or_(
            ChatMessageModel.sent_at < before.sent_at,
            and_(ChatMessageModel.sent_at == before.sent_at, ChatMessageModel.id < before.id),
        ))
    
    query = query.order_by(ChatMessageModel.sent_at.desc(), ChatMessageModel.id.desc()).limit(limit)
    
    result = await db.execute(query)
    messages = result.scalars().all()
    
    # Mark received messages as read
    received_messages = [m for m in messages if m.recipient_id == current_user.id and not m.is_read]
    for msg in received_messages:
        msg.is_read = True
    
    await db.commit()
    
    # Return in chronological order
    messages.reverse()
    
    return success_response([message_to_dict(ChatMessage.model_validate(m)) for m in messages])


@router.post("/send")
async def send_message(
    message: ChatMessageCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("messaging.send"))
):
    """Send a message to another user"""
    from app.infrastructure.models.models import ChatConversation, ClassRoom, Student
    from app.infrastructure.repositories.base import BaseRepository
    repo = BaseRepository(db, tenant)
    sender_id = current_user.id
    await require_recipient(db, tenant, message.recipient_id, message.branch_id)
    if not message.content.strip() or len(message.content) > 10000:
        raise ValidationException("Mesaj 1–10000 karakter olmalı")
    if message.class_id:
        classroom = await repo.get_by_id(message.class_id, ClassRoom)
        if message.branch_id and classroom.branch_id != message.branch_id:
            raise ForbiddenException("Sınıf seçilen şubeye bağlı değil")
    conversation = None
    if message.conversation_id:
        conversation = await repo.get_by_id(message.conversation_id, ChatConversation, for_update=True)
        if {sender_id, message.recipient_id} != {conversation.parent_id, conversation.teacher_id}:
            raise ForbiddenException("Görüşme katılımcıları eşleşmiyor")
        student = await repo.get_by_id(conversation.student_id, Student)
        await require_student_access(db, tenant, student.id)
        if message.branch_id and student.branch_id != message.branch_id:
            raise ForbiddenException("Görüşme seçilen şubeye bağlı değil")

    def replay(row):
        if (row.sender_id, row.recipient_id, row.content, row.class_id, row.conversation_id, row.attachment_url) != (
            sender_id, message.recipient_id, message.content, message.class_id,
            message.conversation_id, message.attachment_url,
        ):
            raise ConflictException("İşlem kimliği farklı bir mesaj için kullanılmış")
        return success_response(message_to_dict(ChatMessage.model_validate(row)), "Mesaj kaydedildi")

    if message.request_id is not None:
        prior = await db.get(ChatMessageModel, message.request_id)
        if prior:
            return replay(prior)
    sender_role = "TEACHER" if "teacher" in tenant.role_slugs else "PARENT" if "parent" in tenant.role_slugs else "STAFF"
    new_message = ChatMessageModel(
        conversation_id=message.conversation_id,
        sender_id=sender_id,
        sender_role=sender_role,
        recipient_id=message.recipient_id,
        class_id=message.class_id,
        content=message.content,
        attachment_url=message.attachment_url,
        is_read=False,
        sent_at=datetime.now(UTC)
    )
    if message.request_id is not None:
        new_message.id = message.request_id
    db.add(new_message)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        if message.request_id is not None:
            prior = await db.get(ChatMessageModel, message.request_id)
            if prior:
                return replay(prior)
        raise
    if conversation:
        conversation.last_message = message.content
        conversation.last_message_at = new_message.sent_at
        if sender_id == conversation.teacher_id:
            conversation.parent_unread_count = (conversation.parent_unread_count or 0) + 1
        else:
            conversation.teacher_unread_count = (conversation.teacher_unread_count or 0) + 1
    await db.commit()
    await db.refresh(new_message)
    
    return success_response(message_to_dict(ChatMessage.model_validate(new_message)), "Mesaj kaydedildi")


@router.put("/{message_id}/read")
async def mark_message_read(
    message_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
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
    
    if message.recipient_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only mark messages sent to you as read")
    
    message.is_read = True
    await db.commit()
    
    return success_response(message_to_dict(ChatMessage.model_validate(message)), "Message marked as read")


@router.delete("/{message_id}")
async def delete_message(
    message_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
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
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("messaging.read"))
):
    """Mark all messages from a partner as read"""
    from app.infrastructure.models.models import ChatMessage as ChatMessageModel
    
    result = await db.execute(
        select(ChatMessageModel).where(
            and_(
                ChatMessageModel.sender_id == partner_id,
                ChatMessageModel.recipient_id == current_user.id,
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
