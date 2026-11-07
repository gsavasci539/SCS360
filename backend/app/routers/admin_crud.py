from datetime import datetime, timezone
from uuid import UUID
from pydantic import BaseModel

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import delete, or_, select, and_
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
from app.core.tenant import TenantContext
from app.infrastructure.models.models import (
    Parent,
    ParentRelationType,
    Permission,
    Role,
    RolePermission,
    User,
    Student,
    StudentParent,
    ChatMessage,
)
from app.infrastructure.repositories.base import BaseRepository

router = APIRouter(tags=["Parents & Access Control"])


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


@router.get("/api/users/{user_id}/roles")
async def get_user_roles(
    user_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("user.read")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    user = (await db.execute(select(User).options(selectinload(User.roles)).where(User.id == user_id, User.deleted_at.is_(None)))).scalar_one_or_none()
    if not user:
        raise NotFoundException("Kullanıcı bulunamadı")
    if not tenant.is_super_admin and (user.organization_id != tenant.organization_id or user.is_super_admin):
        raise ForbiddenException()
    return success_response([role_dict(role) for role in user.roles])


@router.get("/api/users/{user_id}/branches")
async def get_user_branches(
    user_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("user.read")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    user = (await db.execute(select(User).options(selectinload(User.branches)).where(User.id == user_id, User.deleted_at.is_(None)))).scalar_one_or_none()
    if not user:
        raise NotFoundException("Kullanıcı bulunamadı")
    if not tenant.is_super_admin and (user.organization_id != tenant.organization_id or user.is_super_admin):
        raise ForbiddenException()
    return success_response([{"id": str(branch.id), "name": branch.name, "code": branch.code} for branch in user.branches])


@router.get("/api/roles/{role_id}")
async def get_role(
    role_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("user.read", "role.read")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    role = (await db.execute(select(Role).where(Role.id == role_id, Role.deleted_at.is_(None)))).scalar_one_or_none()
    if not role:
        raise NotFoundException("Rol bulunamadı")
    if not tenant.is_super_admin and role.organization_id not in (None, tenant.organization_id):
        raise ForbiddenException()
    return success_response(role_dict(role))


@router.post("/api/roles")
async def create_role(
    body: dict,
    tenant: TenantContext = Depends(PermissionChecker("user.write", "role.write")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    name = str(body.get("name", "")).strip()
    slug = str(body.get("slug", "")).strip().lower()
    if not name or not slug:
        raise ValidationException("Rol adı ve kısa kodu zorunludur")
    organization_id = tenant.organization_id
    existing = (await db.execute(select(Role).where(Role.slug == slug, Role.organization_id == organization_id, Role.deleted_at.is_(None)))).scalar_one_or_none()
    if existing:
        raise ConflictException("Bu rol kodu zaten mevcut")
    role = Role(name=name, slug=slug, description=body.get("description"), organization_id=organization_id, is_system=False)
    db.add(role)
    await db.flush()
    return success_response(role_dict(role), "Rol oluşturuldu")


@router.get("/api/roles/{role_id}/permissions")
async def get_role_permissions(
    role_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("user.read", "role.read")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    role = (await db.execute(select(Role).options(selectinload(Role.permissions)).where(Role.id == role_id, Role.deleted_at.is_(None)))).scalar_one_or_none()
    if not role:
        raise NotFoundException("Rol bulunamadı")
    if not tenant.is_super_admin and role.organization_id not in (None, tenant.organization_id):
        raise ForbiddenException()
    return success_response([permission_dict(permission) for permission in role.permissions])


async def _replace_role_permissions(role_id: UUID, permission_ids: list[str], tenant: TenantContext, db: AsyncSession):
    role = (await db.execute(select(Role).where(Role.id == role_id, Role.deleted_at.is_(None)))).scalar_one_or_none()
    if not role:
        raise NotFoundException("Rol bulunamadı")
    if not tenant.is_super_admin and (role.is_system or role.organization_id != tenant.organization_id):
        raise ForbiddenException("Bu rolün izinleri değiştirilemez")
    ids = [UUID(value) for value in permission_ids]
    found = list((await db.execute(select(Permission.id).where(Permission.id.in_(ids)))).scalars().all()) if ids else []
    if len(found) != len(set(ids)):
        raise ValidationException("Geçersiz izin kaydı")
    await db.execute(delete(RolePermission).where(RolePermission.role_id == role_id))
    for permission_id in ids:
        db.add(RolePermission(role_id=role_id, permission_id=permission_id))
    return success_response(message="Rol izinleri güncellendi")


@router.post("/api/roles/{role_id}/permissions")
async def assign_role_permissions_post(
    role_id: UUID,
    body: dict,
    tenant: TenantContext = Depends(PermissionChecker("user.write", "role.write")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    return await _replace_role_permissions(role_id, body.get("permission_ids", []), tenant, db)


@router.put("/api/roles/{role_id}/permissions")
async def assign_role_permissions_put(
    role_id: UUID,
    body: dict,
    tenant: TenantContext = Depends(PermissionChecker("user.write", "role.write")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    return await _replace_role_permissions(role_id, body.get("permission_ids", []), tenant, db)


class ChatMessageCreate(BaseModel):
    message: str


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
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("messaging.read")),
):
    from app.application.services import teacher_chat_service
    return success_response(await teacher_chat_service.history(db, tenant, student_id, parent_id))


@router.post("/api/admin/chat/{student_id}")
async def send_admin_chat_message(
    student_id: UUID,
    message_data: ChatMessageCreate,
    parent_id: UUID | None = None,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("messaging.send")),
):
    from app.application.services import teacher_chat_service
    return success_response(await teacher_chat_service.send(db, tenant, student_id, message_data.message, parent_id))
