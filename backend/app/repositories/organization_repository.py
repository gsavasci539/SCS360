from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.domain.entities.organization import Organization
from app.repositories.base_repository import BaseRepository


class OrganizationRepository(BaseRepository[Organization]):
    async def get_by_tax_number(
        self, db: AsyncSession, tax_number: str
    ) -> Optional[Organization]:
        result = await db.execute(
            select(Organization).where(Organization.tax_number == tax_number)
        )
        return result.scalar_one_or_none()

    async def get_active_organizations(
        self, db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> List[Organization]:
        result = await db.execute(
            select(Organization)
            .where(Organization.status == "active")
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
