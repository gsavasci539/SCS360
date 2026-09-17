from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from app.domain.entities.parent import Parent
from app.repositories.base_repository import BaseRepository


class ParentRepository(BaseRepository[Parent]):
    async def get_by_organization(
        self, db: AsyncSession, organization_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Parent]:
        result = await db.execute(
            select(Parent)
            .where(Parent.organization_id == organization_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_phone(
        self, db: AsyncSession, phone: str, organization_id: UUID
    ) -> Optional[Parent]:
        result = await db.execute(
            select(Parent).where(
                and_(Parent.phone == phone, Parent.organization_id == organization_id)
            )
        )
        return result.scalar_one_or_none()

    async def get_primary_parents(
        self, db: AsyncSession, organization_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Parent]:
        result = await db.execute(
            select(Parent)
            .where(
                and_(
                    Parent.organization_id == organization_id,
                    Parent.is_primary == True
                )
            )
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def search_parents(
        self,
        db: AsyncSession,
        organization_id: UUID,
        search_term: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Parent]:
        result = await db.execute(
            select(Parent)
            .where(
                and_(
                    Parent.organization_id == organization_id,
                    or_(
                        Parent.first_name.ilike(f"%{search_term}%"),
                        Parent.last_name.ilike(f"%{search_term}%"),
                        Parent.phone.ilike(f"%{search_term}%")
                    )
                )
            )
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
