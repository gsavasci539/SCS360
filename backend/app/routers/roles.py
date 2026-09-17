from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from uuid import UUID

from app.application.schemas import RoleCreate, RoleUpdate, RoleResponse
from app.repositories import RoleRepository, PermissionRepository
from app.domain.entities.role_permission import RolePermission
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.permissions import require_permission
from app.core.responses import success_response
from app.domain.entities.user import User

router = APIRouter(prefix="/api/roles", tags=["Roles"])


@router.post("", response_model=RoleResponse)
@require_permission("roles.create")
async def create_role(
    role: RoleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = RoleRepository()
    role_data = role.model_dump()
    role_data["organization_id"] = current_user.organization_id
    
    db_role = await repo.create(db, role_data)
    return success_response(db_role, "Rol oluşturuldu")


@router.get("", response_model=list[RoleResponse])
@require_permission("roles.view")
async def list_roles(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = RoleRepository()
    
    if current_user.organization_id:
        roles = await repo.get_by_organization(db, current_user.organization_id, skip, limit)
    else:
        roles = await repo.get_system_roles(db, skip, limit)
    
    return success_response(roles)


@router.get("/{role_id}", response_model=RoleResponse)
@require_permission("roles.view")
async def get_role(
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = RoleRepository()
    role = await repo.get_with_permissions(db, role_id)
    
    if not role:
        return success_response(None, "Rol bulunamadı", success=False)
    
    return success_response(role)


@router.put("/{role_id}", response_model=RoleResponse)
@require_permission("roles.update")
async def update_role(
    role_id: UUID,
    role: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = RoleRepository()
    db_role = await repo.get(db, role_id)
    
    if not db_role:
        return success_response(None, "Rol bulunamadı", success=False)
    
    if db_role.is_system:
        return success_response(None, "Sistem rolleri güncellenemez", success=False)
    
    role_data = role.model_dump(exclude_unset=True)
    updated_role = await repo.update(db, db_role, role_data)
    return success_response(updated_role, "Rol güncellendi")


@router.delete("/{role_id}")
@require_permission("roles.delete")
async def delete_role(
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = RoleRepository()
    db_role = await repo.get(db, role_id)
    
    if not db_role:
        return success_response(None, "Rol bulunamadı", success=False)
    
    if db_role.is_system:
        return success_response(None, "Sistem rolleri silinemez", success=False)
    
    await repo.delete(db, role_id)
    return success_response(message="Rol silindi")


@router.post("/{role_id}/permissions")
@require_permission("roles.update")
async def assign_permissions(
    role_id: UUID,
    permission_ids: List[UUID],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = RoleRepository()
    db_role = await repo.get(db, role_id)
    
    if not db_role:
        return success_response(None, "Rol bulunamadı", success=False)
    
    # Remove existing permissions
    await db.execute(
        f"DELETE FROM role_permissions WHERE role_id = '{role_id}'"
    )
    
    # Assign new permissions
    for permission_id in permission_ids:
        role_permission = RolePermission(role_id=role_id, permission_id=permission_id)
        db.add(role_permission)
    
    await db.flush()
    return success_response(message="İzinler atandı")


@router.get("/{role_id}/permissions")
@require_permission("roles.view")
async def get_role_permissions(
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from sqlalchemy import select
    from app.domain.entities.permission import Permission
    from app.domain.entities.role_permission import RolePermission
    
    result = await db.execute(
        select(Permission)
        .join(RolePermission, Permission.id == RolePermission.permission_id)
        .where(RolePermission.role_id == role_id)
    )
    permissions = result.scalars().all()
    
    return success_response(permissions)
