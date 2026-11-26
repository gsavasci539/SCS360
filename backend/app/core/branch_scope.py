"""Reusable dependency for endpoints whose data is inherently branch-scoped."""

from fastapi import Depends

from app.core.dependencies import get_tenant_context
from app.core.exceptions import ForbiddenException
from app.core.tenant import TenantContext


def ensure_assigned_branch(tenant: TenantContext) -> None:
    if not tenant.has_institution_wide_branch_access and not tenant.branch_ids:
        raise ForbiddenException("Bu işlem için atanmış bir şube gerekir")


async def require_assigned_branch(tenant: TenantContext = Depends(get_tenant_context)) -> None:
    ensure_assigned_branch(tenant)
