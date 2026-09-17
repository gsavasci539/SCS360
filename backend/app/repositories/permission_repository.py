from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.domain.entities.permission import Permission
from app.repositories.base_repository import BaseRepository


class PermissionRepository(BaseRepository[Permission]):
    async def get_by_name(
        self, db: AsyncSession, name: str
    ) -> Optional[Permission]:
        result = await db.execute(
            select(Permission).where(Permission.name == name)
        )
        return result.scalar_one_or_none()

    async def get_by_module(
        self, db: AsyncSession, module: str, skip: int = 0, limit: int = 100
    ) -> List[Permission]:
        result = await db.execute(
            select(Permission)
            .where(Permission.module == module)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_all_permissions(
        self, db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> List[Permission]:
        result = await db.execute(
            select(Permission).offset(skip).limit(limit)
        )
        return result.scalars().all()
