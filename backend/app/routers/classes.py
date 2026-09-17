from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field

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
    student_ids: list[UUID]
    target_class_id: UUID


@router.post("", response_model=ClassResponse)
@require_permission("classes.create")
async def create_class(
    class_data: ClassCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = ClassRepository()
    class_dict = class_data.model_dump()
    class_dict["created_by"] = current_user.id
    class_dict["organization_id"] = current_user.organization_id
    
    db_class = await repo.create(db, class_dict)
    return success_response(db_class, "Sınıf oluşturuldu")


@router.get("", response_model=list[ClassResponse])
async def list_classes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    branch_id: Optional[UUID] = None,
    teacher_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("classes.read"))
):
    repo = ClassRepository()
    
    if branch_id:
        classes = await repo.get_by_branch(db, branch_id, skip, limit)
    elif teacher_id:
        classes = await repo.get_by_teacher(db, teacher_id, skip, limit)
    else:
        classes = await repo.get_by_organization(db, tenant.organization_id, skip, limit)
    
    return success_response(classes)


@router.get("/{class_id}", response_model=ClassResponse)
async def get_class(
    class_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("classes.read"))
):
    repo = ClassRepository()
    db_class = await repo.get(db, class_id)
    
    if not db_class or db_class.organization_id != tenant.organization_id:
        return success_response(None, "Sınıf bulunamadı", success=False)
    
    return success_response(db_class)


@router.put("/{class_id}", response_model=ClassResponse)
async def update_class(
    class_id: UUID,
    class_data: ClassUpdate,
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Transfer students from one class to another"""
    from app.infrastructure.models.models import Student, Class
    
    # Verify source class exists
    source_class_result = await db.execute(
        select(Class).where(Class.id == class_id)
    )
    source_class = source_class_result.scalar_one_or_none()
    
    if not source_class or source_class.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Kaynak sınıf bulunamadı")
    
    # Verify target class exists
    target_class_result = await db.execute(
        select(Class).where(Class.id == transfer.target_class_id)
    )
    target_class = target_class_result.scalar_one_or_none()
    
    if not target_class or target_class.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Hedef sınıf bulunamadı")
    
    # Get students to transfer
    students_result = await db.execute(
        select(Student).where(
            Student.id.in_(transfer.student_ids),
            Student.class_id == class_id
        )
    )
    students = students_result.scalars().all()
    
    if not students:
        raise HTTPException(status_code=404, detail="Belirtilen öğrenciler bulunamadı veya bu sınıfta değiller")
    
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
