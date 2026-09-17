from typing import Optional, List
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from app.domain.entities.announcement import Announcement
from app.domain.entities.announcement_recipient import AnnouncementRecipient
from app.repositories.base_repository import BaseRepository


class AnnouncementRepository(BaseRepository[Announcement]):
    async def get_by_organization(
        self, db: AsyncSession, organization_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Announcement]:
        result = await db.execute(
            select(Announcement)
            .where(Announcement.organization_id == organization_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_branch(
        self, db: AsyncSession, branch_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Announcement]:
        result = await db.execute(
            select(Announcement)
            .where(Announcement.branch_id == branch_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_status(
        self, db: AsyncSession, organization_id: UUID, status: str
    ) -> List[Announcement]:
        result = await db.execute(
            select(Announcement).where(
                and_(
                    Announcement.organization_id == organization_id,
                    Announcement.status == status
                )
            )
        )
        return result.scalars().all()

    async def get_scheduled_announcements(
        self, db: AsyncSession, organization_id: UUID
    ) -> List[Announcement]:
        result = await db.execute(
            select(Announcement).where(
                and_(
                    Announcement.organization_id == organization_id,
                    Announcement.status == "scheduled",
                    Announcement.scheduled_for <= datetime.utcnow()
                )
            )
        )
        return result.scalars().all()

    async def get_with_recipients(
        self, db: AsyncSession, announcement_id: UUID
    ) -> Optional[Announcement]:
        result = await db.execute(
            select(Announcement)
            .options(selectinload(Announcement.announcement_recipients))
            .where(Announcement.id == announcement_id)
        )
        return result.scalar_one_or_none()
