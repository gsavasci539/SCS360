"""Explicit tenant workspace for a platform operator, without changing accounts."""
from uuid import UUID

from sqlalchemy import select

from app.core.exceptions import AppException, ForbiddenException, NotFoundException
from app.core.tenant import TenantContext
from app.infrastructure.models.models import Organization

HEADER = "x-scs360-organization-id"


class WorkspacePrincipal:
    """Request-only view; the persistent User is never reassigned or modified."""
    is_super_admin = False
    is_platform_admin = True
    branches = ()
    __slots__ = ("_operator", "organization_id")

    def __init__(self, operator, organization_id):
        self._operator = operator
        self.organization_id = organization_id

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return getattr(self._operator, name)


def is_control_path(path):
    return path.startswith(("/api/auth/", "/api/platform/", "/api/subscription/", "/api/public/"))


async def select_workspace(request, db, operator):
    value = request.headers.get(HEADER)
    if not value:
        return None
    if not operator.is_super_admin:
        raise ForbiddenException("Kurum çalışma alanını yalnız platform yöneticisi seçebilir")
    if is_control_path(request.url.path):
        return None
    try:
        identifier = UUID(value)
    except ValueError as exc:
        raise AppException("Kurum çalışma alanı kimliği geçersiz", status_code=422) from exc
    table = Organization.__table__
    exists = (await db.execute(select(table.c.id).where(table.c.id == identifier, table.c.deleted_at.is_(None)))).first()
    if exists is None:
        raise NotFoundException("Kurum çalışma alanı bulunamadı")
    tenant = TenantContext(user_id=operator.id, organization_id=identifier, role_slugs={"owner"}, platform_admin=True)
    db.info["tenant_context"] = tenant
    db.info["accessible_student_ids"] = None
    return WorkspacePrincipal(operator, identifier)
