"""Health records are factual records; no generated clinical advice."""
from datetime import date
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import and_, case, func, or_, select, update

from app.application.services.consent_service import utc_iso
from app.core.dates import school_day_bounds, school_today, school_time
from app.domain.entities.health import HealthRecord, InfirmaryVisit, MedicationLog, MedicationSchedule
from app.infrastructure.models.models import AuditAction, AuditLog, Student, User


def medicine_request_status(schedule):
    return schedule.request_status or ("COMPLETED" if not schedule.is_active else "APPROVED" if schedule.updated_by else "PENDING")


def status_expression():
    return func.coalesce(MedicationSchedule.request_status, case((MedicationSchedule.is_active.is_(False), "COMPLETED"),
        (MedicationSchedule.updated_by.is_not(None), "APPROVED"), else_="PENDING"))


def instructions(schedule):
    return schedule.parent_notes if schedule.instruction == "NOT_SPECIFIED" else schedule.instruction


def dose_day(day):
    start, end = school_day_bounds(day)
    stamp = func.coalesce(MedicationLog.given_time, MedicationLog.created_at)
    return or_(MedicationLog.scheduled_date == day, and_(MedicationLog.scheduled_date.is_(None), stamp >= start, stamp < end))


async def student(db, identifier):
    row = (await db.execute(select(Student).where(Student.id == identifier, Student.deleted_at.is_(None)))).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "Öğrenci bulunamadı veya erişim kapsamı dışında")
    return row


async def get_record(db, model, identifier):
    row = (await db.execute(select(model).where(model.id == identifier))).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "Kayıt bulunamadı veya erişim kapsamı dışında")
    return row


async def lock(db, model, identifier):
    # Core no-op update locks the already authorized row in SQLite and PG.
    table = model.__table__
    field = table.c.updated_at if "updated_at" in table.c else table.c.created_at
    await db.execute(update(table).where(table.c.id == identifier).values({field.name: field}))
    row = (await db.execute(select(model).where(model.id == identifier).execution_options(populate_existing=True))).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "Kayıt erişim kapsamı dışında")
    return row


def data(row):
    from datetime import datetime, time
    output = {}
    for column in row.__table__.columns:
        value = getattr(row, column.name)
        output[column.name] = str(value) if isinstance(value, UUID) else utc_iso(value) if isinstance(value, datetime) else value.isoformat() if isinstance(value, date) else value.strftime("%H:%M") if isinstance(value, time) else float(value) if column.name == "temperature" and value is not None else value
    if isinstance(row, MedicationSchedule):
        output["status"] = medicine_request_status(row)
    return output


async def enrich(db, rows):
    async def names(model, ids):
        return {row.id: f"{row.first_name} {row.last_name}" for row in (await db.execute(
            select(model.id, model.first_name, model.last_name).where(model.id.in_(ids)))).all()} if ids else {}
    students = await names(Student, {row.student_id for row in rows})
    actors = await names(User, {getattr(row, field) for row in rows for field in ("given_by", "examined_by", "updated_by") if getattr(row, field, None)})
    schedule_ids = {row.schedule_id for row in rows if isinstance(row, MedicationLog)}
    programs = {row.id: row for row in (await db.execute(select(MedicationSchedule).where(MedicationSchedule.id.in_(schedule_ids)))).scalars()} if schedule_ids else {}
    output = []
    for row in rows:
        item = data(row); item["student_name"] = students.get(row.student_id)
        for field in ("given_by", "examined_by", "updated_by"):
            if hasattr(row, field):
                item[field + "_name"] = actors.get(getattr(row, field))
        if isinstance(row, MedicationLog):
            program = programs.get(row.schedule_id)
            if program and program.student_id == row.student_id:
                item.update({"medication_name": program.medication_name, "dosage": program.dosage, "frequency": program.frequency})
        output.append(item)
    return output


def audit(db, tenant, child, row, action, changes):
    db.add(AuditLog(organization_id=child.organization_id, branch_id=child.branch_id, user_id=tenant.user_id,
        action=AuditAction.UPDATE, entity_type=action, entity_id=row.id, new_values=changes))


async def options(db, student_id=None, search=""):
    query = select(Student).where(Student.deleted_at.is_(None))
    filtered = query.where(or_(Student.first_name.ilike(f"%{search}%"), Student.last_name.ilike(f"%{search}%"))) if search else query
    rows = (await db.execute(filtered.order_by(Student.first_name, Student.id).limit(101))).scalars().all()
    choices = rows[:100]
    selected = (await db.execute(query.where(Student.id == student_id))).scalar_one_or_none() if student_id else None
    if selected and not any(row.id == selected.id for row in choices):
        choices = [*choices, selected]
    return {"students": [{"id": str(row.id), "name": f"{row.first_name} {row.last_name}"} for row in choices],
        "more_students": len(rows) > 100, "today": school_today().isoformat(), "time": school_time().strftime("%H:%M")}


async def decide_request(db, tenant, identifier, status):
    if not tenant.has_permission("health.write"):
        raise HTTPException(403, "İlaç kararı için sağlık yazma yetkisi gerekli")
    row = await get_record(db, MedicationSchedule, identifier)
    child = await student(db, row.student_id)
    row = await lock(db, MedicationSchedule, identifier)
    old = medicine_request_status(row)
    if old == status:
        return row
    if status not in {"APPROVED", "REJECTED", "COMPLETED"}:
        raise HTTPException(422, "Geçerli bir ilaç kararı seçin")
    if (old, status) not in {("PENDING", "APPROVED"), ("PENDING", "REJECTED"), ("APPROVED", "COMPLETED")}:
        raise HTTPException(409, "Bu ilaç talebi durum değişikliğine kapalı")
    row.request_status = status; row.is_active = status == "APPROVED"; row.updated_by = tenant.user_id
    audit(db, tenant, child, row, "MEDICATION_REQUEST_DECIDED", {"previous_status": old, "status": status})
    await db.commit(); await db.refresh(row)
    return row


async def summary(db, student_id=None):
    today = school_today()
    async def count(model, *conditions):
        query = select(func.count(model.id)).where(*conditions)
        if student_id:
            query = query.where(model.student_id == student_id)
        return (await db.execute(query)).scalar() or 0
    return {"total_records": await count(HealthRecord),
        "recent_visits": await count(InfirmaryVisit, InfirmaryVisit.visit_date >= today.replace(day=1), InfirmaryVisit.visit_date <= today),
        "follow_up_visits": await count(InfirmaryVisit, InfirmaryVisit.follow_up_required.is_(True)),
        "allergy_records": await count(HealthRecord, func.length(func.trim(HealthRecord.allergies)) > 0),
        "active_schedules": await count(MedicationSchedule, MedicationSchedule.is_active.is_(True), status_expression() == "APPROVED",
            MedicationSchedule.start_date <= today, or_(MedicationSchedule.end_date.is_(None), MedicationSchedule.end_date >= today)),
        "pending_requests": await count(MedicationSchedule, status_expression() == "PENDING")}
