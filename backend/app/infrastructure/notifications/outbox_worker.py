import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.infrastructure.models.models import NotificationJob, NotificationRecipient, NotificationStatus
from app.infrastructure.notifications.dispatcher import NotificationDispatcher

logger = logging.getLogger("edupanel.worker")
dispatcher = NotificationDispatcher()
POLL_INTERVAL = 10


async def process_pending_jobs():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(NotificationJob)
            .options(selectinload(NotificationJob.recipients))
            .where(
                NotificationJob.status == NotificationStatus.PENDING,
                NotificationJob.scheduled_at <= datetime.now(timezone.utc),
            )
            .limit(20)
        )
        jobs = result.scalars().all()
        for job in jobs:
            all_sent = True
            for recipient in job.recipients:
                if recipient.status == NotificationStatus.SENT:
                    continue
                result = await dispatcher.dispatch(
                    job.channel, recipient.recipient_address, job.subject, job.body
                )
                if result.success:
                    recipient.status = NotificationStatus.SENT
                    recipient.sent_at = datetime.now(timezone.utc)
                    recipient.provider_response = result.response
                else:
                    all_sent = False
                    recipient.status = NotificationStatus.FAILED
                    recipient.error_message = result.message
            if all_sent:
                job.status = NotificationStatus.SENT
                job.processed_at = datetime.now(timezone.utc)
            else:
                job.retry_count += 1
                if job.retry_count >= job.max_retries:
                    job.status = NotificationStatus.FAILED
                else:
                    job.status = NotificationStatus.PENDING
            await db.commit()


async def run_worker():
    logger.info("Notification outbox worker started")
    while True:
        try:
            await process_pending_jobs()
        except Exception:
            logger.exception("Worker error")
        await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    asyncio.run(run_worker())
