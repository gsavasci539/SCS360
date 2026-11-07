"""Scoped tutoring choices, calendar locks and booking checks."""
from fastapi import HTTPException
from sqlalchemy import func, or_, select, update

from app.core.dates import school_today
from app.core.exceptions import ForbiddenException
from app.core.student_access import require_teacher_for_student, uses_relationship_scope
from app.core.teaching import teacher_class_condition
from app.domain.entities.tutoring import TeacherAvailability, TutoringRequest, TutoringSession
from app.infrastructure.models.models import ClassRoom, ClassTeacher, ClassroomAssignment, Student, StudentTeacherAssignment, User, Role, UserRole


def self_only(tenant):
    return uses_relationship_scope(tenant) and "teacher" in tenant.role_slugs


def require_calendar_owner(tenant, teacher_id):
    if self_only(tenant) and teacher_id != tenant.user_id:
        raise ForbiddenException("Yalnız kendi etüt kayıtlarınızı değiştirebilirsiniz")


def teacher_condition():
    users, roles, assignments = User.__table__, Role.__table__, UserRole.__table__
    teachers = select(assignments.c.user_id).join(roles, roles.c.id == assignments.c.role_id).where(
        roles.c.slug == "teacher", roles.c.deleted_at.is_(None),
        or_(roles.c.organization_id.is_(None), roles.c.organization_id == users.c.organization_id)).correlate(users)
    return or_(users.c.id.in_(teachers), users.c.id.in_(select(ClassRoom.__table__.c.teacher_id)),
        users.c.id.in_(select(ClassTeacher.__table__.c.user_id)), users.c.id.in_(select(ClassroomAssignment.__table__.c.teacher_id)),
        users.c.id.in_(select(StudentTeacherAssignment.__table__.c.teacher_id)))


async def require_teacher(db, tenant, teacher_id, student=None):
    require_calendar_owner(tenant, teacher_id)
    teacher = (await db.execute(select(User).where(User.id == teacher_id, User.deleted_at.is_(None),
        User.status == "ACTIVE", teacher_condition()))).scalar_one_or_none()
    if teacher is None or (student is not None and teacher.organization_id != student.organization_id):
        raise ForbiddenException("Erişilebilir, aktif ve aynı kuruma bağlı öğretmen gerekli")
    if student is not None:
        await require_teacher_for_student(db, student, teacher_id)
    return teacher


async def require_student(db, student_id):
    student = (await db.execute(select(Student).where(Student.id == student_id, Student.deleted_at.is_(None)))).scalar_one_or_none()
    if student is None:
        raise HTTPException(404, "Öğrenci bulunamadı veya erişim kapsamı dışında")
    return student


async def lock_calendar(db, teacher_ids, student_ids=()):
    # Always lock teachers before students, in UUID order, on both SQLite/PG.
    # A no-op Core UPDATE acquires SQLite's write lock as well as PG's row lock.
    for model, identifiers in ((User, teacher_ids), (Student, student_ids)):
        table = model.__table__
        for identifier in sorted(set(identifiers), key=str):
            await db.execute(update(table).where(table.c.id == identifier).values(updated_at=table.c.updated_at))


async def lock_record(db, model, identifier):
    table = model.__table__
    await db.execute(update(table).where(table.c.id == identifier).values(updated_at=table.c.updated_at))
    row = (await db.execute(select(model).where(model.id == identifier).execution_options(populate_existing=True))).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "Kayıt bulunamadı veya erişim kapsamı dışında")
    return row


async def check_booking(db, body, exclude=None):
    slots = (await db.execute(select(TeacherAvailability).where(TeacherAvailability.teacher_id == body.teacher_id,
        TeacherAvailability.day_of_week == body.session_date.weekday(), TeacherAvailability.is_available.is_(True),
        TeacherAvailability.start_time < body.end_time, TeacherAvailability.end_time > body.start_time))).scalars().all()
    if len(slots) != 1 or slots[0].start_time > body.start_time or slots[0].end_time < body.end_time:
        raise HTTPException(409, "Ders aralığı tek bir aktif öğretmen müsaitliğine sığmalı")
    table = TutoringSession.__table__
    # Already authorized student: check busy times across all their teachers,
    # returning no information about a conflicting teacher or other student.
    student_busy = select(table.c.id).where(table.c.student_id == body.student_id, table.c.session_date == body.session_date,
        table.c.status != "CANCELLED", table.c.start_time < body.end_time, table.c.end_time > body.start_time)
    teacher_busy = select(table.c.start_time, table.c.end_time).where(table.c.teacher_id == body.teacher_id,
        table.c.session_date == body.session_date, table.c.status != "CANCELLED", table.c.start_time < body.end_time,
        table.c.end_time > body.start_time)
    if exclude:
        student_busy = student_busy.where(table.c.id != exclude)
        teacher_busy = teacher_busy.where(table.c.id != exclude)
    if (await db.execute(student_busy.limit(1))).first():
        raise HTTPException(409, "Öğrencinin bu saatlerde kayıtlı başka bir etüdü var")
    # Sweep real concurrency rather than counting sequential overlaps together.
    events = [(body.start_time, 1), (body.end_time, -1)]
    for start, end in (await db.execute(teacher_busy)).all():
        events.extend(((max(start, body.start_time), 1), (min(end, body.end_time), -1)))
    active = 0
    for _, delta in sorted(events):
        active += delta
        if active > slots[0].max_students:
            raise HTTPException(409, "Öğretmenin bu saatlerdeki etüt kapasitesi dolu")


async def names(db, model, identifiers):
    if not identifiers:
        return {}
    return {row.id: f"{row.first_name} {row.last_name}" for row in (await db.execute(
        select(model.id, model.first_name, model.last_name).where(model.id.in_(identifiers)))).all()}


async def options(db, tenant, student_id=None, search="", teacher_search="", teacher_id=None):
    query = select(Student).where(Student.deleted_at.is_(None))
    filtered = query.where(or_(Student.first_name.ilike(f"%{search}%"), Student.last_name.ilike(f"%{search}%"))) if search else query
    rows = (await db.execute(filtered.order_by(Student.first_name, Student.id).limit(101))).scalars().all()
    choices = rows[:100]
    selected = (await db.execute(query.where(Student.id == student_id))).scalar_one_or_none() if student_id else None
    if selected and not any(row.id == selected.id for row in choices):
        choices = [*choices, selected]
    teachers = select(User).where(User.deleted_at.is_(None), User.status == "ACTIVE", teacher_condition())
    if self_only(tenant):
        teachers = teachers.where(User.id == tenant.user_id)
    if selected:
        users, students = User.__table__, StudentTeacherAssignment.__table__
        classes = ClassRoom.__table__
        teachers = teachers.where(User.organization_id == selected.organization_id, or_(
            users.c.id.in_(select(students.c.teacher_id).where(students.c.student_id == selected.id)),
            select(classes.c.id).where(classes.c.id == selected.class_id, classes.c.deleted_at.is_(None),
                teacher_class_condition(classes.c, users.c.id)).correlate(users).exists()))
    filtered_teachers = teachers.where(or_(User.first_name.ilike(f"%{teacher_search}%"), User.last_name.ilike(f"%{teacher_search}%"))) if teacher_search else teachers
    teacher_rows = (await db.execute(filtered_teachers.order_by(User.first_name, User.id).limit(101))).scalars().all()
    teacher_choices = teacher_rows[:100]
    if teacher_id and not any(row.id == teacher_id for row in teacher_choices):
        teacher = (await db.execute(teachers.where(User.id == teacher_id))).scalar_one_or_none()
        if teacher:
            teacher_choices = [*teacher_choices, teacher]
    return {"students": [{"id": str(row.id), "name": f"{row.first_name} {row.last_name}"} for row in choices],
        "teachers": [{"id": str(row.id), "name": f"{row.first_name} {row.last_name}"} for row in teacher_choices],
        "more_students": len(rows) > 100, "more_teachers": len(teacher_rows) > 100, "today": school_today().isoformat(),
        "self_only": self_only(tenant), "current_user_id": str(tenant.user_id)}


async def summary(db, student_id=None, teacher_id=None):
    async def count(model, *conditions):
        query = select(func.count(model.id)).where(*conditions)
        if student_id and model != TeacherAvailability:
            query = query.where(model.student_id == student_id)
        if teacher_id:
            query = query.where(model.teacher_id == teacher_id)
        return (await db.execute(query)).scalar() or 0
    total = await count(TutoringSession)
    completed = await count(TutoringSession, TutoringSession.status == "COMPLETED")
    return {"total_sessions": total, "completed_sessions": completed,
        "scheduled_sessions": await count(TutoringSession, TutoringSession.status == "SCHEDULED"),
        "pending_requests": await count(TutoringRequest, TutoringRequest.status == "PENDING"),
        "approved_requests": await count(TutoringRequest, TutoringRequest.status == "APPROVED"),
        "rejected_requests": await count(TutoringRequest, TutoringRequest.status == "REJECTED"),
        "available_windows": await count(TeacherAvailability, TeacherAvailability.is_available.is_(True)),
        "completion_rate": round(completed * 100 / total, 2) if total else 0}
