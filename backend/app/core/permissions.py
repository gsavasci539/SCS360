from collections.abc import Callable
from functools import wraps

from fastapi import Depends

from app.core.dependencies import get_tenant_context
from app.core.exceptions import ForbiddenException
from app.core.tenant import TenantContext


def require_permission(*permissions: str) -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Try to get tenant from kwargs
            tenant = kwargs.get("tenant")
            if tenant is None:
                # Try to get from args if it's a positional argument
                for arg in args:
                    if isinstance(arg, TenantContext):
                        tenant = arg
                        break
            if tenant is None:
                print(f"DEBUG require_permission: Tenant is None! Args: {args}, Kwargs: {kwargs.keys()}")
                raise ForbiddenException()
            print(f"DEBUG require_permission: Required permissions: {permissions}")
            print(f"DEBUG require_permission: Tenant permissions: {tenant.permissions}")
            print(f"DEBUG require_permission: Tenant role slugs: {tenant.role_slugs}")
            print(f"DEBUG require_permission: Tenant is super admin: {tenant.is_super_admin}")
            if not tenant.has_any_permission(list(permissions)):
                raise ForbiddenException(f"Gerekli yetki: {', '.join(permissions)}")
            return await func(*args, **kwargs)

        return wrapper

    return decorator


class PermissionChecker:
    def __init__(self, *permissions: str):
        self.permissions = permissions

    async def __call__(self, tenant: TenantContext = Depends(get_tenant_context)) -> TenantContext:
        print(f"DEBUG PermissionChecker: Required permissions: {self.permissions}")
        print(f"DEBUG PermissionChecker: Tenant permissions: {tenant.permissions}")
        print(f"DEBUG PermissionChecker: Tenant role slugs: {tenant.role_slugs}")
        print(f"DEBUG PermissionChecker: Tenant is super admin: {tenant.is_super_admin}")
        if not tenant.has_any_permission(list(self.permissions)):
            raise ForbiddenException(f"Gerekli yetki: {', '.join(self.permissions)}")
        return tenant
