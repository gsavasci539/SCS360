from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, ConfigDict, Field

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
from app.infrastructure.models.models import Branch, Organization, Role, User, UserBranch, UserRole, UserStatus
from app.infrastructure.repositories.base import BaseRepository

router = APIRouter(tags=["Users"])


def require_account_access(user, tenant):
    if user.is_super_admin and not tenant.is_super_admin:
        raise ForbiddenException("Platform hesabını yalnız ana yönetici düzenleyebilir")


def user_dict(u: User) -> dict:
    return {
        "id": str(u.id),
        "email": u.email,
        "first_name": u.first_name,
        "last_name": u.last_name,
        "phone": u.phone,
        "position": u.position,
        "department": u.department,
        "status": u.status.value,
        "organization_id": str(u.organization_id) if u.organization_id else None,
        "is_super_admin": u.is_super_admin,
        "roles": [{"id": str(r.id), "name": r.name, "slug": r.slug} for r in u.roles],
    }


@router.get("/api/users")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    search: str | None = None,
    tenant: TenantContext = Depends(PermissionChecker("user.read")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    query = select(User).where(User.deleted_at.is_(None)).options(selectinload(User.roles))
    repo = BaseRepository(db, tenant)
    if not tenant.is_super_admin:
        query = query.where(User.organization_id == tenant.organization_id, User.is_super_admin.is_(False))
    if search:
        query = query.where(
            User.first_name.ilike(f"%{search}%")
            | User.last_name.ilike(f"%{search}%")
            | User.email.ilike(f"%{search}%")
        )
    items, total = await repo.paginate(query.order_by(User.last_name), page, page_size)
    return success_response(paginate([user_dict(u) for u in items], total, page, page_size))


@router.get("/api/users/options")
async def user_options(organization_id: UUID | None = None, tenant: TenantContext = Depends(PermissionChecker("user.write")), db: AsyncSession = Depends(get_db, scope="function")):
    target = organization_id or tenant.organization_id
    if target and not tenant.can_access_organization(target):
        raise ForbiddenException()
    orgs = select(Organization).where(Organization.deleted_at.is_(None))
    if not tenant.is_super_admin:
        orgs = orgs.where(Organization.id == tenant.organization_id)
    organizations = (await db.execute(orgs.order_by(Organization.name, Organization.id).limit(1000))).scalars().all()
    roles, branches = [], []
    if target:
        await BaseRepository(db, tenant).require_related(target, Organization)
        roles = (await db.execute(select(Role).where(Role.deleted_at.is_(None), (Role.organization_id == target) | Role.organization_id.is_(None)).order_by(Role.name))).scalars().all()
        branches = (await db.execute(select(Branch).where(Branch.deleted_at.is_(None), Branch.organization_id == target).order_by(Branch.name))).scalars().all()
    return success_response({"organizations": [{"id": str(row.id), "name": row.name} for row in organizations],
        "roles": [{"id": str(row.id), "name": row.name, "slug": row.slug, "organization_id": str(row.organization_id) if row.organization_id else None} for row in roles],
        "branches": [{"id": str(row.id), "name": row.name} for row in branches]})


class RoleCatalogRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    organization_id: UUID


@router.post("/api/users/role-catalog")
async def complete_role_catalog(body: RoleCatalogRequest, tenant: TenantContext = Depends(PermissionChecker("user.write")), db: AsyncSession = Depends(get_db, scope="function")):
    from app.core.role_catalog import default_permissions, institution_roles
    from app.infrastructure.models.models import Permission
    from app.application.services.platform_service import lock_organization, audit, commit
    from types import SimpleNamespace
    if not (tenant.is_super_admin or tenant.platform_admin or {"owner", "org_admin"}.intersection(tenant.role_slugs)) or not tenant.has_permission("role.write"):
        raise ForbiddenException("Standart rolleri yalnız kurum sahibi veya kurum yöneticisi tamamlayabilir")
    if not tenant.can_access_organization(body.organization_id):
        raise ForbiddenException()
    org = await lock_organization(db, body.organization_id)
    roles = (await db.execute(select(Role).where(Role.organization_id == org.id, Role.deleted_at.is_(None)))).scalars().all()
    codes = default_permissions("owner")
    permissions = list((await db.execute(select(Permission).where(Permission.code.in_(codes)))).scalars())
    if codes - {row.code for row in permissions}:
        raise ConflictException("Kurum rol kataloğu için platform izin kurulumu tamamlanmalı")
    created = institution_roles(org.id, permissions, [row.slug for row in roles])
    db.add_all(created)
    if created:
        audit(db, SimpleNamespace(id=tenant.user_id), org, "INSTITUTION_ROLE_CATALOG_COMPLETED", {"slugs": [row.slug for row in created]})
    await commit(db)
    return success_response({"created_count": len(created)})


@router.post("/api/users")
async def create_user(
    body: UserCreate,
    tenant: TenantContext = Depends(PermissionChecker("user.write")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    existing = await db.execute(select(User).where(User.email == body.email.lower()))
    if existing.scalar_one_or_none():
        raise ConflictException("Bu e-posta zaten kayıtlı")
    org_id = UUID(body.organization_id) if body.organization_id else tenant.organization_id
    if not org_id or not tenant.can_access_organization(org_id):
        raise ForbiddenException()
    await BaseRepository(db, tenant).require_related(org_id, Organization)
    user = User(
        organization_id=org_id,
        email=body.email.lower(),
        password_hash=hash_password(body.password),
        first_name=body.first_name,
        last_name=body.last_name,
        phone=body.phone,
        position=body.position,
        department=body.department,
        created_by=current_user.id,
        updated_by=current_user.id,
        roles=[],
        branches=[],
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictException("Bu e-posta zaten kayıtlı veya kullanıcı ilişkisi geçersiz") from exc
    return success_response(user_dict(user), "Kullanıcı oluşturuldu")


@router.get("/api/users/{user_id}")
async def get_user(
    user_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("user.read")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    repo = BaseRepository(db, tenant)
    user = await repo.get_by_id(user_id, User)
    require_account_access(user, tenant)
    await db.refresh(user, ["roles"])
    return success_response(user_dict(user))


@router.put("/api/users/{user_id}")
async def update_user(
    user_id: UUID,
    body: UserUpdate,
    tenant: TenantContext = Depends(PermissionChecker("user.write")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    repo = BaseRepository(db, tenant)
    user = await repo.get_by_id(user_id, User)
    require_account_access(user, tenant)
    await db.refresh(user, ["roles"])
    data = body.model_dump(exclude_unset=True)
    if user.is_super_admin and "status" in data and data["status"] != "ACTIVE":
        raise ConflictException("Ana platform hesabı kullanıcı ekranından kapatılamaz")
    if "email" in data:
        table = User.__table__
        if (await db.execute(select(table.c.id).where(table.c.email == data["email"], table.c.id != user.id))).first():
            raise ConflictException("Bu e-posta zaten kayıtlı")
    if "password" in data and data["password"]:
        user.password_hash = hash_password(data.pop("password"))
    if "status" in data and data["status"]:
        data["status"] = UserStatus(data["status"])
    for k, v in data.items():
        setattr(user, k, v)
    user.updated_by = current_user.id
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictException("Bu e-posta zaten kayıtlı veya kullanıcı ilişkisi geçersiz") from exc
    return success_response(user_dict(user), "Kullanıcı güncellendi")


@router.delete("/api/users/{user_id}")
async def delete_user(
    user_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("user.write")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    repo = BaseRepository(db, tenant)
    user = await repo.get_by_id(user_id, User)
    require_account_access(user, tenant)
    if user.is_super_admin:
        raise ConflictException("Ana platform hesabı kullanıcı ekranından silinemez")
    user.status = UserStatus.PASSIVE
    await repo.soft_delete(user)
    return success_response(message="Kullanıcı pasife alındı")


@router.post("/api/users/{user_id}/roles")
async def assign_roles(
    user_id: UUID,
    body: RoleAssignRequest,
    tenant: TenantContext = Depends(PermissionChecker("user.write")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    repo = BaseRepository(db, tenant)
    user = await repo.get_by_id(user_id, User)
    require_account_access(user, tenant)
    role_ids = list(dict.fromkeys(UUID(role_id) for role_id in body.role_ids))
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
    db: AsyncSession = Depends(get_db, scope="function"),
):
    repo = BaseRepository(db, tenant)
    user = await repo.get_by_id(user_id, User)
    require_account_access(user, tenant)
    branch_ids = list(dict.fromkeys(UUID(branch_id) for branch_id in body.branch_ids))
    branches = [await repo.require_related(branch_id, Branch) for branch_id in branch_ids]
    if any(branch.organization_id != user.organization_id for branch in branches):
        raise ForbiddenException()
    await db.execute(UserBranch.__table__.delete().where(UserBranch.user_id == user_id))
    for branch_id in branch_ids:
        db.add(UserBranch(user_id=user_id, branch_id=branch_id, assigned_by=tenant.user_id))
    return success_response(message="Şubeler atandı")


class UserAccessWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role_ids: list[UUID] = Field(max_length=1000)
    branch_ids: list[UUID] = Field(max_length=1000)


@router.put("/api/users/{user_id}/access")
async def assign_access(user_id: UUID, body: UserAccessWrite, tenant: TenantContext = Depends(PermissionChecker("user.write")), db: AsyncSession = Depends(get_db, scope="function")):
    await assign_roles(user_id, RoleAssignRequest(role_ids=[str(value) for value in body.role_ids]), tenant, db)
    await assign_branches(user_id, BranchAssignRequest(branch_ids=[str(value) for value in body.branch_ids]), tenant, db)
    return success_response(message="Rol ve şube erişimi kaydedildi")


@router.get("/api/roles")
async def list_roles(
    tenant: TenantContext = Depends(PermissionChecker("user.read")),
    db: AsyncSession = Depends(get_db, scope="function"),
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
    db: AsyncSession = Depends(get_db, scope="function"),
):
    from app.infrastructure.models.models import Permission

    result = await db.execute(select(Permission).order_by(Permission.module, Permission.code))
    perms = result.scalars().all()
    return success_response(
        [{"id": str(p.id), "code": p.code, "name": p.name, "module": p.module} for p in perms]
    )
