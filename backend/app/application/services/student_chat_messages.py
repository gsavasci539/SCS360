"""Persistence and private attachments for an authorized student conversation."""
from datetime import UTC, datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ConflictException, NotFoundException
from app.infrastructure.models.models import ChatMessage, Student
from app.infrastructure.storage.message_attachments import (
    message_attachment_response,
    save_message_attachment,
)


async def lock_student(db, student):
    # Serialize creation of the first conversation and subsequent sends for this student.
    if db.bind.dialect.name == "sqlite":
        # SQLite ignores FOR UPDATE. A no-op write acquires its transaction's writer lock.
        students = Student.__table__
        await db.execute(students.update().where(students.c.id == student.id)
            .values(updated_at=students.c.updated_at))
        return
    await db.execute(select(Student.id).where(Student.id == student.id).with_for_update())


def message_data(message, actor_id):
    return {
        "id": str(message.id), "message_id": str(message.id), "sender_id": str(message.sender_id),
        "receiver_id": str(message.recipient_id), "content": message.content, "is_read": message.is_read,
        "sent_at": message.sent_at.isoformat(), "is_current_user": message.sender_id == actor_id,
        "attachment_name": message.attachment_name, "attachment_sha256": message.attachment_sha256,
    }


async def record(db, student, thread, sender_id, sender_role, content, request_id=None, upload=None):
    is_parent = sender_role == "PARENT"
    recipient_id = thread.teacher_id if is_parent else thread.parent_id
    scope = (thread.id, sender_id, recipient_id, student.organization_id)
    name = upload.name if upload else None
    digest = upload.digest if upload else None

    def replay(saved):
        if (saved.conversation_id, saved.sender_id, saved.recipient_id, saved.organization_id) != scope or (
            saved.content, saved.attachment_name, saved.attachment_sha256
        ) != (content, name, digest):
            raise ConflictException("İşlem kimliği farklı bir mesaj için kullanılmış")
        return message_data(saved, sender_id)

    if request_id is not None:
        saved = await db.get(ChatMessage, request_id)
        if saved is not None:
            return replay(saved)

    message = ChatMessage(id=request_id, organization_id=student.organization_id, branch_id=student.branch_id,
        conversation_id=thread.id, sender_id=sender_id, sender_role=sender_role, recipient_id=recipient_id,
        class_id=student.class_id, content=content, attachment_name=name, attachment_sha256=digest, is_read=False)
    db.add(message)
    thread.last_message, thread.last_message_at = content or name, datetime.now(UTC)
    if is_parent:
        thread.teacher_unread_count = (thread.teacher_unread_count or 0) + 1
    else:
        thread.parent_unread_count = (thread.parent_unread_count or 0) + 1
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        saved = await db.get(ChatMessage, request_id) if request_id is not None else None
        if saved is None:
            raise
        return replay(saved)
    if upload is not None:
        await save_message_attachment(message.id, upload)
    return message_data(message, sender_id)


async def receipt(db, thread, actor_id, message_id):
    if thread is None:
        raise NotFoundException("Mesaj bulunamadı")
    partner_id = thread.teacher_id if actor_id == thread.parent_id else thread.parent_id
    message = await db.scalar(select(ChatMessage).where(ChatMessage.id == message_id,
        ChatMessage.conversation_id == thread.id, ChatMessage.sender_id == actor_id,
        ChatMessage.recipient_id == partner_id))
    if message is None:
        raise NotFoundException("Mesaj bulunamadı")
    return message_data(message, actor_id)


async def download(db, thread, message_id):
    if thread is None:
        raise NotFoundException("Mesaj eki bulunamadı")
    message = await db.scalar(select(ChatMessage).where(
        ChatMessage.id == message_id, ChatMessage.conversation_id == thread.id,
        or_(
            and_(ChatMessage.sender_id == thread.parent_id, ChatMessage.recipient_id == thread.teacher_id),
            and_(ChatMessage.sender_id == thread.teacher_id, ChatMessage.recipient_id == thread.parent_id),
        )))
    return message_attachment_response(message)
