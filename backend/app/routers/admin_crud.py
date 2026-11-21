from datetime import datetime, timezone
import re
from uuid import UUID
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import delete, or_, select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from app.core.permissions import PermissionChecker
from app.core.responses import paginate, success_response
from app.core.role_catalog import ROLE_NAMES
from app.core.tenant import TenantContext
from app.infrastructure.models.models import (
    Parent,
    ParentRelationType,
    Organization,
    Branch,
    Permission,
    Role,
    RolePermission,
    User,
    UserBranch,
    UserRole,
    Student,
    StudentParent,
    ChatMessage,
)
from app.infrastructure.repositories.base import BaseRepository

from app.routers.staff_chat_attachments import router as staff_chat_attachments

router = APIRouter(tags=["Parents & Access Control"])
router.include_router(staff_chat_attachments, prefix="/api/admin")


def permission_dict(permission: Permission) -> dict:
    return {
        "id": str(permission.id),
        "code": permission.code,
        "name": permission.name,
        "module": permission.module,
        "description": permission.description,
    }


def role_dict(role: Role) -> dict:
    return {
        "id": str(role.id),
        "name": role.name,
        "slug": role.slug,
        "description": role.description,
        "is_system": role.is_system,
        "organization_id": str(role.organization_id) if role.organization_id else None,
    }


def require_role_workspace(tenant: TenantContext):
    if tenant.organization_id is None or tenant.is_super_admin:
        raise ForbiddenException("Önce kurum çalışma alanını seçin")


class InstitutionRoleDraft(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    request_id: UUID | None = None


class RolePermissionMatrix(BaseModel):
    permission_ids: list[UUID] = Field(max_length=1000)
    expected_permission_ids: list[UUID] | None = Field(default=None, max_length=1000)


@router.get("/api/users/{user_id}/roles")
async def get_user_roles(
    user_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("user.read")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    user = await BaseRepository(db, tenant).get_by_id(user_id, User)
    if not tenant.is_super_admin and (user.organization_id != tenant.organization_id or user.is_super_admin):
        raise ForbiddenException()
    roles, links = Role.__table__, UserRole.__table__
    rows = (await db.execute(select(roles.c.id, roles.c.name, roles.c.slug, roles.c.description,
        roles.c.is_system, roles.c.organization_id).join(links, links.c.role_id == roles.c.id).where(
            links.c.user_id == user_id, roles.c.deleted_at.is_(None),
            (roles.c.organization_id == user.organization_id) | roles.c.organization_id.is_(None)
    ).order_by(roles.c.name, roles.c.id))).all()
    return success_response([role_dict(role) for role in rows])


@router.get("/api/users/{user_id}/branches")
async def get_user_branches(
    user_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("user.read")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    user = await BaseRepository(db, tenant).get_by_id(user_id, User)
    if not tenant.is_super_admin and (user.organization_id != tenant.organization_id or user.is_super_admin):
        raise ForbiddenException()
    branches, links = Branch.__table__, UserBranch.__table__
    query = select(branches.c.id, branches.c.name, branches.c.code).join(links, links.c.branch_id == branches.c.id).where(
        links.c.user_id == user_id, branches.c.organization_id == user.organization_id, branches.c.deleted_at.is_(None))
    if tenant.branch_ids:
        query = query.where(branches.c.id.in_(tenant.branch_ids))
    rows = (await db.execute(query.order_by(branches.c.name, branches.c.id))).all()
    return success_response([{"id": str(branch.id), "name": branch.name, "code": branch.code} for branch in rows])


@router.get("/api/roles/{role_id}")
async def get_role(
    role_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("user.read", "role.read", "role.write")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    require_role_workspace(tenant)
    role = (await db.execute(select(Role).where(Role.id == role_id, Role.deleted_at.is_(None)))).scalar_one_or_none()
    if not role:
        raise NotFoundException("Rol bulunamadı")
    if not tenant.is_super_admin and role.organization_id not in (None, tenant.organization_id):
        raise ForbiddenException()
    return success_response(role_dict(role))


@router.post("/api/roles")
async def create_role(
    body: InstitutionRoleDraft,
    tenant: TenantContext = Depends(PermissionChecker("user.write", "role.write")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    require_role_workspace(tenant)
    name = body.name.strip()
    slug = body.slug.strip().lower()
    if not name or not slug:
        raise ValidationException("Rol adı ve kısa kodu zorunludur")
    if not re.fullmatch(r"[a-z][a-z0-9_-]*", slug):
        raise ValidationException("Rol kodu küçük Latin harf, rakam, tire ve alt çizgi içerebilir")
    if slug in ROLE_NAMES or slug in {"super_admin", "superadmin", "admin", "teacher1", "teacher2", "teacher3"}:
        raise ValidationException("Bu rol kodu standart roller için ayrılmış")
    organization_id = tenant.organization_id
    await db.execute(update(Organization).where(Organization.id == organization_id).values(updated_at=Organization.updated_at))
    description = body.description.strip() or None if body.description else None
    if body.request_id is not None:
        previous = await db.scalar(select(Role).where(Role.id == body.request_id,
            Role.organization_id == organization_id, Role.deleted_at.is_(None)))
        if previous is not None:
            if previous.is_system or (previous.name, previous.slug, previous.description) != (name, slug, description):
                raise ConflictException("İşlem kimliği farklı rol bilgileri için kullanılmış")
            return success_response(role_dict(previous))
        if await db.scalar(select(Role.__table__.c.id).where(Role.__table__.c.id == body.request_id)) is not None:
            raise ConflictException("İşlem kimliği kullanılamıyor")
    existing = (await db.execute(select(Role).where(Role.slug == slug, Role.organization_id == organization_id, Role.deleted_at.is_(None)))).scalar_one_or_none()
    if existing:
        raise ConflictException("Bu rol kodu zaten mevcut")
    role = Role(name=name, slug=slug, description=description, organization_id=organization_id, is_system=False)
    if body.request_id is not None:
        role.id = body.request_id
    db.add(role)
    await db.flush()
    return success_response(role_dict(role), "Rol oluşturuldu")


@router.get("/api/roles/{role_id}/permissions")
async def get_role_permissions(
    role_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("user.read", "role.read", "role.write")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    require_role_workspace(tenant)
    role = (await db.execute(select(Role).options(selectinload(Role.permissions)).where(Role.id == role_id, Role.deleted_at.is_(None)))).scalar_one_or_none()
    if not role:
        raise NotFoundException("Rol bulunamadı")
    if not tenant.is_super_admin and role.organization_id not in (None, tenant.organization_id):
        raise ForbiddenException()
    return success_response([permission_dict(permission) for permission in role.permissions])


async def _replace_role_permissions(role_id: UUID, body: RolePermissionMatrix, tenant: TenantContext, db: AsyncSession):
    require_role_workspace(tenant)
    role = (await db.execute(select(Role).where(Role.id == role_id, Role.deleted_at.is_(None)).with_for_update())).scalar_one_or_none()
    if not role:
        raise NotFoundException("Rol bulunamadı")
    if role.is_system or role.organization_id != tenant.organization_id:
        raise ForbiddenException("Bu rolün izinleri değiştirilemez")
    await db.execute(update(Role).where(Role.id == role_id).values(updated_at=Role.updated_at))
    ids = set(body.permission_ids)
    current = set((await db.scalars(select(RolePermission.permission_id).where(RolePermission.role_id == role_id))).all())
    permissions = dict((await db.execute(select(Permission.id, Permission.code).where(Permission.id.in_(ids | current)))).all())
    if ids - permissions.keys():
        raise ValidationException("Geçersiz izin kaydı")
    if any(not tenant.has_permission(permissions[identifier]) for identifier in ids ^ current if identifier in permissions):
        raise ForbiddenException("Kendi yetki kapsamınız dışındaki izinleri değiştiremezsiniz")
    if ids == current:
        return success_response({"role_id": str(role_id), "permission_ids": sorted(map(str, ids))})
    if body.expected_permission_ids is not None and set(body.expected_permission_ids) != current:
        raise ConflictException("Rol izinleri değişti. Güncel kayıtları yeniden açın.")
    if current - ids:
        await db.execute(delete(RolePermission).where(RolePermission.role_id == role_id,
            RolePermission.permission_id.in_(current - ids)))
    for permission_id in ids - current:
        db.add(RolePermission(role_id=role_id, permission_id=permission_id))
    await db.flush()
    return success_response({"role_id": str(role_id), "permission_ids": sorted(map(str, ids))})


@router.post("/api/roles/{role_id}/permissions")
async def assign_role_permissions_post(
    role_id: UUID,
    body: RolePermissionMatrix,
    tenant: TenantContext = Depends(PermissionChecker("user.write", "role.write")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    return await _replace_role_permissions(role_id, body, tenant, db)


@router.put("/api/roles/{role_id}/permissions")
async def assign_role_permissions_put(
    role_id: UUID,
    body: RolePermissionMatrix,
    tenant: TenantContext = Depends(PermissionChecker("user.write", "role.write")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    return await _replace_role_permissions(role_id, body, tenant, db)


class ChatMessageCreate(BaseModel):
    message: str
    request_id: UUID | None = None


@router.get("/api/admin/students")
async def get_all_students(
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("student.read"))
):
    """Get all students for admin to chat with"""
    from app.infrastructure.models.models import Student, StudentParent, Parent, ClassRoom
    
    students_result = await db.execute(
        select(Student, ClassRoom)
        .outerjoin(ClassRoom, Student.class_id == ClassRoom.id)
        .where(Student.deleted_at.is_(None))
        .where(Student.organization_id == tenant.organization_id)
    )
    
    students_data = []
    for student, cls in students_result:
        # Get parent info for this student
        parent_result = await db.execute(
            select(StudentParent, Parent)
            .join(Parent, StudentParent.parent_id == Parent.id)
            .where(StudentParent.student_id == student.id, Parent.organization_id == student.organization_id,
                Parent.deleted_at.is_(None), Parent.user_id.is_not(None))
        )
        
        for student_parent, parent in parent_result:
            students_data.append({
                "student_id": str(student.id),
                "student_name": f"{student.first_name} {student.last_name}",
                "class_name": cls.name if cls else None,
                "parent_id": str(parent.user_id),
                "parent_name": f"{parent.first_name} {parent.last_name}",
                "is_primary": student_parent.is_primary
            })
    
    return success_response(students_data)


@router.get("/api/admin/chat/{student_id}")
async def get_admin_chat_messages(
    student_id: UUID,
    parent_id: UUID | None = None,
    branch_id: UUID | None = None,
    limit: int | None = Query(None, ge=1, le=100),
    before_id: UUID | None = None,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("messaging.read")),
):
    from app.application.services import teacher_chat_service
    return success_response(await teacher_chat_service.history(db, tenant, student_id, parent_id, branch_id,
        limit=limit, before_id=before_id))


@router.post("/api/admin/chat/{student_id}")
async def send_admin_chat_message(
    student_id: UUID,
    message_data: ChatMessageCreate,
    parent_id: UUID | None = None,
    branch_id: UUID | None = None,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("messaging.send")),
):
    from app.application.services import teacher_chat_service
    return success_response(await teacher_chat_service.send(db, tenant, student_id, message_data.message, parent_id,
        message_data.request_id, branch_id=branch_id))
