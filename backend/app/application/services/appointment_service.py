"""Persistent, tenant-scoped appointments for web and mobile clients."""
from datetime import UTC, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.core.exceptions import ConflictException, ForbiddenException, ValidationException
from app.core.student_access import require_student_access, require_teacher_for_student, uses_relationship_scope
from app.infrastructure.models.models import Appointment, Student, User
from app.infrastructure.repositories.base import BaseRepository
from app.application.services.operations_service import identifier


def school_time(value):
    return (value.replace(tzinfo=UTC) if value.tzinfo is None else value).astimezone(ZoneInfo("Europe/Istanbul"))


async def records(db, tenant, status=None, mine=False):
    repo = BaseRepository(db, tenant)
    query = select(Appointment, Student, User).join(Student, Student.id == Appointment.student_id).join(User, User.id == Appointment.teacher_id)
    query = repo._branch_filter(repo._org_filter(query, Appointment), Student)
    query = query.where(Appointment.deleted_at.is_(None))
    if status:
        query = query.where(Appointment.status == status.upper())
    if "parent" in tenant.role_slugs or mine:
        query = query.where((Appointment.parent_id == tenant.user_id) | (Appointment.teacher_id == tenant.user_id))
    elif "teacher" in tenant.role_slugs:
        query = query.where(Appointment.teacher_id == tenant.user_id)
    rows = (await db.execute(query.order_by(Appointment.slot_datetime.desc()))).all()
    return [{
        "id": str(appointment.id), "teacher_id": str(teacher.id),
        "teacher_name": f"{teacher.first_name} {teacher.last_name}",
        "student_id": str(student.id), "student_name": f"{student.first_name} {student.last_name}",
        "parent_id": str(appointment.parent_id), "slot_datetime": appointment.slot_datetime.isoformat(),
        "appointment_date": school_time(appointment.slot_datetime).date().isoformat(),
        "appointment_time": school_time(appointment.slot_datetime).strftime("%H:%M"),
        "status": appointment.status, "duration_minutes": appointment.duration_minutes,
        "notes": appointment.parent_note, "feedback_notes": appointment.teacher_note,
        "created_at": appointment.created_at.isoformat(),
    } for appointment, student, teacher in rows]


async def create(db, tenant, body):
    repo = BaseRepository(db, tenant)
    if not body.student_id:
        raise ValidationException("Öğrenci seçin")
    student = await repo.get_by_id(identifier(body.student_id), Student)
    teacher = await repo.get_by_id(identifier(body.teacher_id), User, for_update=True)
    if student.organization_id != teacher.organization_id:
        raise ValidationException("Öğretmen ve öğrenci aynı kuruma ait olmalı")
    if uses_relationship_scope(tenant) and "teacher" in tenant.role_slugs and teacher.id != tenant.user_id:
        raise ForbiddenException("Yalnızca kendi randevunuzu oluşturabilirsiniz")
    await require_student_access(db, tenant, student.id)
    if "parent" in tenant.role_slugs:
        await require_teacher_for_student(db, student, teacher.id)
    slot = body.slot_datetime
    if slot is None:
        try:
            slot = datetime.fromisoformat(f"{body.appointment_date or body.date}T{body.appointment_time or body.time_slot}")
        except (ValueError, TypeError) as exc:
            raise ValidationException("Geçerli randevu tarihi ve saati girin") from exc
    # Naive values are the existing web contract's school local time.
    if slot.tzinfo is None:
        from zoneinfo import ZoneInfo
        slot = slot.replace(tzinfo=ZoneInfo("Europe/Istanbul"))
    slot = slot.astimezone(UTC)
    existing = (await db.execute(select(Appointment).where(
        Appointment.teacher_id == teacher.id, Appointment.deleted_at.is_(None),
        Appointment.status.not_in(["CANCELLED", "REJECTED"]),
    ))).scalars().all()
    for record in existing:
        start = record.slot_datetime.replace(tzinfo=UTC) if record.slot_datetime.tzinfo is None else record.slot_datetime
        if start < slot + timedelta(minutes=body.duration_minutes) and start + timedelta(minutes=record.duration_minutes) > slot:
            raise ConflictException("Bu saat dolu; başka bir saat seçin")
    appointment = Appointment(organization_id=student.organization_id, teacher_id=teacher.id,
        student_id=student.id, parent_id=tenant.user_id, slot_datetime=slot,
        duration_minutes=body.duration_minutes, parent_note=body.parent_note or body.notes,
        status="PENDING" if "parent" in tenant.role_slugs else "CONFIRMED")
    db.add(appointment)
    await db.flush()
    return {"id": str(appointment.id), "status": appointment.status, "slot_datetime": slot.isoformat()}


async def update_status(db, tenant, appointment_id, body):
    appointment = await get(db, tenant, appointment_id)
    if uses_relationship_scope(tenant) and "parent" in tenant.role_slugs and body.status != "CANCELLED":
        raise ForbiddenException("Veli yalnızca kendi randevusunu iptal edebilir")
    if body.status not in {"PENDING", "CONFIRMED", "APPROVED", "REJECTED", "CANCELLED", "COMPLETED"}:
        raise ValidationException("Geçersiz randevu durumu")
    appointment.status = body.status
    appointment.teacher_note = body.feedback_notes
    return {"id": str(appointment.id), "status": appointment.status}


async def delete(db, tenant, appointment_id):
    appointment = await get(db, tenant, appointment_id)
    appointment.deleted_at = datetime.now(UTC)


async def get(db, tenant, appointment_id):
    appointment = await BaseRepository(db, tenant).get_by_id(identifier(appointment_id), Appointment)
    await BaseRepository(db, tenant).get_by_id(appointment.student_id, Student)
    if uses_relationship_scope(tenant):
        if "parent" in tenant.role_slugs and appointment.parent_id != tenant.user_id:
            raise ForbiddenException("Bu randevuya erişiminiz yok")
        if "teacher" in tenant.role_slugs and appointment.teacher_id != tenant.user_id:
            raise ForbiddenException("Bu randevuya erişiminiz yok")
    return appointment
