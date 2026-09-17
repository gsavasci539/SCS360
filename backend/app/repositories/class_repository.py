from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.domain.entities.class_ import Class
from app.repositories.base_repository import BaseRepository


class ClassRepository(BaseRepository[Class]):
    def __init__(self):
        super().__init__(Class)
    async def get_by_code(
        self, db: AsyncSession, code: str, organization_id: UUID
    ) -> Optional[Class]:
        result = await db.execute(
            select(Class).where(
                and_(Class.code == code, Class.organization_id == organization_id)
            )
        )
        return result.scalar_one_or_none()

    async def get_by_branch(
        self, db: AsyncSession, branch_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Class]:
        result = await db.execute(
            select(Class)
            .where(Class.branch_id == branch_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_organization(
        self, db: AsyncSession, organization_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Class]:
        result = await db.execute(
            select(Class)
            .where(Class.organization_id == organization_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_active_classes(
        self, db: AsyncSession, organization_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Class]:
        result = await db.execute(
            select(Class)
            .where(
                and_(
                    Class.organization_id == organization_id,
                    Class.status == "active"
                )
            )
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_teacher(
        self, db: AsyncSession, teacher_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Class]:
        result = await db.execute(
            select(Class)
            .where(Class.teacher_id == teacher_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
