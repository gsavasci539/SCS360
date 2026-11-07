"""Read legacy grades and current exam results without copying either source."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from math import isfinite
from uuid import UUID

from sqlalchemy import or_, select

from app.domain.entities.exams import Exam, ExamResult
from app.infrastructure.models.models import ClassRoom, Grade, Student


@dataclass(frozen=True)
class AcademicRecord:
    id: UUID
    student_id: UUID
    subject: str
    grade_type: str
    score: Decimal | None
    max_score: Decimal | None
    exam_date: date
    source: str
    exam_id: UUID | None = None
    grade_scale: str | None = None
    status: str = "COMPLETED"


def numeric(value):
    return float(value) if value is not None and isfinite(float(value)) else None


def normalized_score(row):
    score, maximum = numeric(row.score), numeric(row.max_score)
    if row.status == "CANCELLED" or score is None or maximum is None or maximum <= 0 or not 0 <= score <= maximum:
        return None
    return score / maximum * 100


def enum_value(value):
    return str(value.value if hasattr(value, "value") else value)


async def records(db, organization_id, student_ids=None, *, start=None, end=None, limit=None):
    if not organization_id or student_ids == []:
        return []
    # ORM student visibility remains the authorization boundary. Core queries
    # then retain that child's historical class records after a class transfer.
    query = select(Student.id).where(Student.organization_id == organization_id, Student.deleted_at.is_(None))
    if student_ids is not None:
        requested = list(dict.fromkeys(UUID(str(value)) for value in student_ids))
        allowed = []
        for offset in range(0, len(requested), 5000):
            allowed.extend((await db.execute(query.where(Student.id.in_(requested[offset:offset + 5000])))).scalars().all())
    else:
        allowed = (await db.execute(query)).scalars().all()
    tenant = db.info.get("tenant_context")
    branches = tenant.branch_ids if tenant and not tenant.is_super_admin else []
    grades, exams, results, classes = Grade.__table__, Exam.__table__, ExamResult.__table__, ClassRoom.__table__
    output = []
    for offset in range(0, len(allowed), 5000):
        identifiers = allowed[offset:offset + 5000]
        legacy = select(grades).join(classes, classes.c.id == grades.c.class_id).where(
            grades.c.organization_id == organization_id, classes.c.organization_id == organization_id,
            grades.c.student_id.in_(identifiers))
        current = select(results.c.id, results.c.student_id, results.c.score, results.c.grade_scale,
            exams.c.id.label("exam_id"), exams.c.title, exams.c.exam_type, exams.c.max_score,
            exams.c.exam_date, exams.c.status).select_from(results.join(exams, results.c.exam_id == exams.c.id)
            .join(classes, classes.c.id == exams.c.class_id)).where(classes.c.organization_id == organization_id,
                results.c.student_id.in_(identifiers), or_(results.c.score.is_not(None), results.c.grade_scale.is_not(None)))
        if branches:
            legacy = legacy.where(grades.c.branch_id.in_(branches))
            current = current.where(classes.c.branch_id.in_(branches))
        if start:
            legacy = legacy.where(grades.c.exam_date >= start)
            current = current.where(exams.c.exam_date >= start)
        if end:
            legacy = legacy.where(grades.c.exam_date <= end)
            current = current.where(exams.c.exam_date <= end)
        legacy = legacy.order_by(grades.c.exam_date.desc(), grades.c.id)
        current = current.order_by(exams.c.exam_date.desc(), results.c.id)
        if limit:
            legacy, current = legacy.limit(limit), current.limit(limit)
        for row in (await db.execute(legacy)).mappings():
            output.append(AcademicRecord(row.id, row.student_id, enum_value(row.subject), enum_value(row.grade_type),
                row.score, row.max_score, row.exam_date, "GRADE"))
        for row in (await db.execute(current)).mappings():
            scale = row.grade_scale.strip() or None if row.grade_scale else None
            if row.score is None and scale is None:
                continue
            output.append(AcademicRecord(row.id, row.student_id, row.title, row.exam_type, row.score,
                row.max_score, row.exam_date, "EXAM_RESULT", row.exam_id, scale,
                "CANCELLED" if row.status == "CANCELLED" else "COMPLETED"))
    output.sort(key=lambda row: (row.exam_date, str(row.id)), reverse=True)
    return output[:limit] if limit else output
