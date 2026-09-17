from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import UserRepository, RoleRepository
from app.domain.entities.user import User
from app.domain.entities.user_role import UserRole
from app.domain.entities.user_branch import UserBranch
from app.core.security import hash_password
from app.core.exceptions import AppException


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository()
        self.role_repo = RoleRepository()

    async def create_user(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        organization_id: UUID,
        role_ids: Optional[List[UUID]] = None,
        branch_ids: Optional[List[UUID]] = None,
        **kwargs
    ) -> User:
        # Check if email already exists
        existing = await self.user_repo.get_by_email(self.db, email)
        if existing:
            raise AppException("Bu email zaten kullanımda", status_code=400)
        
        # Create user
        user_data = {
            "email": email,
            "password_hash": hash_password(password),
            "first_name": first_name,
            "last_name": last_name,
            "organization_id": organization_id,
            **kwargs
        }
        
        user = await self.user_repo.create(self.db, user_data)
        
        # Assign roles
        if role_ids:
            for role_id in role_ids:
                user_role = UserRole(user_id=user.id, role_id=role_id)
                self.db.add(user_role)
            await self.db.flush()
        
        # Assign branches
        if branch_ids:
            for branch_id in branch_ids:
                user_branch = UserBranch(user_id=user.id, branch_id=branch_id)
                self.db.add(user_branch)
            await self.db.flush()
        
        return user

    async def update_user(
        self,
        user_id: UUID,
        **kwargs
    ) -> User:
        user = await self.user_repo.get(self.db, user_id)
        if not user:
            raise AppException("Kullanıcı bulunamadı", status_code=404)
        
        if "password" in kwargs:
            kwargs["password_hash"] = hash_password(kwargs.pop("password"))
        
        user = await self.user_repo.update(self.db, user, kwargs)
        return user

    async def assign_roles(self, user_id: UUID, role_ids: List[UUID]) -> None:
        # Remove existing roles
        await self.db.execute(
            f"DELETE FROM user_roles WHERE user_id = '{user_id}'"
        )
        
        # Assign new roles
        for role_id in role_ids:
            user_role = UserRole(user_id=user_id, role_id=role_id)
            self.db.add(user_role)
        
        await self.db.flush()

    async def assign_branches(self, user_id: UUID, branch_ids: List[UUID]) -> None:
        # Remove existing branches
        await self.db.execute(
            f"DELETE FROM user_branches WHERE user_id = '{user_id}'"
        )
        
        # Assign new branches
        for branch_id in branch_ids:
            user_branch = UserBranch(user_id=user_id, branch_id=branch_id)
            self.db.add(user_branch)
        
        await self.db.flush()

    async def get_user_roles(self, user_id: UUID) -> List[str]:
        from sqlalchemy import select
        from app.domain.entities.role import Role
        from app.domain.entities.user_role import UserRole
        
        result = await self.db.execute(
            select(Role.name)
            .join(UserRole, Role.id == UserRole.role_id)
            .where(UserRole.user_id == user_id)
        )
        return [r[0] for r in result.fetchall()]

    async def get_user_permissions(self, user_id: UUID) -> List[str]:
        from sqlalchemy import select
        from app.domain.entities.permission import Permission
        from app.domain.entities.role_permission import RolePermission
        from app.domain.entities.user_role import UserRole
        
        result = await self.db.execute(
            select(Permission.name)
            .join(RolePermission, Permission.id == RolePermission.permission_id)
            .join(UserRole, RolePermission.role_id == UserRole.role_id)
            .where(UserRole.user_id == user_id)
        )
        return list(set([p[0] for p in result.fetchall()]))
