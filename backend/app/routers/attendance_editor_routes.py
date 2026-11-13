"""Tenant-scoped, versioned attendance editor API."""
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.schemas.attendance_editor import AttendanceBatchSave
from app.application.services.attendance_editor import save, version
from app.core.database import get_db
from app.core.permissions import PermissionChecker
from app.core.responses import paginate, success_response
from app.core.tenant import TenantContext
from app.infrastructure.models.models import AttendanceRecord, ClassRoom, Student
from app.infrastructure.repositories.base import BaseRepository

router = APIRouter(prefix="/api/attendance", tags=["Attendance editor"])


@router.get("")
async def list_attendance_editor(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    class_id: UUID | None = None,
    attendance_date: date | None = None,
    tenant: TenantContext = Depends(PermissionChecker("attendance.read")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    query = select(AttendanceRecord).where(AttendanceRecord.deleted_at.is_(None))
    repo = BaseRepository(db, tenant)
    query = repo._org_filter(query, AttendanceRecord)
    query = repo._branch_filter(query, AttendanceRecord)
    if class_id:
        await repo.get_by_id(class_id, ClassRoom)
        query = query.where(AttendanceRecord.class_id == class_id)
    if attendance_date:
        query = query.where(AttendanceRecord.attendance_date == attendance_date)
    items, total = await repo.paginate(
        query.order_by(AttendanceRecord.attendance_date.desc(), AttendanceRecord.student_id), page, page_size
    )
    ids = [row.student_id for row in items]
    students = (await db.execute(select(Student).where(
        Student.id.in_(ids), Student.organization_id == tenant.organization_id,
        Student.deleted_at.is_(None),
    ))).scalars().all() if ids else []
    names = {row.id: row for row in students}
    data = [{
        "id": str(row.id), "student_id": str(row.student_id), "class_id": str(row.class_id),
        "attendance_date": row.attendance_date.isoformat(), "status": row.status.value,
        "notes": row.notes, "check_in_time": row.check_in_time.isoformat() if row.check_in_time else None,
        "version": version(row), "first_name": names[row.student_id].first_name if row.student_id in names else None,
        "last_name": names[row.student_id].last_name if row.student_id in names else None,
    } for row in items]
    return success_response(paginate(data, total, page, page_size))


@router.put("/bulk")
async def save_attendance_editor(
    body: AttendanceBatchSave,
    tenant: TenantContext = Depends(PermissionChecker("attendance.write")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    return success_response(await save(db, tenant, body), "Yoklama değişiklikleri kaydedildi")
