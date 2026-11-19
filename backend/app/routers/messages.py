from __future__ import annotations
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, case, or_, func
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
from app.application.services.message_contacts import message_branches, recipient_query, require_recipient
from app.application.services.message_history import message_partner, message_visibility
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
    visible = await message_visibility(db, tenant, branch_id)
    message = await db.scalar(select(ChatMessageModel).where(
        visible, ChatMessageModel.id == message_id, ChatMessageModel.sender_id == tenant.user_id,
    ))
    if message is None:
        raise NotFoundException("Gönderilen mesaj bulunamadı")
    return success_response(message_to_dict(ChatMessage.model_validate(message)))


@router.get("/conversations")
async def get_conversations(
    branch_id: UUID | None = None,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("messaging.read"))
):
    visible = await message_visibility(db, tenant, branch_id)
    messages, users = ChatMessageModel.__table__, UserModel.__table__
    partner = message_partner(tenant.user_id)
    incoming = and_(messages.c.recipient_id == tenant.user_id, messages.c.is_read.is_(False))
    ranked = select(
        messages, partner.label("partner_id"),
        func.row_number().over(partition_by=partner, order_by=(messages.c.sent_at.desc(), messages.c.id.desc())).label("rank"),
        func.sum(case((incoming, 1), else_=0)).over(partition_by=partner).label("unread_count"),
    ).where(visible).subquery()
    result = await db.execute(select(ranked, users.c.first_name, users.c.last_name, users.c.email)
        .join(users, users.c.id == ranked.c.partner_id).where(ranked.c.rank == 1)
        .order_by(ranked.c.sent_at.desc(), ranked.c.id.desc()))
    return success_response([
        {"user_id": str(row.partner_id), "name": f"{row.first_name} {row.last_name}",
         "email": row.email, "last_message": message_to_dict(ChatMessage.model_validate(row._mapping)),
         "unread_count": row.unread_count}
        for row in result
    ])


@router.get("/conversation/{partner_id}")
async def get_conversation_messages(
    partner_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    before_id: Optional[UUID] = None,
    branch_id: UUID | None = None,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("messaging.read"))
):
    """Get messages between current user and a specific partner"""
    visible = await message_visibility(db, tenant, branch_id)
    query = select(ChatMessageModel).where(visible, message_partner(tenant.user_id) == partner_id)
    
    if before_id:
        before = await db.scalar(query.where(ChatMessageModel.id == before_id))
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
    received_messages = [m for m in messages if m.recipient_id == tenant.user_id and not m.is_read]
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
    branches = await message_branches(db, tenant, message.branch_id)
    branch_id = message.branch_id
    if not message.content.strip() or len(message.content) > 10000:
        raise ValidationException("Mesaj 1–10000 karakter olmalı")
    if message.class_id:
        classroom = await repo.get_by_id(message.class_id, ClassRoom)
        if branch_id and classroom.branch_id != branch_id:
            raise ForbiddenException("Sınıf seçilen şubeye bağlı değil")
        branch_id = classroom.branch_id
    conversation = None
    if message.conversation_id:
        conversation = await repo.get_by_id(message.conversation_id, ChatConversation, for_update=True)
        if {sender_id, message.recipient_id} != {conversation.parent_id, conversation.teacher_id}:
            raise ForbiddenException("Görüşme katılımcıları eşleşmiyor")
        student = await repo.get_by_id(conversation.student_id, Student)
        await require_student_access(db, tenant, student.id)
        if branch_id and student.branch_id != branch_id:
            raise ForbiddenException("Görüşme seçilen şubeye bağlı değil")
        branch_id = student.branch_id
    if branch_id is None and len(branches) == 1:
        branch_id = branches[0]
    await require_recipient(db, tenant, message.recipient_id, branch_id)

    def replay(row):
        if (row.sender_id, row.recipient_id, row.content, row.class_id, row.conversation_id, row.attachment_url) != (
            sender_id, message.recipient_id, message.content, message.class_id,
            message.conversation_id, message.attachment_url,
        ):
            raise ConflictException("İşlem kimliği farklı bir mesaj için kullanılmış")
        if row.organization_id not in {None, tenant.organization_id} or row.branch_id != branch_id:
            raise ConflictException("İşlem kimliği farklı bir mesaj kapsamı için kullanılmış")
        return success_response(message_to_dict(ChatMessage.model_validate(row)), "Mesaj kaydedildi")

    saved_query = None
    if message.request_id is not None:
        stored = ChatMessageModel.__table__
        # Check only the exact operation key. A collision in another scope
        # must still be rejected consistently without returning that row.
        saved_query = select(stored).where(stored.c.id == message.request_id)
        prior = (await db.execute(saved_query)).first()
        if prior:
            return replay(prior._mapping)
    sender_role = "TEACHER" if "teacher" in tenant.role_slugs else "PARENT" if "parent" in tenant.role_slugs else "STAFF"
    new_message = ChatMessageModel(
        organization_id=tenant.organization_id,
        branch_id=branch_id,
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
        if saved_query is not None:
            prior = (await db.execute(saved_query)).first()
            if prior:
                return replay(prior._mapping)
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
    branch_id: UUID | None = None,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("messaging.read"))
):
    """Mark a message as read"""
    visible = await message_visibility(db, tenant, branch_id)
    message = await db.scalar(select(ChatMessageModel).where(visible, ChatMessageModel.id == message_id))
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    if message.recipient_id != tenant.user_id:
        raise HTTPException(status_code=403, detail="You can only mark messages sent to you as read")
    
    message.is_read = True
    await db.commit()
    
    return success_response(message_to_dict(ChatMessage.model_validate(message)), "Message marked as read")


@router.delete("/{message_id}")
async def delete_message(
    message_id: UUID,
    branch_id: UUID | None = None,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("messaging.write"))
):
    """Delete a message"""
    visible = await message_visibility(db, tenant, branch_id)
    message = await db.scalar(select(ChatMessageModel).where(visible, ChatMessageModel.id == message_id))
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    if message.sender_id != tenant.user_id:
        raise HTTPException(status_code=403, detail="You can only delete your own messages")
    
    await db.delete(message)
    await db.commit()
    
    return success_response({"message": "Message deleted successfully"})


@router.post("/conversation/{partner_id}/mark-all-read")
async def mark_conversation_read(
    partner_id: UUID,
    branch_id: UUID | None = None,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("messaging.read"))
):
    """Mark all messages from a partner as read"""
    visible = await message_visibility(db, tenant, branch_id)
    result = await db.execute(
        select(ChatMessageModel).where(
            visible, ChatMessageModel.sender_id == partner_id,
            ChatMessageModel.recipient_id == tenant.user_id, ChatMessageModel.is_read.is_(False),
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
