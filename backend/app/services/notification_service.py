from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.notification_job import NotificationJob
from app.repositories import NotificationJobRepository


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.notification_repo = NotificationJobRepository()

    async def create_notification_job(
        self,
        organization_id: UUID,
        channel: str,
        recipient_type: str,
        recipient_id: UUID,
        body: str,
        subject: Optional[str] = None,
        scheduled_for: Optional[datetime] = None,
        **kwargs
    ) -> NotificationJob:
        notification_data = {
            "organization_id": organization_id,
            "channel": channel,
            "recipient_type": recipient_type,
            "recipient_id": recipient_id,
            "subject": subject,
            "body": body,
            "scheduled_for": scheduled_for,
            "status": "pending",
            **kwargs
        }
        
        return await self.notification_repo.create(self.db, notification_data)

    async def process_pending_jobs(self, limit: int = 100) -> List[NotificationJob]:
        jobs = await self.notification_repo.get_pending_jobs(self.db, limit)
        
        for job in jobs:
            try:
                await self._send_notification(job)
                job.status = "sent"
                job.sent_at = datetime.utcnow()
                job.retry_count = 0
            except Exception as e:
                job.status = "failed"
                job.failed_at = datetime.utcnow()
                job.retry_count += 1
                job.error_message = str(e)
                
                if job.retry_count >= job.max_retries:
                    job.status = "failed_permanently"
            
            await self.db.flush()
        
        return jobs

    async def _send_notification(self, job: NotificationJob):
        # TODO: Implement actual notification sending based on channel
        # Email: SMTP
        # SMS: Netgsm/Twilio
        # WhatsApp: Meta API
        
        if job.channel == "email":
            await self._send_email(job)
        elif job.channel == "sms":
            await self._send_sms(job)
        elif job.channel == "whatsapp":
            await self._send_whatsapp(job)

    async def _send_email(self, job: NotificationJob):
        # TODO: Implement email sending
        pass

    async def _send_sms(self, job: NotificationJob):
        # TODO: Implement SMS sending
        pass

    async def _send_whatsapp(self, job: NotificationJob):
        # TODO: Implement WhatsApp sending
        pass
