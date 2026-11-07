from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedException, ValidationException
from app.core.tenant import effective_branches, effective_roles
from app.application.services.subscription_access import for_user
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
        for role in effective_roles(user):
            roles.append({"id": str(role.id), "name": role.name, "slug": role.slug})
            for perm in role.permissions:
                permissions.add(perm.code)
        
        # Add super_admin permission if user is super admin
        if user.is_super_admin:
            permissions.add("super_admin")
            # Also add all common permissions for super admin
            all_permissions = ["org.read", "org.write", "branch.read", "branch.write", 
                            "user.read", "user.write", "student.read", "student.write",
                            "class.read", "class.write", "attendance.read", "attendance.write",
                            "finance.read", "finance.write", "receipt.read", "receipt.write",
                            "announcement.read", "announcement.write", "notification.read", "notification.write",
                            "report.read", "settings.read", "settings.write", "dashboard.read", "dashboard.view",
                            "canteen.read", "canteen.write", "security.read", "security.write"]
            permissions.update(all_permissions)

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
                "organization_access": await for_user(self.db, user),
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
                "branch_ids": [str(b.id) for b in effective_branches(user)],
            },
        }

    async def refresh(self, refresh_token: str, ip: str | None, user_agent: str | None) -> dict:
        token_hash = hash_token(refresh_token)
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash).with_for_update()
        )
        old_token = result.scalar_one_or_none()
        now = datetime.now(UTC)
        # SQLite returns timezone-naive values even for timezone=True columns.
        # Stored timestamps represent UTC on both supported database engines.
        expires_at = old_token.expires_at if old_token else None
        if expires_at is not None and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if not old_token or expires_at <= now:
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
            .options(selectinload(User.roles).selectinload(Role.permissions), selectinload(User.branches))
            .where(User.id == old_token.user_id, User.deleted_at.is_(None))
        )
        user = user_result.scalar_one_or_none()
        if not user or user.status != UserStatus.ACTIVE:
            old_token.revoked_at = now
            await self.db.commit()
            raise UnauthorizedException("Kullanıcı hesabı aktif değil")

        claimed = await self.db.execute(update(RefreshToken).where(RefreshToken.id == old_token.id,
            RefreshToken.revoked_at.is_(None)).values(revoked_at=now).execution_options(synchronize_session=False))
        if claimed.rowcount != 1:
            await self.db.execute(update(RefreshToken).where(RefreshToken.family_id == old_token.family_id,
                RefreshToken.revoked_at.is_(None)).values(revoked_at=now))
            await self.db.commit()
            raise UnauthorizedException("Refresh token yeniden kullanıldı; oturum sonlandırıldı")
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
        for role in effective_roles(user):
            for perm in role.permissions:
                permissions.add(perm.code)
        
        # Add super_admin permission if user is super admin
        if user.is_super_admin:
            permissions.add("super_admin")
            # Also add all common permissions for super admin
            all_permissions = ["org.read", "org.write", "branch.read", "branch.write", 
                            "user.read", "user.write", "student.read", "student.write",
                            "class.read", "class.write", "attendance.read", "attendance.write",
                            "finance.read", "finance.write", "receipt.read", "receipt.write",
                            "announcement.read", "announcement.write", "notification.read", "notification.write",
                            "report.read", "settings.read", "settings.write", "dashboard.read", "dashboard.view",
                            "canteen.read", "canteen.write", "security.read", "security.write"]
            permissions.update(all_permissions)

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
            "user": await self.get_me(user),
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
        if user.organization_id:
            from urllib.parse import urlencode
            from app.infrastructure.models.models import NotificationJob, NotificationRecipient, NotificationChannel
            separator = "&" if "?" in settings.PASSWORD_RESET_URL else "?"
            url = settings.PASSWORD_RESET_URL + separator + urlencode({"token": token_value})
            job = NotificationJob(organization_id=user.organization_id, channel=NotificationChannel.EMAIL,
                subject="SCS360 şifre sıfırlama", body=f"Şifrenizi sıfırlamak için: {url}\nBağlantı 1 saat geçerlidir.",
                reference_type="PASSWORD_RESET", reference_id=user.id)
            self.db.add(job)
            await self.db.flush()
            self.db.add(NotificationRecipient(notification_job_id=job.id, user_id=user.id,
                recipient_name=f"{user.first_name} {user.last_name}", recipient_address=user.email))
        await self.db.flush()
        return token_value

    async def reset_password(self, token: str, new_password: str) -> None:
        if not 8 <= len(new_password) <= 4096:
            raise ValidationException("Şifre 8 ile 4096 karakter arasında olmalıdır")
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
        for role in effective_roles(user):
            roles.append({"id": str(role.id), "name": role.name, "slug": role.slug})
            for perm in role.permissions:
                permissions.add(perm.code)
        
        # Add super_admin permission if user is super admin
        if user.is_super_admin:
            permissions.add("super_admin")
            # Also add all common permissions for super admin
            all_permissions = ["org.read", "org.write", "branch.read", "branch.write", 
                            "user.read", "user.write", "student.read", "student.write",
                            "class.read", "class.write", "attendance.read", "attendance.write",
                            "finance.read", "finance.write", "receipt.read", "receipt.write",
                            "announcement.read", "announcement.write", "notification.read", "notification.write",
                            "report.read", "settings.read", "settings.write", "dashboard.read", "dashboard.view",
                            "canteen.read", "canteen.write", "security.read", "security.write"]
            permissions.update(all_permissions)
        
        return {
            "id": str(user.id),
            "organization_access": await for_user(self.db, user),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": user.phone,
            "avatar_url": user.avatar_url,
            "status": user.status.value,
            "is_super_admin": user.is_super_admin,
            "organization_id": str(user.organization_id) if user.organization_id else None,
            "roles": roles,
            "permissions": sorted(permissions),
            "branch_ids": [str(b.id) for b in effective_branches(user)],
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        }
