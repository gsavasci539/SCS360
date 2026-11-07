from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict

from app.application.schemas import ParentCreate, ParentUpdate, ParentResponse
from app.repositories import ParentRepository
from app.core.database import get_db
from app.core.dependencies import get_current_user, get_tenant_context
from app.core.permissions import require_permission, PermissionChecker
from app.core.responses import success_response
from app.domain.entities.user import User
from app.core.tenant import TenantContext

router = APIRouter(prefix="/api/parents", tags=["Parents"])


class ParentAccountLink(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: UUID | None


@router.get("/{parent_id}/account-options")
async def account_options(parent_id: UUID, search: str = Query("", max_length=100), limit: int = Query(21, ge=1, le=100), offset: int = Query(0, ge=0),
    tenant: TenantContext = Depends(get_tenant_context), db: AsyncSession = Depends(get_db, scope="function")):
    from app.application.services import parent_account_service as service
    return success_response(await service.options(db, tenant, parent_id, search, limit, offset))


@router.put("/{parent_id}/account")
async def account_link(parent_id: UUID, body: ParentAccountLink, tenant: TenantContext = Depends(get_tenant_context),
    actor: User = Depends(get_current_user), db: AsyncSession = Depends(get_db, scope="function")):
    from app.application.services import parent_account_service as service
    return success_response(await service.link(db, tenant, actor, parent_id, body.user_id))


def parent_to_dict(parent):
    """Convert Parent model object to dict for JSON serialization"""
    return {
        "id": str(parent.id),
        "organization_id": str(parent.organization_id),
        "user_id": str(parent.user_id) if parent.user_id else None,
        "first_name": parent.first_name,
        "last_name": parent.last_name,
        "relation_type": parent.relation_type.value,
        "phone": parent.phone,
        "sms_phone": parent.sms_phone,
        "whatsapp_phone": parent.whatsapp_phone,
        "email": parent.email,
        "address": parent.address,
        "receive_notifications": parent.receive_notifications,
        "created_at": parent.created_at,
        "updated_at": parent.updated_at,
        "deleted_at": parent.deleted_at,
        "status": "ACTIVE" if parent.deleted_at is None else "PASSIVE"
    }


@router.post("")
@require_permission("parents.write")
async def create_parent(
    parent: ParentCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user)
):
    repo = ParentRepository()
    parent_data = parent.model_dump()
    parent_data["created_by"] = current_user.id
    parent_data["organization_id"] = current_user.organization_id
    
    db_parent = await repo.create(db, parent_data)
    return success_response(parent_to_dict(db_parent), "Veli oluşturuldu")


@router.get("")
async def list_parents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("parents.read"))
):
    repo = ParentRepository()
    
    if search:
        parents = await repo.search_parents(db, tenant.organization_id, search, skip, limit)
    else:
        parents = await repo.get_by_organization(db, tenant.organization_id, skip, limit)
    
    return success_response([parent_to_dict(parent) for parent in parents])


@router.get("/{parent_id}")
async def get_parent(
    parent_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("parents.read"))
):
    repo = ParentRepository()
    parent = await repo.get(db, parent_id)
    
    if not parent or parent.organization_id != tenant.organization_id:
        return success_response(None, "Veli bulunamadı", success=False)
    
    return success_response(parent_to_dict(parent))


@router.put("/{parent_id}")
async def update_parent(
    parent_id: UUID,
    parent: ParentUpdate,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("parents.write"))
):
    repo = ParentRepository()
    db_parent = await repo.get(db, parent_id)
    
    if not db_parent or db_parent.organization_id != tenant.organization_id:
        return success_response(None, "Veli bulunamadı", success=False)
    
    parent_data = parent.model_dump(exclude_unset=True)
    parent_data["updated_by"] = tenant.user_id
    
    updated_parent = await repo.update(db, db_parent, parent_data)
    return success_response(parent_to_dict(updated_parent), "Veli güncellendi")


@router.delete("/{parent_id}")
async def delete_parent(
    parent_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("parents.write"))
):
    repo = ParentRepository()
    db_parent = await repo.get(db, parent_id)
    
    if not db_parent or db_parent.organization_id != tenant.organization_id:
        return success_response(None, "Veli bulunamadı", success=False)
    
    await repo.delete(db, parent_id)
    return success_response(message="Veli silindi")
