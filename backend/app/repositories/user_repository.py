from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from app.domain.entities.user import User
from app.domain.entities.user_role import UserRole
from app.domain.entities.user_branch import UserBranch
from app.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    async def get_by_email(
        self, db: AsyncSession, email: str
    ) -> Optional[User]:
        result = await db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_email_with_roles(
        self, db: AsyncSession, email: str
    ) -> Optional[User]:
        result = await db.execute(
            select(User)
            .options(selectinload(User.user_roles))
            .where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_organization(
        self, db: AsyncSession, organization_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[User]:
        result = await db.execute(
            select(User)
            .where(User.organization_id == organization_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_branch(
        self, db: AsyncSession, branch_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[User]:
        result = await db.execute(
            select(User)
            .join(UserBranch, User.id == UserBranch.user_id)
            .where(UserBranch.branch_id == branch_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_active_users(
        self, db: AsyncSession, organization_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[User]:
        result = await db.execute(
            select(User)
            .where(
                and_(
                    User.organization_id == organization_id,
                    User.status == "active",
                    User.is_active == True
                )
            )
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def search_users(
        self,
        db: AsyncSession,
        organization_id: UUID,
        search_term: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        result = await db.execute(
            select(User)
            .where(
                and_(
                    User.organization_id == organization_id,
                    or_(
                        User.first_name.ilike(f"%{search_term}%"),
                        User.last_name.ilike(f"%{search_term}%"),
                        User.email.ilike(f"%{search_term}%")
                    )
                )
            )
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
