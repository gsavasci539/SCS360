from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.application.schemas import PermissionResponse
from app.repositories import PermissionRepository
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.permissions import require_permission
from app.core.responses import success_response
from app.domain.entities.user import User

router = APIRouter(prefix="/api/permissions", tags=["Permissions"])


@router.get("", response_model=list[PermissionResponse])
@require_permission("permissions.view")
async def list_permissions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    module: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = PermissionRepository()
    
    if module:
        permissions = await repo.get_by_module(db, module, skip, limit)
    else:
        permissions = await repo.get_all_permissions(db, skip, limit)
    
    return success_response(permissions)


@router.get("/modules")
@require_permission("permissions.view")
async def list_permission_modules(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from sqlalchemy import select, func
    from app.domain.entities.permission import Permission
    
    result = await db.execute(
        select(Permission.module).distinct()
    )
    modules = [m[0] for m in result.fetchall()]
    
    return success_response(modules)
