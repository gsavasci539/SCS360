"""Validated exam management, serialized per school without rewriting history."""
from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import func, or_, select

from app.application.services.academic_records import normalized_score, numeric, records
from app.application.services.platform_service import lock_organization
from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException, ValidationException
from app.core.responses import paginate
from app.domain.entities.exams import Exam, ExamResult, ReportCard
from app.infrastructure.models.models import AttendanceRecord, AttendanceStatus, Branch, ClassRoom, Student, User, UserStatus


class ExamFields(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, allow_inf_nan=False, extra="forbid")
    class_id: UUID
    subject_id: UUID | None = None
    teacher_id: UUID | None = None
    title: str = Field(min_length=1, max_length=255)
    exam_type: Literal["MIDTERM", "FINAL", "QUIZ", "MAKEUP", "PROJECT", "OTHER"]
    exam_date: date
    start_time: time | None = None
    duration_minutes: int = Field(default=60, ge=15, le=300)
    max_score: Decimal = Field(default=Decimal("100"), gt=0, le=Decimal("999.99"), decimal_places=2)
    weight: Decimal = Field(default=Decimal("1"), ge=0, le=2, decimal_places=2)
    description: str | None = Field(default=None, max_length=1000)

    @field_validator("exam_type", mode="before")
    @classmethod
    def normalize_type(cls, value):
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("start_time")
    @classmethod
    def local_time(cls, value):
        if value is not None and value.tzinfo is not None:
            raise ValueError("Sınav saati okulun yerel saati olmalı")
        return value


class GradeEntry(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, allow_inf_nan=False, extra="forbid")
    student_id: UUID
    score: Decimal | None = Field(default=None, ge=0, le=Decimal("999.99"), decimal_places=2)
    grade_scale: str | None = Field(default=None, max_length=10)
    notes: str | None = Field(default=None, max_length=1000)


class BulkGrades(BaseModel):
    model_config = ConfigDict(extra="forbid")
    exam_id: UUID
    grades: list[GradeEntry] = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def distinct_students(self):
        if len({row.student_id for row in self.grades}) != len(self.grades):
            raise ValueError("Aynı öğrenci bir not grubunda tekrar edemez")
        return self


class ResultFields(GradeEntry):
    exam_id: UUID


class CardFields(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    student_id: UUID
    academic_year: str = Field(pattern=r"^\d{4}-\d{4}$")
    semester: Literal["FALL", "SPRING", "SUMMER"] = "FALL"
    teacher_comments: str | None = Field(default=None, max_length=2000)
    principal_comments: str | None = Field(default=None, max_length=2000)

    @field_validator("semester", mode="before")
    @classmethod
    def normalize_semester(cls, value):
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("academic_year")
    @classmethod
    def consecutive_years(cls, value):
        start, end = map(int, value.split("-"))
        if not 1 <= start < 9999 or end != start + 1:
            raise ValueError("Akademik yıl ardışık iki yıl olmalı")
        return value


def period(academic_year, semester):
    first, last = map(int, academic_year.split("-"))
    if semester == "FALL":
        return date(first, 9, 1), date(last, 2, 1)
    if semester == "SPRING":
        return date(last, 2, 1), date(last, 7, 1)
    return date(last, 7, 1), date(last, 9, 1)


async def lock_school(db, tenant):
    if tenant.is_super_admin or tenant.organization_id is None:
        raise ForbiddenException("Önce kurum çalışma alanını seçin")
    await lock_organization(db, tenant.organization_id)


async def classroom(db, tenant, identifier, *, admission=False):
    row = (await db.execute(select(ClassRoom).where(ClassRoom.id == identifier,
        ClassRoom.organization_id == tenant.organization_id, ClassRoom.deleted_at.is_(None)))).scalar_one_or_none()
    if row is None:
        raise NotFoundException("Sınıf bulunamadı")
    if admission:
        branch = (await db.execute(select(Branch).where(Branch.id == row.branch_id,
            Branch.organization_id == tenant.organization_id, Branch.deleted_at.is_(None)))).scalar_one_or_none()
        if not row.is_active or branch is None or not branch.is_active:
            raise ValidationException("Yeni sınav için aktif sınıf ve şube seçin")
    return row


async def exam_record(db, tenant, identifier):
    row = (await db.execute(select(Exam).where(Exam.id == identifier)
        .execution_options(populate_existing=True))).scalar_one_or_none()
    if row is None:
        raise NotFoundException("Sınav bulunamadı")
    await classroom(db, tenant, row.class_id)
    return row


async def class_options(db, tenant, page, page_size, search, selected_id=None, exam_id=None):
    if tenant.is_super_admin or not tenant.organization_id:
        raise ForbiddenException("Önce kurum çalışma alanını seçin")
    query = select(ClassRoom.id, ClassRoom.name).join(Branch, Branch.id == ClassRoom.branch_id).where(
        ClassRoom.organization_id == tenant.organization_id, ClassRoom.deleted_at.is_(None),
        Branch.organization_id == tenant.organization_id, Branch.deleted_at.is_(None))
    current = (await exam_record(db, tenant, exam_id)).class_id if exam_id else None
    selected = (await db.execute(query.where(ClassRoom.id == current))).first() if selected_id == current and current else None
    query = query.where(ClassRoom.is_active.is_(True), Branch.is_active.is_(True))
    if search:
        query = query.where(ClassRoom.name.ilike(f"%{search.strip()}%"))
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    rows = (await db.execute(query.order_by(ClassRoom.name, ClassRoom.id).offset((page - 1) * page_size).limit(page_size))).all()
    return {**paginate([{"id": str(row.id), "name": row.name} for row in rows], total, page, page_size),
        "selected": {"id": str(selected.id), "name": selected.name} if selected else None}


async def save_exam(db, tenant, payload, identifier=None):
    await lock_school(db, tenant)
    existing = await exam_record(db, tenant, identifier) if identifier else None
    if existing and existing.status == "CANCELLED":
        raise ConflictException("İptal edilen sınav değiştirilemez")
    target = await classroom(db, tenant, payload.class_id, admission=existing is None or existing.class_id != payload.class_id)
    if payload.teacher_id:
        teacher = (await db.execute(select(User).where(User.id == payload.teacher_id,
            User.organization_id == target.organization_id, User.deleted_at.is_(None), User.status == UserStatus.ACTIVE))).scalar_one_or_none()
        if teacher is None:
            raise ValidationException("Sınav görevlisi aynı kurumda aktif bir kullanıcı olmalı")
    if existing and (existing.class_id != payload.class_id or existing.max_score != payload.max_score):
        # Core count retains awareness of historical rows hidden by current pupil scope.
        table = ExamResult.__table__
        if await db.scalar(select(func.count()).select_from(table).where(table.c.exam_id == existing.id)):
            raise ConflictException("Not girilmiş sınavın sınıfı ve tam puanı değiştirilemez")
    now = datetime.now(UTC)
    if existing is None:
        existing = Exam(**payload.model_dump(), status="SCHEDULED", created_by=tenant.user_id, updated_by=tenant.user_id)
        db.add(existing)
    else:
        for key, value in payload.model_dump().items():
            setattr(existing, key, value)
        existing.updated_by = tenant.user_id
        existing.updated_at = now
    await db.flush()
    return existing


async def cancel_exam(db, tenant, identifier):
    await lock_school(db, tenant)
    row = await exam_record(db, tenant, identifier)
    if row.status != "CANCELLED":
        row.status, row.updated_by, row.updated_at = "CANCELLED", tenant.user_id, datetime.now(UTC)
        await db.flush()
    return row


async def write_grades(db, tenant, payload, *, result_id=None):
    await lock_school(db, tenant)
    exam = await exam_record(db, tenant, payload.exam_id)
    if exam.status == "CANCELLED":
        raise ConflictException("İptal edilen sınava not girilemez")
    maximum = numeric(exam.max_score)
    if maximum is None or maximum <= 0:
        raise ValidationException("Sınavın eski tam puan kaydı geçersiz; kayıt incelenmeli")
    grades = payload.grades if isinstance(payload, BulkGrades) else [payload]
    identifiers = [row.student_id for row in grades]
    students = {row.id: row for row in (await db.execute(select(Student).where(Student.id.in_(identifiers),
        Student.organization_id == tenant.organization_id, Student.deleted_at.is_(None)))).scalars()}
    if len(students) != len(identifiers):
        raise NotFoundException("Öğrenci bulunamadı")
    stored = (await db.execute(select(ExamResult).where(ExamResult.exam_id == exam.id,
        ExamResult.student_id.in_(identifiers)).execution_options(populate_existing=True))).scalars().all()
    existing = {}
    for row in stored:
        if row.student_id in existing:
            raise ConflictException("Bu sınavda aynı öğrenci için birden fazla eski not var; kayıtları inceleyin")
        existing[row.student_id] = row
    if result_id is not None and (identifiers[0] not in existing or existing[identifiers[0]].id != result_id):
        raise ValidationException("Notun sınavı ve öğrencisi değiştirilemez")
    for grade in grades:
        if grade.score is not None and grade.score > Decimal(str(maximum)):
            raise ValidationException("Not sınavın tam puanından büyük olamaz")
        if grade.student_id not in existing and students[grade.student_id].class_id != exam.class_id:
            raise ValidationException("Yeni not yalnız sınavın sınıfındaki öğrenciye girilebilir")
    created, updated, output = 0, 0, []
    for grade in grades:
        row = existing.get(grade.student_id)
        if row is None:
            row = ExamResult(exam_id=exam.id, student_id=grade.student_id)
            db.add(row); created += 1
        else:
            updated += 1
        row.score, row.grade_scale, row.notes = grade.score, grade.grade_scale or None, grade.notes or None
        row.submitted_by, row.submitted_at = tenant.user_id, datetime.now(UTC)
        output.append(row)
    await db.flush()
    return created, updated, output


def result_data(row, student_name=None, exam_title=None, actor_name=None):
    return {"id": str(row.id), "exam_id": str(row.exam_id), "exam_title": exam_title,
        "student_id": str(row.student_id), "student_name": student_name,
        "score": numeric(row.score), "grade_scale": row.grade_scale,
        "notes": row.notes, "submitted_by": str(row.submitted_by) if row.submitted_by else None,
        "submitted_by_name": actor_name, "submitted_at": row.submitted_at,
        "created_at": row.created_at, "updated_at": row.updated_at}


async def roster(db, tenant, identifier, page, page_size, search):
    exam = await exam_record(db, tenant, identifier)
    result_ids = select(ExamResult.student_id).where(ExamResult.exam_id == exam.id)
    query = select(Student).where(Student.deleted_at.is_(None),
        or_(Student.class_id == exam.class_id, Student.id.in_(result_ids)))
    if search:
        query = query.where(or_(Student.first_name.ilike(f"%{search.strip()}%"), Student.last_name.ilike(f"%{search.strip()}%")))
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    students = (await db.execute(query.order_by(Student.first_name, Student.last_name, Student.id)
        .offset((page - 1) * page_size).limit(page_size))).scalars().all()
    rows = (await db.execute(select(ExamResult).where(ExamResult.exam_id == exam.id,
        ExamResult.student_id.in_([row.id for row in students])))).scalars().all()
    by_student = {}
    duplicates = set()
    for row in rows:
        if row.student_id in by_student:
            duplicates.add(row.student_id)
        by_student[row.student_id] = row
    items = []
    for student in students:
        result = by_student.get(student.id)
        items.append({"id": str(student.id), "name": f"{student.first_name} {student.last_name}",
            "result_id": str(result.id) if result else None, "score": numeric(result.score) if result else None,
            "invalid_numeric_score": result is not None and result.score is not None and numeric(result.score) is None,
            "grade_scale": result.grade_scale if result else None, "notes": result.notes if result else None,
            "duplicate_results": student.id in duplicates, "historical": student.class_id != exam.class_id})
    return paginate(items, total, page, page_size)


async def performance(db, tenant, student, academic_year, semester):
    start, end = period(academic_year, semester)
    cohort = (await db.execute(select(Student.id).where(Student.class_id == student.class_id,
        Student.deleted_at.is_(None)))).scalars().all() if student.class_id else [student.id]
    if student.id not in cohort:
        cohort.append(student.id)
    assessed = {}
    for row in await records(db, student.organization_id, cohort, start=start, end=date.fromordinal(end.toordinal() - 1)):
        value = normalized_score(row)
        if value is not None:
            assessed.setdefault(row.student_id, []).append(value)
    means = {key: sum(values) / len(values) for key, values in assessed.items()}
    average = means.get(student.id)
    # Never label a partial teacher/relationship view as the whole class rank.
    table = Student.__table__
    full_size = await db.scalar(select(func.count()).select_from(table).where(table.c.class_id == student.class_id,
        table.c.organization_id == student.organization_id, table.c.deleted_at.is_(None))) if student.class_id else 1
    full_scope = full_size == len(cohort)
    rank = 1 + sum(value > average + 1e-8 for value in means.values()) if average is not None and full_scope else None
    rate = None
    if tenant.has_permission("attendance.read"):
        statuses = (await db.execute(select(AttendanceRecord.status).where(AttendanceRecord.student_id == student.id,
            AttendanceRecord.attendance_date >= start, AttendanceRecord.attendance_date < end,
            AttendanceRecord.deleted_at.is_(None)))).scalars().all()
        attended = sum(1 if status in {AttendanceStatus.PRESENT, AttendanceStatus.LATE} else
            Decimal("0.5") if status == AttendanceStatus.HALF_DAY else 0 for status in statuses)
        rate = round(Decimal(str(attended)) / len(statuses) * 100, 2) if statuses else None
    return (round(average / 25, 2) if average is not None else None, rank, full_size if full_scope else None, rate)


async def generate_card(db, tenant, payload):
    await lock_school(db, tenant)
    student = (await db.execute(select(Student).where(Student.id == payload.student_id,
        Student.deleted_at.is_(None)))).scalar_one_or_none()
    if student is None:
        raise NotFoundException("Öğrenci bulunamadı")
    values = await performance(db, tenant, student, payload.academic_year, payload.semester)
    cards = (await db.execute(select(ReportCard).where(ReportCard.student_id == student.id,
        ReportCard.academic_year == payload.academic_year, ReportCard.semester == payload.semester))).scalars().all()
    if len(cards) > 1:
        raise ConflictException("Bu dönem için birden fazla eski karne var; kayıtları inceleyin")
    card = cards[0] if cards else ReportCard(student_id=student.id, academic_year=payload.academic_year, semester=payload.semester)
    card.gpa, card.class_rank, card.total_students, card.attendance_rate = values
    card.teacher_comments, card.principal_comments = payload.teacher_comments, payload.principal_comments
    card.generated_by, card.generated_at, card.is_published = tenant.user_id, datetime.now(UTC), False
    db.add(card)
    await db.flush()
    return card


def card_data(card, student_name=None, actor_name=None):
    return {"id": str(card.id), "student_id": str(card.student_id), "student_name": student_name,
        "academic_year": card.academic_year, "semester": card.semester,
        "gpa": numeric(card.gpa), "class_rank": card.class_rank,
        "total_students": card.total_students,
        "attendance_rate": numeric(card.attendance_rate),
        "teacher_comments": card.teacher_comments, "principal_comments": card.principal_comments,
        "generated_by": str(card.generated_by) if card.generated_by else None, "generated_by_name": actor_name,
        "generated_at": card.generated_at, "pdf_url": card.pdf_url, "is_published": card.is_published,
        "created_at": card.created_at, "updated_at": card.updated_at}
