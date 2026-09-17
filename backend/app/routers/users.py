from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.application.schemas.common import (
    BranchAssignRequest,
    RoleAssignRequest,
    UserCreate,
    UserUpdate,
)
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import ConflictException, ForbiddenException
from app.core.permissions import PermissionChecker
from app.core.responses import paginate, success_response
from app.core.security import hash_password
from app.core.tenant import TenantContext
from app.infrastructure.models.models import Branch, Role, User, UserBranch, UserRole, UserStatus
from app.infrastructure.repositories.base import BaseRepository

router = APIRouter(tags=["Users"])


def user_dict(u: User) -> dict:
    return {
        "id": str(u.id),
        "email": u.email,
        "first_name": u.first_name,
        "last_name": u.last_name,
        "phone": u.phone,
        "status": u.status.value,
        "organization_id": str(u.organization_id) if u.organization_id else None,
        "roles": [{"id": str(r.id), "name": r.name, "slug": r.slug} for r in u.roles],
    }


@router.get("/api/users")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    tenant: TenantContext = Depends(PermissionChecker("user.read")),
    db: AsyncSession = Depends(get_db),
):
    query = select(User).where(User.deleted_at.is_(None)).options(selectinload(User.roles))
    repo = BaseRepository(db, tenant)
    if not tenant.is_super_admin:
        query = query.where(User.organization_id == tenant.organization_id)
    if search:
        query = query.where(
            User.first_name.ilike(f"%{search}%")
            | User.last_name.ilike(f"%{search}%")
            | User.email.ilike(f"%{search}%")
        )
    items, total = await repo.paginate(query.order_by(User.last_name), page, page_size)
    return success_response(paginate([user_dict(u) for u in items], total, page, page_size))


@router.post("/api/users")
async def create_user(
    body: UserCreate,
    tenant: TenantContext = Depends(PermissionChecker("user.write")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(User).where(User.email == body.email.lower()))
    if existing.scalar_one_or_none():
        raise ConflictException("Bu e-posta zaten kayıtlı")
    org_id = UUID(body.organization_id) if body.organization_id else tenant.organization_id
    if not org_id or not tenant.can_access_organization(org_id):
        raise ForbiddenException()
    user = User(
        organization_id=org_id,
        email=body.email.lower(),
        password_hash=hash_password(body.password),
        first_name=body.first_name,
        last_name=body.last_name,
        phone=body.phone,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(user)
    await db.flush()
    return success_response(user_dict(user), "Kullanıcı oluşturuldu")


@router.get("/api/users/{user_id}")
async def get_user(
    user_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("user.read")),
    db: AsyncSession = Depends(get_db),
):
    repo = BaseRepository(db, tenant)
    user = await repo.get_by_id(user_id, User)
    return success_response(user_dict(user))


@router.put("/api/users/{user_id}")
async def update_user(
    user_id: UUID,
    body: UserUpdate,
    tenant: TenantContext = Depends(PermissionChecker("user.write")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = BaseRepository(db, tenant)
    user = await repo.get_by_id(user_id, User)
    data = body.model_dump(exclude_unset=True)
    if "password" in data and data["password"]:
        user.password_hash = hash_password(data.pop("password"))
    if "status" in data and data["status"]:
        data["status"] = UserStatus(data["status"])
    for k, v in data.items():
        setattr(user, k, v)
    user.updated_by = current_user.id
    return success_response(user_dict(user), "Kullanıcı güncellendi")


@router.delete("/api/users/{user_id}")
async def delete_user(
    user_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("user.write")),
    db: AsyncSession = Depends(get_db),
):
    repo = BaseRepository(db, tenant)
    user = await repo.get_by_id(user_id, User)
    user.status = UserStatus.PASSIVE
    await repo.soft_delete(user)
    return success_response(message="Kullanıcı pasife alındı")


@router.post("/api/users/{user_id}/roles")
async def assign_roles(
    user_id: UUID,
    body: RoleAssignRequest,
    tenant: TenantContext = Depends(PermissionChecker("user.write")),
    db: AsyncSession = Depends(get_db),
):
    repo = BaseRepository(db, tenant)
    await repo.get_by_id(user_id, User)
    role_ids = [UUID(role_id) for role_id in body.role_ids]
    roles = list(
        (await db.execute(select(Role).where(Role.id.in_(role_ids), Role.deleted_at.is_(None))))
        .scalars()
        .all()
    )
    if len(roles) != len(set(role_ids)):
        raise ConflictException("Geçersiz rol kaydı")
    if not tenant.is_super_admin and any(
        role.organization_id not in (None, tenant.organization_id) for role in roles
    ):
        raise ForbiddenException()
    await db.execute(UserRole.__table__.delete().where(UserRole.user_id == user_id))
    for role_id in role_ids:
        db.add(UserRole(user_id=user_id, role_id=role_id, assigned_by=tenant.user_id))
    return success_response(message="Roller atandı")


@router.post("/api/users/{user_id}/branches")
async def assign_branches(
    user_id: UUID,
    body: BranchAssignRequest,
    tenant: TenantContext = Depends(PermissionChecker("user.write")),
    db: AsyncSession = Depends(get_db),
):
    repo = BaseRepository(db, tenant)
    user = await repo.get_by_id(user_id, User)
    branch_ids = [UUID(branch_id) for branch_id in body.branch_ids]
    branches = [await repo.require_related(branch_id, Branch) for branch_id in branch_ids]
    if any(branch.organization_id != user.organization_id for branch in branches):
        raise ForbiddenException()
    await db.execute(UserBranch.__table__.delete().where(UserBranch.user_id == user_id))
    for branch_id in branch_ids:
        db.add(UserBranch(user_id=user_id, branch_id=branch_id, assigned_by=tenant.user_id))
    return success_response(message="Şubeler atandı")


@router.get("/api/roles")
async def list_roles(
    tenant: TenantContext = Depends(PermissionChecker("user.read")),
    db: AsyncSession = Depends(get_db),
):
    query = select(Role).where(Role.deleted_at.is_(None))
    if not tenant.is_super_admin:
        query = query.where(
            (Role.organization_id == tenant.organization_id) | Role.is_system.is_(True)
        )
    result = await db.execute(query)
    roles = result.scalars().all()
    return success_response([{"id": str(r.id), "name": r.name, "slug": r.slug} for r in roles])


@router.get("/api/permissions")
async def list_permissions(
    tenant: TenantContext = Depends(PermissionChecker("user.read")),
    db: AsyncSession = Depends(get_db),
):
    from app.infrastructure.models.models import Permission

    result = await db.execute(select(Permission).order_by(Permission.module, Permission.code))
    perms = result.scalars().all()
    return success_response(
        [{"id": str(p.id), "code": p.code, "name": p.name, "module": p.module} for p in perms]
    )
