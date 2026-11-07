from collections.abc import Callable
from functools import wraps
from inspect import Parameter, signature

from fastapi import Depends

from app.core.dependencies import get_tenant_context
from app.core.exceptions import ForbiddenException
from app.core.tenant import TenantContext


def require_permission(*permissions: str) -> Callable:
    def decorator(func: Callable) -> Callable:
        original_signature = signature(func, eval_str=True)
        inject_tenant = "tenant" not in original_signature.parameters

        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Try to get tenant from kwargs
            tenant = kwargs.pop("_permission_tenant", None) if inject_tenant else kwargs.get("tenant")
            if tenant is None:
                # Try to get from args if it's a positional argument
                for arg in args:
                    if isinstance(arg, TenantContext):
                        tenant = arg
                        break
            if tenant is None:
                raise ForbiddenException()
            if not tenant.has_any_permission(list(permissions)):
                raise ForbiddenException(f"Gerekli yetki: {', '.join(permissions)}")
            return await func(*args, **kwargs)

        if inject_tenant:
            parameters = list(original_signature.parameters.values())
            insertion = next((i for i, p in enumerate(parameters) if p.kind == Parameter.VAR_KEYWORD), len(parameters))
            parameters.insert(insertion, Parameter(
                "_permission_tenant", Parameter.KEYWORD_ONLY,
                default=Depends(get_tenant_context), annotation=TenantContext,
            ))
            wrapper.__signature__ = original_signature.replace(parameters=parameters)
        else:
            wrapper.__signature__ = original_signature
        return wrapper

    return decorator


class PermissionChecker:
    def __init__(self, *permissions: str):
        self.permissions = permissions

    async def __call__(self, tenant: TenantContext = Depends(get_tenant_context)) -> TenantContext:
        if not tenant.has_any_permission(list(self.permissions)):
            raise ForbiddenException(f"Gerekli yetki: {', '.join(self.permissions)}")
        return tenant
