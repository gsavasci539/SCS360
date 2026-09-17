from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import verify_access_token
from app.core.tenant import TenantContext
from app.infrastructure.models.models import ClassTeacher, Role, User, UserStatus

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not credentials:
        raise UnauthorizedException()
    payload = verify_access_token(credentials.credentials)
    if not payload:
        raise UnauthorizedException("Geçersiz veya süresi dolmuş token")
    user_id = payload.get("sub")
    try:
        parsed_user_id = UUID(str(user_id))
    except (TypeError, ValueError, AttributeError) as exc:
        raise UnauthorizedException("Geçersiz token öznesi") from exc
    result = await db.execute(
        select(User)
        .options(
            selectinload(User.roles).selectinload(Role.permissions),
            selectinload(User.branches),
        )
        .where(User.id == parsed_user_id, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise UnauthorizedException("Kullanıcı bulunamadı")
    if user.status != UserStatus.ACTIVE:
        raise ForbiddenException("Hesabınız aktif değil")
    return user


async def get_tenant_context(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TenantContext:
    permissions: set[str] = set()
    role_slugs: set[str] = set()
    for role in user.roles:
        role_slugs.add(role.slug)
        for perm in role.permissions:
            permissions.add(perm.code)
    
    # Debug logging
    print(f"DEBUG: User {user.email} - Role slugs: {role_slugs}")
    print(f"DEBUG: User {user.email} - Permissions from DB: {permissions}")

    branch_ids = [b.id for b in user.branches]

    class_ids: list[UUID] = []
    if "teacher" in role_slugs:
        result = await db.execute(
            select(ClassTeacher.class_id).where(ClassTeacher.user_id == user.id)
        )
        class_ids = list(result.scalars().all())

    return TenantContext(
        user_id=user.id,
        organization_id=user.organization_id,
        branch_ids=branch_ids,
        class_ids=class_ids,
        permissions=permissions,
        role_slugs=role_slugs,
        is_super_admin=user.is_super_admin,
    )


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    if not credentials:
        return None
    try:
        return await get_current_user(credentials, db)
    except (UnauthorizedException, ForbiddenException):
        return None
