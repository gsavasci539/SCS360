from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

from app.application.schemas import ClassCreate, ClassUpdate, ClassResponse
from app.repositories import ClassRepository
from app.core.database import get_db
from app.core.dependencies import get_current_user, get_tenant_context
from app.core.permissions import require_permission, PermissionChecker
from app.core.responses import success_response
from app.domain.entities.user import User
from app.core.tenant import TenantContext

router = APIRouter(prefix="/api/classes", tags=["Classes"])


class ClassTransferCreate(BaseModel):
    student_ids: list[UUID] = Field(min_length=1, max_length=1000)
    target_class_id: UUID

    @field_validator("student_ids")
    @classmethod
    def unique_students(cls, values):
        return list(dict.fromkeys(values))


@router.post("", response_model=ClassResponse)
@require_permission("classes.create")
async def create_class(
    class_data: ClassCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user)
):
    repo = ClassRepository()
    class_dict = class_data.model_dump()
    class_dict["created_by"] = current_user.id
    class_dict["organization_id"] = current_user.organization_id
    
    db_class = await repo.create(db, class_dict)
    return success_response(db_class, "Sınıf oluşturuldu")


@router.get("")
async def list_classes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    branch_id: Optional[UUID] = None,
    teacher_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("classes.read"))
):
    repo = ClassRepository()
    
    if branch_id:
        classes = await repo.get_by_branch(db, branch_id, skip, limit)
    elif teacher_id:
        classes = await repo.get_by_teacher(db, teacher_id, skip, limit)
    else:
        classes = await repo.get_by_organization(db, tenant.organization_id, skip, limit)
    
    print(f"DEBUG: List classes returning {len(classes)} classes")
    if classes:
        print(f"DEBUG: Sample class: {classes[0]}")
        print(f"DEBUG: teacher_name in sample: {classes[0].get('teacher_name')}")
    
    return success_response(classes)


@router.get("/{class_id}")
async def get_class(
    class_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("classes.read"))
):
    from app.infrastructure.models.models import User
    from sqlalchemy import select
    
    print(f"DEBUG: Class endpoint called with class_id={class_id}")
    
    repo = ClassRepository()
    db_class = await repo.get(db, class_id)
    
    if not db_class or db_class.organization_id != tenant.organization_id:
        print(f"DEBUG: Class not found or organization mismatch")
        return success_response(None, "Sınıf bulunamadı", success=False)
    
    print(f"DEBUG: Class found: {db_class.name}")
    
    # Get teacher for this class using teacher_id
    teacher_name = ""
    if db_class.teacher_id:
        teacher_result = await db.execute(
            select(User.first_name, User.last_name)
            .where(User.id == db_class.teacher_id)
        )
        teacher_row = teacher_result.first()
        teacher_name = f"{teacher_row[0]} {teacher_row[1]}" if teacher_row else ""
    
    print(f"DEBUG: teacher_name={teacher_name}")
    
    # Convert to dict and add teacher_name
    class_dict = {
        "id": str(db_class.id),
        "name": db_class.name,
        "code": db_class.code,
        "capacity": db_class.capacity,
        "academic_year": db_class.academic_year,
        "is_active": db_class.is_active,
        "status": "ACTIVE" if db_class.is_active else "PASSIVE",
        "teacher_name": teacher_name,
        "teacher_id": str(db_class.teacher_id) if db_class.teacher_id else None,
        "organization_id": str(db_class.organization_id),
        "branch_id": str(db_class.branch_id),
        "created_at": db_class.created_at,
        "updated_at": db_class.updated_at
    }
    
    print(f"DEBUG: Response data keys: {list(class_dict.keys())}")
    print(f"DEBUG: teacher_name in response: {class_dict.get('teacher_name')}")
    
    return success_response(class_dict)


@router.put("/{class_id}", response_model=ClassResponse)
async def update_class(
    class_id: UUID,
    class_data: ClassUpdate,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("classes.write"))
):
    repo = ClassRepository()
    db_class = await repo.get(db, class_id)
    
    if not db_class or db_class.organization_id != tenant.organization_id:
        return success_response(None, "Sınıf bulunamadı", success=False)
    
    class_dict = class_data.model_dump(exclude_unset=True)
    class_dict["updated_by"] = tenant.user_id
    
    updated_class = await repo.update(db, db_class, class_dict)
    return success_response(updated_class, "Sınıf güncellendi")


@router.delete("/{class_id}")
async def delete_class(
    class_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("classes.write"))
):
    repo = ClassRepository()
    db_class = await repo.get(db, class_id)
    
    if not db_class or db_class.organization_id != tenant.organization_id:
        return success_response(None, "Sınıf bulunamadı", success=False)
    
    await repo.delete(db, class_id)
    return success_response(message="Sınıf silindi")


@router.post("/{class_id}/transfer-students")
async def transfer_students(
    class_id: UUID,
    transfer: ClassTransferCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("class.write")),
):
    """Transfer students from one class to another"""
    from app.infrastructure.models.models import Student, ClassRoom as Class
    from app.infrastructure.repositories.base import BaseRepository
    from app.core.exceptions import ValidationException
    repo = BaseRepository(db, tenant)
    source_class = await repo.get_by_id(class_id, Class)
    target_class = await repo.get_by_id(transfer.target_class_id, Class)
    if source_class.organization_id != target_class.organization_id or source_class.branch_id != target_class.branch_id:
        raise ValidationException("Sınıf aktarımı aynı kurum ve şube içinde yapılmalıdır; şube değişimi için öğrenci kaydını düzenleyin")
    
    # Get students to transfer
    students_result = await db.execute(
        select(Student).where(
            Student.id.in_(transfer.student_ids),
            Student.class_id == class_id
        )
    )
    students = students_result.scalars().all()
    
    if len(students) != len(transfer.student_ids):
        raise ValidationException("Belirtilen öğrencilerin tümü kaynak sınıfta olmalıdır")
    
    # Transfer students
    transferred_count = 0
    for student in students:
        student.class_id = transfer.target_class_id
        student.updated_by = current_user.id
        transferred_count += 1
    
    await db.commit()
    
    return success_response({
        "source_class_id": str(class_id),
        "target_class_id": str(transfer.target_class_id),
        "transferred_count": transferred_count,
        "student_ids": [str(s.id) for s in students]
    }, f"{transferred_count} öğrenci başarıyla transfer edildi")
