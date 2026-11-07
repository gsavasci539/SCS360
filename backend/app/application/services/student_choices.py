"""Minimal student choices scoped by the calling feature's tenant context."""
from sqlalchemy import or_, select

from app.core.dates import school_today
from app.infrastructure.models.models import Student


async def options(db, student_id=None, search=""):
    base = select(Student).where(Student.deleted_at.is_(None))
    query = base.where(Student.status == "ACTIVE")
    filtered = query.where(or_(Student.first_name.ilike(f"%{search}%"), Student.last_name.ilike(f"%{search}%"), Student.student_number.ilike(f"%{search}%"))) if search else query
    rows = (await db.execute(filtered.order_by(Student.first_name, Student.id).limit(101))).scalars().all()
    choices = rows[:100]
    if student_id and not any(row.id == student_id for row in choices):
        chosen = (await db.execute(base.where(Student.id == student_id))).scalar_one_or_none()
        if chosen:
            choices = [*choices, chosen]
    return {"students": [{"id": str(row.id), "name": f"{row.first_name} {row.last_name}", "student_number": row.student_number, "active": row.status == "ACTIVE"} for row in choices],
        "more_students": len(rows) > 100, "today": school_today().isoformat()}
