"""Durable delivery history; retry queues work without claiming delivery."""
from datetime import UTC, datetime

from sqlalchemy import or_, select

from app.core.exceptions import ConflictException, NotFoundException
from app.infrastructure.models.models import NotificationJob, NotificationRecipient, NotificationStatus
from app.infrastructure.repositories.base import BaseRepository


def scoped(tenant):
    repo = BaseRepository(None, tenant)
    return repo._branch_filter(repo._org_filter(
        select(NotificationRecipient, NotificationJob).join(NotificationJob,
            NotificationJob.id == NotificationRecipient.notification_job_id), NotificationJob), NotificationJob)


def serialize(recipient, job):
    return {"id": str(recipient.id), "job_id": str(job.id), "recipient": recipient.recipient_address,
        "recipient_name": recipient.recipient_name, "subject": job.subject, "type": job.channel.value,
        "channel": job.channel.value, "message": "Şifre sıfırlama e-postası" if job.reference_type == "PASSWORD_RESET" else job.body,
        "status": recipient.status.value,
        "sent_at": recipient.sent_at.isoformat() if recipient.sent_at else None,
        "scheduled_at": job.scheduled_at.isoformat(), "created_at": job.created_at.isoformat(),
        "error_message": recipient.error_message, "retry_count": job.retry_count}


async def records(db, tenant, channel=None, status=None, search=None):
    query = scoped(tenant)
    if channel:
        query = query.where(NotificationJob.channel == channel)
    if status:
        query = query.where(NotificationRecipient.status == status)
    if search:
        query = query.where(or_(NotificationRecipient.recipient_address.ilike(f"%{search}%"),
            NotificationRecipient.recipient_name.ilike(f"%{search}%"), NotificationJob.subject.ilike(f"%{search}%")))
    rows = (await db.execute(query.order_by(NotificationRecipient.created_at.desc()))).all()
    return [serialize(*row) for row in rows]


async def get(db, tenant, identifier):
    row = (await db.execute(scoped(tenant).where(NotificationRecipient.id == identifier))).one_or_none()
    if row is None:
        raise NotFoundException("Gönderim kaydı bulunamadı")
    return row


async def retry(db, tenant, identifier):
    recipient, job = await get(db, tenant, identifier)
    if recipient.status == NotificationStatus.SENT:
        raise ConflictException("Gönderilmiş ileti yeniden kuyruğa alınamaz")
    if job.locked_until and job.locked_until.replace(tzinfo=UTC) > datetime.now(UTC):
        raise ConflictException("Gönderim şu anda işleniyor")
    recipient.status, recipient.error_message = NotificationStatus.PENDING, None
    job.status, job.retry_count = NotificationStatus.PENDING, 0
    job.scheduled_at, job.processed_at = datetime.now(UTC), None
    await db.flush()
    return serialize(recipient, job)
