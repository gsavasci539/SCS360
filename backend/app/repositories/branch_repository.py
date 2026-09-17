from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.domain.entities.branch import Branch
from app.repositories.base_repository import BaseRepository


class BranchRepository(BaseRepository[Branch]):
    async def get_by_code(
        self, db: AsyncSession, code: str, organization_id: UUID
    ) -> Optional[Branch]:
        result = await db.execute(
            select(Branch).where(
                and_(Branch.code == code, Branch.organization_id == organization_id)
            )
        )
        return result.scalar_one_or_none()

    async def get_by_organization(
        self, db: AsyncSession, organization_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Branch]:
        result = await db.execute(
            select(Branch)
            .where(Branch.organization_id == organization_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_active_branches(
        self, db: AsyncSession, organization_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Branch]:
        result = await db.execute(
            select(Branch)
            .where(
                and_(
                    Branch.organization_id == organization_id,
                    Branch.status == "active"
                )
            )
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
