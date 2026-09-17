from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import secrets

from app.core.security import (
    verify_password,
    hash_password,
    create_access_token,
    create_refresh_token,
    decode_token
)
from app.repositories import UserRepository
from app.domain.entities.user import User
from app.domain.entities.role import Role
from app.domain.entities.permission import Permission
from app.domain.entities.role_permission import RolePermission
from app.domain.entities.user_role import UserRole
from app.core.exceptions import AppException


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository()

    async def login(
        self,
        email: str,
        password: str,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> dict:
        user = await self.user_repo.get_by_email(self.db, email)
        
        if not user:
            raise AppException("Geçersiz email veya şifre", status_code=401)
        
        if not user.is_active:
            raise AppException("Hesap devre dışı bırakılmış", status_code=403)
        
        if user.status != "active":
            raise AppException("Hesap aktif değil", status_code=403)
        
        if not verify_password(password, user.password_hash):
            raise AppException("Geçersiz email veya şifre", status_code=401)
        
        # Get user roles and permissions
        user_data = await self._get_user_with_permissions(user.id)
        
        # Create tokens
        access_token = create_access_token(
            subject=str(user.id),
            organization_id=str(user.organization_id),
            roles=user_data["roles"],
            permissions=user_data["permissions"]
        )
        refresh_token = await self._create_refresh_token(user.id, ip, user_agent)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": user_data
        }

    async def refresh(
        self,
        refresh_token: str,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> dict:
        try:
            payload = decode_token(refresh_token)
            user_id = UUID(payload.get("sub"))
            
            user = await self.user_repo.get(self.db, user_id)
            if not user or not user.is_active:
                raise AppException("Geçersiz refresh token", status_code=401)
            
            # Get user roles and permissions
            user_data = await self._get_user_with_permissions(user.id)
            
            # Create new tokens
            access_token = create_access_token(
                subject=str(user.id),
                organization_id=str(user.organization_id),
                roles=user_data["roles"],
                permissions=user_data["permissions"]
            )
            new_refresh_token = await self._create_refresh_token(user.id, ip, user_agent)
            
            return {
                "access_token": access_token,
                "refresh_token": new_refresh_token,
                "token_type": "bearer"
            }
        except Exception:
            raise AppException("Geçersiz refresh token", status_code=401)

    async def logout(self, refresh_token: str, user_id: UUID):
        # TODO: Implement refresh token invalidation
        pass

    async def get_me(self, user: User) -> dict:
        user_data = await self._get_user_with_permissions(user.id)
        return user_data

    async def forgot_password(self, email: str):
        user = await self.user_repo.get_by_email(self.db, email)
        if user:
            # TODO: Generate reset token and send email
            pass

    async def reset_password(self, token: str, new_password: str):
        # TODO: Verify token and update password
        pass

    async def _get_user_with_permissions(self, user_id: UUID) -> dict:
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise AppException("Kullanıcı bulunamadı", status_code=404)
        
        # Get user roles
        roles_result = await self.db.execute(
            select(Role.name)
            .join(UserRole, Role.id == UserRole.role_id)
            .where(UserRole.user_id == user_id)
        )
        roles = [r[0] for r in roles_result.fetchall()]
        
        # Get permissions
        permissions_result = await self.db.execute(
            select(Permission.name)
            .join(RolePermission, Permission.id == RolePermission.permission_id)
            .join(UserRole, RolePermission.role_id == UserRole.role_id)
            .where(UserRole.user_id == user_id)
        )
        permissions = list(set([p[0] for p in permissions_result.fetchall()]))
        
        return {
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "organization_id": str(user.organization_id),
            "roles": roles,
            "permissions": permissions
        }

    async def _create_refresh_token(
        self,
        user_id: UUID,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> str:
        # TODO: Store refresh token in database with expiration
        return create_refresh_token(subject=str(user_id))
