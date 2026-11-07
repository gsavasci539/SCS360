from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from typing import Optional
from uuid import UUID
from pydantic import BaseModel

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.permissions import PermissionChecker
from app.core.responses import success_response
from app.infrastructure.models.models import User
from app.core.tenant import TenantContext

from app.core.teaching import teacher_classes_query
from app.application.services import teacher_day_service

router = APIRouter(prefix="/api/teacher", tags=["Teacher"])


@router.get("/my-classes")
async def get_teacher_classes(db: AsyncSession = Depends(get_db, scope="function"), current_user: User = Depends(get_current_user)):
    return success_response(await teacher_day_service.classes(db, current_user))


@router.get("/today-schedule")
async def get_teacher_today_schedule(db: AsyncSession = Depends(get_db, scope="function"), current_user: User = Depends(get_current_user)):
    return success_response(await teacher_day_service.today_schedule(db, current_user))


@router.get("/pending-tasks")
async def get_teacher_pending_tasks(db: AsyncSession = Depends(get_db, scope="function"), current_user: User = Depends(get_current_user)):
    return success_response(await teacher_day_service.pending_tasks(db, current_user))


@router.get("/medicine-requests")
async def get_teacher_medicine_requests(
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("health.read", "teacher.view_medicine_requests")),
):
    """Get medicine requests for students in the teacher's assigned classes."""
    from app.domain.entities.health import MedicationSchedule
    from app.infrastructure.models.models import ClassRoom, Student, StudentTeacherAssignment
    class_result = await db.execute(teacher_classes_query(current_user.id))
    class_ids = [cls.id for cls in class_result.scalars().all() if cls is not None]
    result = await db.execute(
        select(MedicationSchedule, Student, ClassRoom)
        .select_from(MedicationSchedule)
        .join(Student, MedicationSchedule.student_id == Student.id)
        .outerjoin(ClassRoom, Student.class_id == ClassRoom.id)
        .where(Student.organization_id == current_user.organization_id, Student.deleted_at.is_(None), or_(Student.class_id.in_(class_ids),
            Student.id.in_(select(StudentTeacherAssignment.__table__.c.student_id).where(StudentTeacherAssignment.__table__.c.teacher_id == current_user.id))))
        .order_by(MedicationSchedule.created_at.desc(), MedicationSchedule.id)
    )
    requests = []
    from app.application.services.infirmary_service import medicine_request_status, instructions
    for schedule, student, cls in result:
        request_status = medicine_request_status(schedule)
        requests.append({
            "id": str(schedule.id),
            "student_id": str(student.id),
            "student_name": f"{student.first_name} {student.last_name}",
            "class_name": cls.name if cls else "Bireysel öğrenci",
            "medicine_name": schedule.medication_name,
            "dosage": schedule.dosage,
            "time_to_give": schedule.frequency,
            "instructions": instructions(schedule),
            "status": request_status,
            "created_at": schedule.created_at.isoformat() if schedule.created_at else None
        })
    return success_response(requests)


@router.get("/class/{class_id}/students")
async def get_class_students(
    class_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("students.read")),
):
    from app.infrastructure.models.models import Student, StudentParent, Parent, ClassRoom, User as UserModel
    from app.core.exceptions import ForbiddenException
    allowed = (await db.execute(teacher_classes_query(current_user.id).where(ClassRoom.id == class_id))).scalar_one_or_none()
    if allowed is None:
        raise ForbiddenException("Bu sınıfa erişim yetkiniz yok")
    rows = (await db.execute(select(Student, Parent, StudentParent)
        .select_from(Student)
        .outerjoin(StudentParent, StudentParent.student_id == Student.id)
        .outerjoin(Parent, and_(Parent.id == StudentParent.parent_id, Parent.deleted_at.is_(None),
            Parent.organization_id == Student.organization_id))
        .where(Student.class_id == class_id, Student.deleted_at.is_(None))
        .order_by(Student.first_name, StudentParent.is_primary.desc()))).all()
    return success_response([{"student_id": str(student.id),
        "student_name": f"{student.first_name} {student.last_name}",
        "parent_id": str(parent.user_id) if parent and parent.user_id else None,
        "parent_name": f"{parent.first_name} {parent.last_name}" if parent else "Bağlı veli hesabı yok",
        "is_primary": bool(link and link.is_primary)} for student, parent, link in rows])


@router.get("/chat/{student_id}")
async def get_chat_messages(
    student_id: UUID,
    parent_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("messaging.read")),
):
    from app.application.services import teacher_chat_service
    return success_response(await teacher_chat_service.history(db, tenant, student_id, parent_id))


class TeacherChatCreate(BaseModel):
    message: str


@router.post("/chat/{student_id}")
async def send_chat_message(
    student_id: UUID,
    request: TeacherChatCreate,
    parent_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("messaging.send")),
):
    from app.application.services import teacher_chat_service
    return success_response(await teacher_chat_service.send(db, tenant, student_id, request.message, parent_id))
