from uuid import UUID

from fastapi import Depends, Request, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import verify_access_token
from app.core.tenant import TenantContext, effective_roles
from app.infrastructure.models.models import ClassTeacher, Role, User, UserStatus
from app.core import tenant_guard  # noqa: F401 - register session boundary guards
from app.core import class_capacity_guard  # noqa: F401 - organization locks precede quota checks
from app.core import subscription_guard  # noqa: F401 - register purchased capacity checks

security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db, scope="function"),
    workspace_header: str | None = Header(default=None, alias="X-SCS360-Organization-Id", description="Yalnız platform yöneticisi: seçilen kurum çalışma alanının UUID'si. Auth/platform/subscription yolları asıl platform hesabında kalır."),
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
    from app.core.platform_workspace import select_workspace
    workspace_user = await select_workspace(request, db, user)
    if workspace_user is not None:
        return workspace_user
    from app.core.student_access import accessible_student_ids
    roles = effective_roles(user)
    tenant = TenantContext(user_id=user.id, organization_id=user.organization_id,
        # Preserve the presence of branch assignments. Removing every stale
        # link here would turn a restricted user into an organization-wide one;
        # the tenant guard filters out deleted and foreign branches instead.
        branch_ids=[branch.id for branch in user.branches],
        role_slugs={role.slug for role in roles}, permissions={perm.code for role in roles for perm in role.permissions},
        is_super_admin=user.is_super_admin)
    db.info["accessible_student_ids"] = await accessible_student_ids(db, tenant)
    db.info["tenant_context"] = tenant
    from app.application.services.subscription_access import for_user
    from app.core.exceptions import AppException
    access = await for_user(db, user)
    if access["restricted"] and request.url.path not in {"/api/auth/me", "/api/auth/logout", "/api/auth/refresh"} and not request.url.path.startswith("/api/subscription/"):
        raise AppException(access["warning"], status_code=402, errors=[{"code": "SUBSCRIPTION_REQUIRED", "access": access}])
    return user


async def get_tenant_context(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
) -> TenantContext:
    existing = db.info.get("tenant_context")
    if existing is not None and (existing.platform_admin or existing.parent_portal):
        return existing
    permissions: set[str] = set()
    role_slugs: set[str] = set()
    for role in effective_roles(user):
        role_slugs.add(role.slug)
        for perm in role.permissions:
            permissions.add(perm.code)
    
    # Add super_admin permissions for super admin users
    if user.is_super_admin:
        permissions.add("super_admin")
        all_permissions = ["org.read", "org.write", "branch.read", "branch.write", 
                        "user.read", "user.write", "student.read", "student.write",
                        "class.read", "class.write", "attendance.read", "attendance.write",
                        "finance.read", "finance.write", "receipt.read", "receipt.write",
                        "announcement.read", "announcement.write", "notification.read", "notification.write",
                        "report.read", "settings.read", "settings.write", "dashboard.read", "dashboard.view",
                        "canteen.read", "canteen.write", "security.read", "security.write"]
        permissions.update(all_permissions)

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
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db, scope="function"),
) -> User | None:
    if not credentials:
        return None
    try:
        return await get_current_user(request=request, credentials=credentials, db=db)
    except (UnauthorizedException, ForbiddenException):
        return None


async def require_super_admin(
    user: User = Depends(get_current_user),
) -> User:
    """Dependency that requires the user to be a super admin."""
    if not user.is_super_admin:
        raise ForbiddenException("Bu işlem için süper admin yetkisi gereklidir")
    return user
