from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.schemas.common import BranchCreate, BranchUpdate, OrganizationCreate, OrganizationUpdate
from app.core.database import get_db
from app.core.dependencies import get_current_user, get_tenant_context
from app.core.exceptions import ForbiddenException
from app.core.permissions import PermissionChecker
from app.core.responses import paginate, success_response
from app.core.tenant import TenantContext
from app.infrastructure.models.models import Branch, Organization, User
from app.infrastructure.repositories.base import BaseRepository

router = APIRouter(tags=["Organizations"])


def org_to_dict(o: Organization) -> dict:
    return {
        "id": str(o.id),
        "name": o.name,
        "legal_name": o.legal_name,
        "tax_number": o.tax_number,
        "phone": o.phone,
        "email": o.email,
        "address": o.address,
        "city": o.city,
        "country": o.country,
        "is_active": o.is_active,
        "created_at": o.created_at.isoformat(),
    }


def branch_to_dict(b: Branch) -> dict:
    return {
        "id": str(b.id),
        "organization_id": str(b.organization_id),
        "name": b.name,
        "code": b.code,
        "phone": b.phone,
        "email": b.email,
        "address": b.address,
        "city": b.city,
        "capacity": b.capacity,
        "is_active": b.is_active,
        "created_at": b.created_at.isoformat(),
    }


@router.get("/api/organizations")
async def list_organizations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    tenant: TenantContext = Depends(PermissionChecker("org.read")),
    db: AsyncSession = Depends(get_db),
):
    query = select(Organization).where(Organization.deleted_at.is_(None))
    if not tenant.is_super_admin:
        query = query.where(Organization.id == tenant.organization_id)
    if search:
        query = query.where(Organization.name.ilike(f"%{search}%"))
    query = query.order_by(Organization.name)
    repo = BaseRepository(db, tenant)
    items, total = await repo.paginate(query, page, page_size)
    return success_response(paginate([org_to_dict(o) for o in items], total, page, page_size))


@router.post("/api/organizations")
async def create_organization(
    body: OrganizationCreate,
    tenant: TenantContext = Depends(PermissionChecker("org.write")),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not tenant.is_super_admin:
        raise ForbiddenException()
    org = Organization(**body.model_dump(), created_by=user.id, updated_by=user.id)
    db.add(org)
    await db.flush()
    return success_response(org_to_dict(org), "Kurum oluşturuldu")


@router.get("/api/organizations/{org_id}")
async def get_organization(
    org_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("org.read")),
    db: AsyncSession = Depends(get_db),
):
    repo = BaseRepository(db, tenant)
    org = await repo.get_by_id(org_id, Organization)
    return success_response(org_to_dict(org))


@router.put("/api/organizations/{org_id}")
async def update_organization(
    org_id: UUID,
    body: OrganizationUpdate,
    tenant: TenantContext = Depends(PermissionChecker("org.write")),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = BaseRepository(db, tenant)
    org = await repo.get_by_id(org_id, Organization)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(org, k, v)
    org.updated_by = user.id
    return success_response(org_to_dict(org), "Kurum güncellendi")


@router.delete("/api/organizations/{org_id}")
async def delete_organization(
    org_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("org.write")),
    db: AsyncSession = Depends(get_db),
):
    repo = BaseRepository(db, tenant)
    org = await repo.get_by_id(org_id, Organization)
    org.is_active = False
    await repo.soft_delete(org)
    return success_response(message="Kurum pasife alındı")


@router.get("/api/branches")
async def list_branches(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    organization_id: UUID | None = None,
    tenant: TenantContext = Depends(PermissionChecker("branch.read")),
    db: AsyncSession = Depends(get_db),
):
    query = select(Branch).where(Branch.deleted_at.is_(None))
    query = BaseRepository(db, tenant)._org_filter(query, Branch)
    query = BaseRepository(db, tenant)._branch_filter(query, Branch)
    if organization_id:
        query = query.where(Branch.organization_id == organization_id)
    if search:
        query = query.where(Branch.name.ilike(f"%{search}%"))
    query = query.order_by(Branch.name)
    repo = BaseRepository(db, tenant)
    items, total = await repo.paginate(query, page, page_size)
    return success_response(paginate([branch_to_dict(b) for b in items], total, page, page_size))


@router.post("/api/branches")
async def create_branch(
    body: BranchCreate,
    tenant: TenantContext = Depends(PermissionChecker("branch.write")),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not tenant.can_access_organization(UUID(body.organization_id)):
        raise ForbiddenException()
    branch = Branch(**body.model_dump(), created_by=user.id, updated_by=user.id)
    branch.organization_id = UUID(body.organization_id)
    db.add(branch)
    await db.flush()
    return success_response(branch_to_dict(branch), "Şube oluşturuldu")


@router.get("/api/branches/{branch_id}")
async def get_branch(
    branch_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("branch.read")),
    db: AsyncSession = Depends(get_db),
):
    repo = BaseRepository(db, tenant)
    branch = await repo.get_by_id(branch_id, Branch)
    return success_response(branch_to_dict(branch))


@router.put("/api/branches/{branch_id}")
async def update_branch(
    branch_id: UUID,
    body: BranchUpdate,
    tenant: TenantContext = Depends(PermissionChecker("branch.write")),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = BaseRepository(db, tenant)
    branch = await repo.get_by_id(branch_id, Branch)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(branch, k, v)
    branch.updated_by = user.id
    return success_response(branch_to_dict(branch), "Şube güncellendi")


@router.delete("/api/branches/{branch_id}")
async def delete_branch(
    branch_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("branch.write")),
    db: AsyncSession = Depends(get_db),
):
    repo = BaseRepository(db, tenant)
    branch = await repo.get_by_id(branch_id, Branch)
    branch.is_active = False
    await repo.soft_delete(branch)
    return success_response(message="Şube pasife alındı")
