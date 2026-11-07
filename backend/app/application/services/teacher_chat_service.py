"""Teacher replies use the same student/parent conversation as the parent portal."""
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.exceptions import ForbiddenException, NotFoundException, ValidationException
from app.core.student_access import require_teacher_for_student, uses_relationship_scope
from app.infrastructure.models.models import ChatConversation, ChatMessage, Parent, Student, StudentParent, User
from app.infrastructure.repositories.base import BaseRepository


async def participants(db, tenant, student_id, parent_id=None):
    student = await BaseRepository(db, tenant).get_by_id(student_id, Student)
    if uses_relationship_scope(tenant):
        await require_teacher_for_student(db, student, tenant.user_id)
    query = select(Parent, StudentParent).join(StudentParent, StudentParent.parent_id == Parent.id).where(
        StudentParent.student_id == student.id, Parent.organization_id == student.organization_id,
        Parent.deleted_at.is_(None), Parent.user_id.is_not(None))
    if parent_id:
        query = query.where(Parent.user_id == parent_id)
    row = (await db.execute(query.order_by(StudentParent.is_primary.desc(), Parent.id).limit(1))).first()
    if row is None:
        raise NotFoundException("Öğrenciye bağlı veli hesabı bulunamadı")
    parent = row[0]
    account = (await db.execute(select(User).where(User.id == parent.user_id,
        User.organization_id == student.organization_id, User.deleted_at.is_(None)))).scalar_one_or_none()
    if account is None:
        raise ForbiddenException("Veli hesabına erişilemiyor")
    return student, account


async def thread(db, tenant, student_id, parent_id=None, *, create=False):
    student, parent = await participants(db, tenant, student_id, parent_id)
    conversation = (await db.execute(select(ChatConversation).where(
        ChatConversation.student_id == student.id, ChatConversation.parent_id == parent.id,
        ChatConversation.teacher_id == tenant.user_id, ChatConversation.is_active.is_(True))
        .order_by(ChatConversation.created_at).limit(1))).scalar_one_or_none()
    if conversation is None and create:
        conversation = ChatConversation(student_id=student.id, parent_id=parent.id,
            teacher_id=tenant.user_id, subject_context="Veli-öğretmen iletişimi", created_via="DIRECT")
        db.add(conversation)
        await db.flush()
    return student, parent, conversation


async def history(db, tenant, student_id, parent_id=None):
    _, _, conversation = await thread(db, tenant, student_id, parent_id)
    if conversation is None:
        return []
    rows = (await db.execute(select(ChatMessage, User).join(User, User.id == ChatMessage.sender_id)
        .where(ChatMessage.conversation_id == conversation.id).order_by(ChatMessage.sent_at))).all()
    conversation.teacher_unread_count = 0
    for message, _ in rows:
        if message.recipient_id == tenant.user_id:
            message.is_read = True
    return [{"id": str(message.id), "sender_id": str(message.sender_id),
        "receiver_id": str(message.recipient_id), "content": message.content, "is_read": message.is_read,
        "sent_at": message.sent_at.isoformat(), "sender_name": f"{sender.first_name} {sender.last_name}",
        "is_current_user": message.sender_id == tenant.user_id} for message, sender in rows]


async def send(db, tenant, student_id, content, parent_id=None):
    content = content.strip()
    if not content or len(content) > 10000:
        raise ValidationException("Mesaj 1–10000 karakter olmalı")
    student, parent, conversation = await thread(db, tenant, student_id, parent_id, create=True)
    message = ChatMessage(conversation_id=conversation.id, sender_id=tenant.user_id,
        sender_role="TEACHER" if "teacher" in tenant.role_slugs else "STAFF",
        recipient_id=parent.id, class_id=student.class_id, content=content, is_read=False)
    db.add(message)
    conversation.last_message, conversation.last_message_at = content, datetime.now(UTC)
    conversation.parent_unread_count = (conversation.parent_unread_count or 0) + 1
    await db.flush()
    return {"id": str(message.id), "content": content, "sent_at": message.sent_at.isoformat()}
