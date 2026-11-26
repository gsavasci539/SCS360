"""Durable delivery history; retry queues work without claiming delivery."""
from datetime import UTC, datetime

from sqlalchemy import func, or_, select, update

from app.core.exceptions import ConflictException, NotFoundException
from app.infrastructure.models.models import NotificationJob, NotificationRecipient, NotificationStatus
from app.infrastructure.repositories.base import BaseRepository


def scoped(tenant, branch_id=None):
    repo = BaseRepository(None, tenant)
    query = repo._branch_filter(repo._org_filter(
        select(NotificationRecipient, NotificationJob).join(NotificationJob,
            NotificationJob.id == NotificationRecipient.notification_job_id), NotificationJob), NotificationJob)
    # Branchless outbox rows may contain all-organization recipients; do not
    # treat them as readable by every branch-scoped operator.
    if tenant.branch_ids:
        query = query.where(NotificationJob.branch_id.in_(tenant.branch_ids))
    return query.where(NotificationJob.branch_id == branch_id) if branch_id else query


def serialize(recipient, job):
    return {"id": str(recipient.id), "job_id": str(job.id), "recipient": recipient.recipient_address,
        "branch_id": str(job.branch_id) if job.branch_id else None,
        "recipient_name": recipient.recipient_name, "subject": job.subject, "type": job.channel.value,
        "channel": job.channel.value, "message": "Şifre sıfırlama e-postası" if job.reference_type == "PASSWORD_RESET" else job.body,
        "status": recipient.status.value,
        "sent_at": recipient.sent_at.isoformat() if recipient.sent_at else None,
        "scheduled_at": job.scheduled_at.isoformat(), "created_at": job.created_at.isoformat(),
        "error_message": recipient.error_message, "retry_count": job.retry_count}


def filtered(tenant, channel, status, search, branch_id):
    query = scoped(tenant, branch_id)
    if channel:
        query = query.where(NotificationJob.channel == channel)
    if status:
        query = query.where(NotificationRecipient.status == status)
    if search:
        query = query.where(or_(NotificationRecipient.recipient_address.ilike(f"%{search}%"),
            NotificationRecipient.recipient_name.ilike(f"%{search}%"), NotificationJob.subject.ilike(f"%{search}%")))
    return query


async def records(db, tenant, channel=None, status=None, search=None, *, branch_id=None, limit=None, offset=0):
    query = filtered(tenant, channel, status, search, branch_id)
    rows = (await db.execute(query.order_by(NotificationRecipient.created_at.desc(), NotificationRecipient.id)
        .limit(limit).offset(offset))).all()
    return [serialize(*row) for row in rows]


async def count(db, tenant, channel, status, search, branch_id):
    query = filtered(tenant, channel, status, search, branch_id)
    return int(await db.scalar(select(func.count()).select_from(query.with_only_columns(NotificationRecipient.id).subquery())))


async def get(db, tenant, identifier, branch_id=None):
    row = (await db.execute(scoped(tenant, branch_id).where(NotificationRecipient.id == identifier)
        .execution_options(populate_existing=True))).one_or_none()
    if row is None:
        raise NotFoundException("Gönderim kaydı bulunamadı")
    return row


async def lock_ready(db, tenant, identifier, branch_id):
    recipient, job = await get(db, tenant, identifier, branch_id)
    locked = await db.execute(update(NotificationJob).where(NotificationJob.id == job.id,
        or_(NotificationJob.locked_until.is_(None), NotificationJob.locked_until <= datetime.now(UTC)))
        .values(status=NotificationJob.status).execution_options(synchronize_session=False))
    if locked.rowcount != 1:
        raise ConflictException("Gönderim şu anda işleniyor")
    return await get(db, tenant, identifier, branch_id)


async def retry(db, tenant, identifier, branch_id=None):
    recipient, job = await lock_ready(db, tenant, identifier, branch_id)
    if recipient.status == NotificationStatus.SENT:
        raise ConflictException("Gönderilmiş ileti yeniden kuyruğa alınamaz")
    recipient.status, recipient.error_message = NotificationStatus.PENDING, None
    job.status, job.retry_count = NotificationStatus.PENDING, 0
    job.scheduled_at, job.processed_at = datetime.now(UTC), None
    await db.flush()
    return serialize(recipient, job)


async def remove(db, tenant, identifier, branch_id=None):
    recipient, _ = await lock_ready(db, tenant, identifier, branch_id)
    await db.delete(recipient)
