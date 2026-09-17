from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedException, ValidationException
from app.core.security import (
    create_access_token,
    create_password_reset_token_value,
    create_refresh_token_value,
    hash_password,
    hash_token,
    verify_password,
)
from app.infrastructure.models.models import (
    AuditAction,
    AuditLog,
    LoginAttempt,
    PasswordResetToken,
    RefreshToken,
    Role,
    User,
    UserStatus,
)

settings = get_settings()


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def login(
        self, email: str, password: str, ip: str | None, user_agent: str | None
    ) -> dict:
        result = await self.db.execute(
            select(User)
            .options(
                selectinload(User.roles).selectinload(Role.permissions), selectinload(User.branches)
            )
            .where(User.email == email.lower(), User.deleted_at.is_(None))
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.password_hash):
            self.db.add(
                LoginAttempt(
                    email=email,
                    ip_address=ip,
                    user_agent=user_agent,
                    success=False,
                    failure_reason="invalid_credentials",
                )
            )
            # Persist security telemetry even though the authentication request fails.
            await self.db.commit()
            raise UnauthorizedException("E-posta veya şifre hatalı")

        if user.status != UserStatus.ACTIVE:
            raise UnauthorizedException("Hesabınız aktif değil")

        # Skip last_login_at update due to UUID issues
        # user.last_login_at = datetime.now(UTC)
        self.db.add(LoginAttempt(email=email, ip_address=ip, user_agent=user_agent, success=True))

        permissions = set()
        roles = []
        for role in user.roles:
            roles.append({"id": str(role.id), "name": role.name, "slug": role.slug})
            for perm in role.permissions:
                permissions.add(perm.code)
        
        # Add super_admin permission if user is super admin
        if user.is_super_admin:
            permissions.add("super_admin")

        access_token = create_access_token(
            user.id, {
                "org_id": str(user.organization_id) if user.organization_id else None,
                "permissions": sorted(permissions)
            }
        )
        refresh_value = create_refresh_token_value()
        family_id = uuid4()
        refresh = RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh_value),
            family_id=family_id,
            expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            ip_address=ip,
            user_agent=user_agent,
        )
        self.db.add(refresh)
        self.db.add(
            AuditLog(
                user_id=user.id,
                organization_id=user.organization_id,
                action=AuditAction.LOGIN,
                entity_type="user",
                entity_id=user.id,
                ip_address=ip,
                user_agent=user_agent,
            )
        )
        await self.db.flush()

        return {
            "access_token": access_token,
            "refresh_token": refresh_value,
            "token_type": "bearer",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone": user.phone,
                "status": user.status.value,
                "is_super_admin": user.is_super_admin,
                "organization_id": str(user.organization_id) if user.organization_id else None,
                "roles": roles,
                "permissions": sorted(permissions),
                "branch_ids": [str(b.id) for b in user.branches],
            },
        }

    async def refresh(self, refresh_token: str, ip: str | None, user_agent: str | None) -> dict:
        token_hash = hash_token(refresh_token)
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash).with_for_update()
        )
        old_token = result.scalar_one_or_none()
        now = datetime.now(UTC)
        if not old_token or old_token.expires_at <= now:
            raise UnauthorizedException("Geçersiz refresh token")

        if old_token.revoked_at is not None:
            await self.db.execute(
                update(RefreshToken)
                .where(
                    RefreshToken.family_id == old_token.family_id,
                    RefreshToken.revoked_at.is_(None),
                )
                .values(revoked_at=now)
            )
            await self.db.commit()
            raise UnauthorizedException("Refresh token yeniden kullanıldı; oturum sonlandırıldı")

        user_result = await self.db.execute(
            select(User)
            .options(selectinload(User.roles).selectinload(Role.permissions))
            .where(User.id == old_token.user_id, User.deleted_at.is_(None))
        )
        user = user_result.scalar_one_or_none()
        if not user or user.status != UserStatus.ACTIVE:
            old_token.revoked_at = now
            await self.db.commit()
            raise UnauthorizedException("Kullanıcı hesabı aktif değil")

        old_token.revoked_at = now
        new_refresh_value = create_refresh_token_value()
        new_token = RefreshToken(
            user_id=old_token.user_id,
            token_hash=hash_token(new_refresh_value),
            family_id=old_token.family_id,
            expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            ip_address=ip,
            user_agent=user_agent,
        )
        self.db.add(new_token)
        await self.db.flush()
        old_token.replaced_by = new_token.id

        # Get permissions for the new access token
        permissions = set()
        for role in user.roles:
            for perm in role.permissions:
                permissions.add(perm.code)
        
        # Add super_admin permission if user is super admin
        if user.is_super_admin:
            permissions.add("super_admin")

        access_token = create_access_token(
            old_token.user_id,
            {
                "org_id": str(user.organization_id) if user.organization_id else None,
                "permissions": sorted(permissions)
            },
        )
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_value,
            "token_type": "bearer",
        }

    async def logout(self, refresh_token: str, user_id: UUID) -> None:
        token_hash = hash_token(refresh_token)
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash, RefreshToken.user_id == user_id
            )
        )
        token = result.scalar_one_or_none()
        if token:
            token.revoked_at = datetime.now(UTC)
        self.db.add(
            AuditLog(
                user_id=user_id, action=AuditAction.LOGOUT, entity_type="user", entity_id=user_id
            )
        )

    async def forgot_password(self, email: str) -> str:
        result = await self.db.execute(
            select(User).where(User.email == email.lower(), User.deleted_at.is_(None))
        )
        user = result.scalar_one_or_none()
        if not user:
            return "reset_sent"
        token_value = create_password_reset_token_value()
        self.db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=hash_token(token_value),
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            )
        )
        await self.db.flush()
        return token_value

    async def reset_password(self, token: str, new_password: str) -> None:
        if len(new_password) < 8:
            raise ValidationException("Şifre en az 8 karakter olmalıdır")
        token_hash = hash_token(token)
        result = await self.db.execute(
            select(PasswordResetToken)
            .where(
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.used_at.is_(None),
                PasswordResetToken.expires_at > datetime.now(UTC),
            )
            .with_for_update()
        )
        reset_token = result.scalar_one_or_none()
        if not reset_token:
            raise ValidationException("Geçersiz veya süresi dolmuş token")
        user_result = await self.db.execute(select(User).where(User.id == reset_token.user_id))
        user = user_result.scalar_one()
        user.password_hash = hash_password(new_password)
        now = datetime.now(UTC)
        reset_token.used_at = now
        await self.db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user.id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )

    async def get_me(self, user: User) -> dict:
        permissions = set()
        roles = []
        for role in user.roles:
            roles.append({"id": str(role.id), "name": role.name, "slug": role.slug})
            for perm in role.permissions:
                permissions.add(perm.code)
        return {
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": user.phone,
            "status": user.status.value,
            "is_super_admin": user.is_super_admin,
            "organization_id": str(user.organization_id) if user.organization_id else None,
            "roles": roles,
            "permissions": sorted(permissions),
            "branch_ids": [str(b.id) for b in user.branches],
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        }
