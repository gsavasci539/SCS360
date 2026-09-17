from typing import Optional, List
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from app.domain.entities.notification_job import NotificationJob
from app.repositories.base_repository import BaseRepository


class NotificationJobRepository(BaseRepository[NotificationJob]):
    async def get_pending_jobs(
        self, db: AsyncSession, limit: int = 100
    ) -> List[NotificationJob]:
        result = await db.execute(
            select(NotificationJob)
            .where(
                and_(
                    NotificationJob.status == "pending",
                    NotificationJob.scheduled_for <= datetime.utcnow(),
                    NotificationJob.retry_count < NotificationJob.max_retries
                )
            )
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_organization(
        self, db: AsyncSession, organization_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[NotificationJob]:
        result = await db.execute(
            select(NotificationJob)
            .where(NotificationJob.organization_id == organization_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_channel(
        self, db: AsyncSession, channel: str, skip: int = 0, limit: int = 100
    ) -> List[NotificationJob]:
        result = await db.execute(
            select(NotificationJob)
            .where(NotificationJob.channel == channel)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_failed_jobs(
        self, db: AsyncSession, organization_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[NotificationJob]:
        result = await db.execute(
            select(NotificationJob).where(
                and_(
                    NotificationJob.organization_id == organization_id,
                    NotificationJob.status == "failed"
                )
            )
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_recipient(
        self, db: AsyncSession, recipient_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[NotificationJob]:
        result = await db.execute(
            select(NotificationJob)
            .where(NotificationJob.recipient_id == recipient_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
