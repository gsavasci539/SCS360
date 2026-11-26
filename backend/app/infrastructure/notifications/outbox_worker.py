import asyncio
import logging
import re
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import or_, select, update
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.infrastructure.models.models import NotificationJob, NotificationStatus
from app.infrastructure.notifications.base import ProviderResult
from app.infrastructure.notifications.dispatcher import NotificationDispatcher

logger = logging.getLogger("scs360.worker")
dispatcher = NotificationDispatcher()
POLL_INTERVAL = 10
SAFE_PROVIDER_RESPONSE_KEYS = {"status", "code", "provider_id", "delivery_status"}
SAFE_PROVIDER_ERROR = "Bildirim sağlayıcısı isteği tamamlayamadı"
SAFE_PROVIDER_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")


def _safe_provider_response(response):
    """Persist only bounded delivery diagnostics, never an arbitrary provider payload."""
    if not isinstance(response, dict):
        return None
    safe = {}
    for key in SAFE_PROVIDER_RESPONSE_KEYS:
        value = response.get(key)
        if key == "status" and isinstance(value, int) and not isinstance(value, bool) and 100 <= value <= 599:
            safe[key] = value
        elif key == "delivery_status" and isinstance(value, str) and value in {"ACCEPTED", "REJECTED", "PENDING"}:
            safe[key] = value
        elif key in {"code", "provider_id"} and isinstance(value, str) and SAFE_PROVIDER_ID.fullmatch(value):
            safe[key] = value
    messages = response.get("messages")
    if isinstance(messages, list):
        message_ids = [item["id"] for item in messages
            if isinstance(item, dict) and isinstance(item.get("id"), str)
            and SAFE_PROVIDER_ID.fullmatch(item["id"])]
        if message_ids:
            safe["provider_message_ids"] = message_ids[:20]
    return safe or None


def claimable(now):
    return (NotificationJob.status == NotificationStatus.PENDING,
        NotificationJob.scheduled_at <= now,
        or_(NotificationJob.locked_until.is_(None), NotificationJob.locked_until <= now))


async def process_pending_jobs(session_factory=None, delivery=None):
    session_factory = session_factory or AsyncSessionLocal
    delivery = delivery or dispatcher
    async with session_factory() as db:
        now = datetime.now(UTC)
        ids = (await db.execute(select(NotificationJob.id).where(*claimable(now))
            .order_by(NotificationJob.scheduled_at).limit(20))).scalars().all()
        for identifier in ids:
            token = uuid4()
            claimed = await db.execute(update(NotificationJob).where(
                NotificationJob.id == identifier, *claimable(datetime.now(UTC)))
                .values(lock_token=token, locked_until=datetime.now(UTC) + timedelta(minutes=5)))
            await db.commit()
            if claimed.rowcount != 1:
                continue
            job = (await db.execute(select(NotificationJob).where(NotificationJob.id == identifier)
                .options(selectinload(NotificationJob.recipients)))).scalar_one()
            try:
                for recipient in job.recipients:
                    if recipient.status in {NotificationStatus.SENT, NotificationStatus.CANCELLED}:
                        continue
                    try:
                        result = await asyncio.wait_for(delivery.dispatch(job.channel,
                            recipient.recipient_address, job.subject, job.body), timeout=120)
                    except Exception as exc:
                        logger.warning("notification_provider_failed error_type=%s", type(exc).__name__)
                        result = ProviderResult(success=False, message="Bildirim sağlayıcısı yanıt vermedi")
                    recipient.provider_response = _safe_provider_response(result.response)
                    recipient.error_message = None if result.success else SAFE_PROVIDER_ERROR
                    recipient.status = NotificationStatus.SENT if result.success else NotificationStatus.FAILED
                    if result.success:
                        recipient.sent_at = datetime.now(UTC)
                    job.locked_until = datetime.now(UTC) + timedelta(minutes=5)
                    # Commit each delivery so a later provider failure doesn't replay earlier recipients.
                    await db.commit()
                all_sent = bool(job.recipients) and all(recipient.status in {
                    NotificationStatus.SENT, NotificationStatus.CANCELLED} for recipient in job.recipients)
                if all_sent:
                    job.status, job.processed_at = NotificationStatus.SENT, datetime.now(UTC)
                else:
                    job.retry_count += 1
                    job.status = NotificationStatus.FAILED if not job.recipients or job.retry_count >= job.max_retries else NotificationStatus.PENDING
                    job.scheduled_at = datetime.now(UTC) + timedelta(seconds=min(3600, 60 * 2 ** min(job.retry_count, 6)))
                job.locked_until, job.lock_token = None, None
                await db.commit()
            except Exception as exc:
                await db.rollback()
                # The durable lease expires after a crashed attempt.
                logger.error("notification_job_attempt_failed error_type=%s", type(exc).__name__)


async def run_worker():
    logger.info("Notification outbox worker started")
    while True:
        try:
            await process_pending_jobs()
        except Exception as exc:
            logger.error("notification_worker_iteration_failed error_type=%s", type(exc).__name__)
        await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    asyncio.run(run_worker())
