from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from datetime import datetime

from app.application.schemas import AttendanceCreate, AttendanceUpdate, AttendanceResponse
from app.repositories import AttendanceRepository
from app.core.database import get_db
from app.core.dependencies import get_current_user, get_tenant_context
from app.core.permissions import require_permission, PermissionChecker
from app.core.responses import success_response
from app.domain.entities.user import User
from app.core.tenant import TenantContext

router = APIRouter(prefix="/api/attendance", tags=["Attendance"])


@router.post("", response_model=AttendanceResponse)
async def create_attendance(
    attendance: AttendanceCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("attendance.write"))
):
    repo = AttendanceRepository()
    attendance_data = attendance.model_dump()
    attendance_data["created_by"] = tenant.user_id
    attendance_data["organization_id"] = tenant.organization_id
    
    # Check if attendance already exists for this student on this date
    existing = await repo.get_by_student_and_date(db, attendance.student_id, attendance.date)
    if existing:
        return success_response(None, "Bu öğrenci için bu tarihte zaten yoklama var", success=False)
    
    db_attendance = await repo.create(db, attendance_data)
    return success_response(db_attendance, "Yoklama oluşturuldu")


@router.get("", response_model=list[AttendanceResponse])
async def list_attendance(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    class_id: Optional[UUID] = None,
    student_id: Optional[UUID] = None,
    date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("attendance.read"))
):
    repo = AttendanceRepository()
    
    if class_id and date:
        attendance = await repo.get_by_class_and_date(db, class_id, date)
    elif student_id and date:
        attendance = await repo.get_by_student_and_date(db, student_id, date)
    else:
        attendance = await repo.get_multi(db, skip, limit, {"organization_id": tenant.organization_id})
    
    return success_response(attendance)


@router.get("/{attendance_id}", response_model=AttendanceResponse)
async def get_attendance(
    attendance_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("attendance.read"))
):
    repo = AttendanceRepository()
    attendance = await repo.get(db, attendance_id)
    
    if not attendance or attendance.organization_id != tenant.organization_id:
        return success_response(None, "Yoklama bulunamadı", success=False)
    
    return success_response(attendance)


@router.put("/{attendance_id}", response_model=AttendanceResponse)
async def update_attendance(
    attendance_id: UUID,
    attendance: AttendanceUpdate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("attendance.write"))
):
    repo = AttendanceRepository()
    db_attendance = await repo.get(db, attendance_id)
    
    if not db_attendance or db_attendance.organization_id != tenant.organization_id:
        return success_response(None, "Yoklama bulunamadı", success=False)
    
    attendance_data = attendance.model_dump(exclude_unset=True)
    attendance_data["updated_by"] = tenant.user_id
    
    updated_attendance = await repo.update(db, db_attendance, attendance_data)
    return success_response(updated_attendance, "Yoklama güncellendi")


@router.delete("/{attendance_id}")
async def delete_attendance(
    attendance_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("attendance.write"))
):
    repo = AttendanceRepository()
    db_attendance = await repo.get(db, attendance_id)
    
    if not db_attendance or db_attendance.organization_id != tenant.organization_id:
        return success_response(None, "Yoklama bulunamadı", success=False)
    
    await repo.delete(db, attendance_id)
    return success_response(message="Yoklama silindi")


# ==================== TEACHER SPECIFIC ENDPOINTS ====================

@router.post("/bulk")
@require_permission("attendance.take")
async def bulk_create_attendance(
    class_id: UUID,
    date: datetime,
    records: list,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Bulk create attendance records for a class (Teacher attendance taking)"""
    from app.infrastructure.models.models import AttendanceRecord as AttendanceModel
    from sqlalchemy import select, and_
    
    # Verify teacher has access to this class
    from app.infrastructure.models.models import ClassTeacher
    teacher_class_result = await db.execute(
        select(ClassTeacher).where(
            and_(
                ClassTeacher.user_id == current_user.id,
                ClassTeacher.class_id == class_id
            )
        )
    )
    if not teacher_class_result.scalar_one_or_none():
        return success_response(None, "Bu sınıfa erişiminiz yok", success=False)
    
    created_records = []
    updated_records = []
    
    for record in records:
        student_id = record.get("student_id")
        status = record.get("status")
        check_in_time = record.get("check_in_time")
        check_out_time = record.get("check_out_time")
        note = record.get("note")
        
        # Check if attendance already exists
        existing_result = await db.execute(
            select(AttendanceModel).where(
                and_(
                    AttendanceModel.student_id == student_id,
                    AttendanceModel.attendance_date == date.date()
                )
            )
        )
        existing = existing_result.scalar_one_or_none()
        
        if existing:
            # Update existing record
            existing.status = status
            existing.check_in_time = check_in_time
            existing.check_out_time = check_out_time
            existing.note = note
            existing.recorded_by = current_user.id
            updated_records.append(existing)
        else:
            # Create new record
            new_attendance = AttendanceModel(
                organization_id=current_user.organization_id,
                branch_id=current_user.branch_id if hasattr(current_user, 'branch_id') else None,
                class_id=class_id,
                student_id=student_id,
                attendance_date=date.date(),
                status=status,
                check_in_time=check_in_time,
                check_out_time=check_out_time,
                note=note,
                recorded_by=current_user.id
            )
            db.add(new_attendance)
            created_records.append(new_attendance)
    
    await db.commit()
    
    for record in created_records:
        await db.refresh(record)
    
    return success_response({
        "created": len(created_records),
        "updated": len(updated_records),
        "message": f"{len(created_records)} yeni yoklama oluşturuldu, {len(updated_records)} güncellendi"
    })


@router.post("/mark-all-present")
@require_permission("attendance.take")
async def mark_all_present(
    class_id: UUID,
    date: datetime,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark all students in a class as present (Quick attendance)"""
    from app.infrastructure.models.models import AttendanceRecord as AttendanceModel, Student
    from sqlalchemy import select, and_
    
    # Verify teacher has access to this class
    from app.infrastructure.models.models import ClassTeacher
    teacher_class_result = await db.execute(
        select(ClassTeacher).where(
            and_(
                ClassTeacher.user_id == current_user.id,
                ClassTeacher.class_id == class_id
            )
        )
    )
    if not teacher_class_result.scalar_one_or_none():
        return success_response(None, "Bu sınıfa erişiminiz yok", success=False)
    
    # Get all students in this class
    students_result = await db.execute(
        select(Student).where(Student.class_id == class_id)
    )
    students = students_result.scalars().all()
    
    marked_count = 0
    skipped_count = 0
    
    for student in students:
        # Check if attendance already exists
        existing_result = await db.execute(
            select(AttendanceModel).where(
                and_(
                    AttendanceModel.student_id == student.id,
                    AttendanceModel.attendance_date == date.date()
                )
            )
        )
        existing = existing_result.scalar_one_or_none()
        
        if existing:
            skipped_count += 1
        else:
            # Create new attendance record
            new_attendance = AttendanceModel(
                organization_id=current_user.organization_id,
                branch_id=student.branch_id,
                class_id=class_id,
                student_id=student.id,
                attendance_date=date.date(),
                status="PRESENT",
                recorded_by=current_user.id
            )
            db.add(new_attendance)
            marked_count += 1
    
    await db.commit()
    
    return success_response({
        "marked": marked_count,
        "skipped": skipped_count,
        "message": f"{marked_count} öğrenci 'Geldi' olarak işaretlendi"
    })
