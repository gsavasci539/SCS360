from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from app.domain.entities.role import Role
from app.domain.entities.role_permission import RolePermission
from app.repositories.base_repository import BaseRepository


class RoleRepository(BaseRepository[Role]):
    async def get_by_name(
        self, db: AsyncSession, name: str, organization_id: Optional[UUID] = None
    ) -> Optional[Role]:
        query = select(Role).where(Role.name == name)
        if organization_id:
            query = query.where(Role.organization_id == organization_id)
        else:
            query = query.where(Role.organization_id.is_(None))
        
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_organization(
        self, db: AsyncSession, organization_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Role]:
        result = await db.execute(
            select(Role)
            .where(Role.organization_id == organization_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_system_roles(
        self, db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> List[Role]:
        result = await db.execute(
            select(Role)
            .where(Role.is_system == True)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_with_permissions(
        self, db: AsyncSession, role_id: UUID
    ) -> Optional[Role]:
        result = await db.execute(
            select(Role)
            .options(selectinload(Role.role_permissions))
            .where(Role.id == role_id)
        )
        return result.scalar_one_or_none()
