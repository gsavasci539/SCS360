import hashlib
import json
from datetime import UTC, date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel, field_validator
from sqlalchemy import Text, cast, delete, func, insert, literal, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AppException, ConflictException, ForbiddenException, NotFoundException, ValidationException
from app.core.permissions import PermissionChecker
from app.core.responses import paginate, success_response
from app.core.student_access import accessible_student_ids, require_student_access
from app.core.tenant import TenantContext
from app.infrastructure.models.models import Branch, ClassRoom, DailyDevelopmentReport, Student
from app.infrastructure.repositories.base import BaseRepository

router = APIRouter(prefix="/api/daily-reports", tags=["Daily Reports"])
OBSERVATIONS = ("meal_status", "sleep_status", "mood", "activities", "teacher_notes")
REPORT_SNAPSHOT = ("student_id", "class_id", "date", "recorded_by", *OBSERVATIONS, "created_at", "updated_at")
TURKISH_CASE = str.maketrans("IİÇĞÖŞÜ", "ıiçğöşü")


def contains_turkish_text(column, term: str):
    # SQLite's lower() only converts ASCII. Fold Turkish capitals on both databases.
    for upper, lower in TURKISH_CASE.items():
        column = func.replace(column, chr(upper), chr(lower))
    return column.icontains(term.translate(TURKISH_CASE), autoescape=True)


class ReportFields(BaseModel):
    meal_status: str | None = None
    meal_breakfast: str | None = None
    meal_lunch: str | None = None
    meal_snack: str | None = None
    sleep_status: str | None = None
    mood: str | None = None
    activities: list[str] | None = None
    teacher_notes: str | None = None

    @field_validator("activities", mode="before")
    @classmethod
    def activities_list(cls, value):
        return [item.strip() for item in value.split(",") if item.strip()] if isinstance(value, str) else value


class ReportCreate(ReportFields):
    student_id: UUID
    class_id: UUID | None = None
    date: date


class BulkReportCreate(ReportFields):
    class_id: UUID
    date: date
    reports: list[ReportCreate] | None = None


async def scoped(db, tenant):
    repo = BaseRepository(db, tenant)
    query = repo._branch_filter(repo._org_filter(select(DailyDevelopmentReport)
        .join(Student, Student.id == DailyDevelopmentReport.student_id), Student), Student)
    ids = await accessible_student_ids(db, tenant)
    return query.where(Student.id.in_(ids)) if ids is not None else query


async def get(db, tenant, identifier):
    query = (await scoped(db, tenant)).where(DailyDevelopmentReport.id == identifier)
    row = (await db.execute(query.execution_options(populate_existing=True))).scalar_one_or_none()
    if row is None:
        raise NotFoundException("Günlük rapor bulunamadı")
    return row


def report_version(row):
    values = [str(row.id), *(getattr(row, key) for key in REPORT_SNAPSHOT)]
    encoded = json.dumps(values, default=str, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def stale_report():
    return AppException("Günlük karne değişti. Güncel kaydı açın.", status_code=412)


async def mutation_filter(db, tenant, identifier, if_match):
    table = DailyDevelopmentReport.__table__
    query = (await scoped(db, tenant)).where(DailyDevelopmentReport.id == identifier)
    # Compare the stored representation of JSON and timestamps on both dialects.
    text_fields = ("activities", "created_at", "updated_at")
    raw = [cast(table.c[key], Text) for key in text_fields]
    snapshots = [cast(getattr(DailyDevelopmentReport, key), Text).label(f"snapshot_{key}") for key in text_fields]
    result = (await db.execute(query.add_columns(*snapshots).execution_options(populate_existing=True))).one_or_none()
    if result is None:
        raise NotFoundException("Günlük rapor bulunamadı")
    row, *stored = result
    if if_match is not None and if_match != f'"{report_version(row)}"':
        raise stale_report()
    return (
        table.c.id.in_(query.with_only_columns(DailyDevelopmentReport.id).correlate(None)),
        *(column.is_not_distinct_from(value) for column, value in zip(raw, stored, strict=True)),
        *(table.c[key].is_not_distinct_from(getattr(row, key)) for key in REPORT_SNAPSHOT if key not in text_fields),
    )


async def serialize(db, row):
    student = await db.get(Student, row.student_id)
    return {"id": str(row.id), "student_id": str(row.student_id), "class_id": str(row.class_id),
        "student_name": f"{student.first_name} {student.last_name}" if student else None,
        "date": row.date.isoformat(), "meal_status": row.meal_status, "sleep_status": row.sleep_status,
        "mood": row.mood, "activities": row.activities, "teacher_notes": row.teacher_notes,
        "recorded_by": str(row.recorded_by) if row.recorded_by else None, "version": report_version(row)}


def report_fields(body):
    values = body.model_dump(exclude_unset=True)
    meal_parts = [f"{label}: {values[key]}" for key, label in
        (("meal_breakfast", "Kahvaltı"), ("meal_lunch", "Öğle"), ("meal_snack", "Ara öğün")) if values.get(key)]
    if meal_parts:
        values["meal_status"] = " / ".join(meal_parts)
    return {key: values[key] for key in OBSERVATIONS if key in values}


async def save(db, tenant, body):
    # PostgreSQL locks the student row. SQLite serializes the single conditional insert.
    student = await BaseRepository(db, tenant).get_by_id(body.student_id, Student, for_update=True)
    await require_student_access(db, tenant, student.id)
    if student.class_id is None or body.class_id and body.class_id != student.class_id:
        raise ValidationException("Öğrencinin sınıfı ile rapor sınıfı eşleşmiyor")
    table = DailyDevelopmentReport.__table__
    existing = select(table.c.id).where(table.c.student_id == student.id, table.c.date == body.date).exists()
    values = {"student_id": student.id, "class_id": student.class_id, "date": body.date,
        "recorded_by": tenant.user_id, **report_fields(body)}
    candidate = select(*(literal(value, type_=table.c[key].type) for key, value in values.items())).where(~existing)
    result = await db.execute(insert(table).from_select(list(values), candidate).returning(table.c.id))
    identifier = result.scalar_one_or_none()
    if identifier is None:
        raise ConflictException("Bu öğrenci ve tarihe ait rapor zaten var")
    return await serialize(db, await db.get(DailyDevelopmentReport, identifier))


@router.get("")
@router.get("/")
async def list_daily_reports(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    class_id: UUID | None = None, student_id: UUID | None = None, date: date | None = None, branch_id: UUID | None = None,
    report_date: str | None = None, search: str | None = Query(None, max_length=150),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("daily_reports.read", "academic.read"))):
    query = await scoped(db, tenant)
    if class_id: query = query.where(DailyDevelopmentReport.class_id == class_id)
    if student_id: query = query.where(DailyDevelopmentReport.student_id == student_id)
    if branch_id: query = query.where(Student.branch_id == branch_id)
    if date: query = query.where(DailyDevelopmentReport.date == date)
    if report_date:
        from datetime import date as Date
        try: query = query.where(DailyDevelopmentReport.date == Date.fromisoformat(report_date))
        except ValueError as exc: raise ValidationException("Geçerli bir tarih girin") from exc
    if search and (term := " ".join(search.split())):
        query = query.where(or_(
            contains_turkish_text(Student.first_name + " " + Student.last_name, term),
            Student.student_number.icontains(term, autoescape=True),
            *(contains_turkish_text(getattr(DailyDevelopmentReport, name), term)
                for name in ("mood", "sleep_status", "meal_status", "teacher_notes")),
        ))
    rows, total = await BaseRepository(db, tenant).paginate(query.order_by(DailyDevelopmentReport.date.desc(),
        DailyDevelopmentReport.id), page, page_size)
    return success_response(paginate([await serialize(db, row) for row in rows], total, page, page_size))


@router.post("")
@router.post("/")
async def create_daily_report(report: ReportCreate, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("daily_reports.write", "academic.write"))):
    return success_response(await save(db, tenant, report), "Günlük rapor kaydedildi")


@router.post("/bulk")
async def create_bulk_daily_reports(body: BulkReportCreate, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("daily_reports.write", "academic.write"))):
    from app.application.services.homework_service import class_scope
    if (await db.execute(class_scope(tenant).where(ClassRoom.id == body.class_id))).scalar_one_or_none() is None:
        raise ValidationException("Bu sınıfa rapor yazma yetkiniz yok")
    records = body.reports
    if records is None:
        ids = (await db.execute(select(Student.id).where(Student.class_id == body.class_id, Student.deleted_at.is_(None)))).scalars()
        values = body.model_dump(exclude={"reports"})
        records = [ReportCreate(**values, student_id=identifier) for identifier in ids]
    result = [None] * len(records)
    # Overlapping bulk requests take student locks in the same order.
    for index, record in sorted(enumerate(records), key=lambda entry: entry[1].student_id):
        if record.class_id and record.class_id != body.class_id:
            raise ValidationException("Toplu rapordaki sınıflar eşleşmeli")
        result[index] = await save(db, tenant, record.model_copy(update={"class_id": body.class_id, "date": body.date}))
    return success_response(result, f"{len(result)} rapor kaydedildi")


@router.get("/student-options")
async def daily_report_student_options(
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100),
    search: str | None = Query(None, max_length=150), selected_id: UUID | None = None, branch_id: UUID | None = None,
    class_id: UUID | None = None,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("daily_reports.write", "academic.write")),
):
    if tenant.organization_id is None:
        raise ForbiddenException("Önce kurum çalışma alanını seçin")
    repo = BaseRepository(db, tenant)
    classroom = select(ClassRoom.id).where(ClassRoom.id == Student.class_id,
        ClassRoom.organization_id == Student.organization_id, ClassRoom.branch_id == Student.branch_id,
        ClassRoom.deleted_at.is_(None))
    query = repo._branch_filter(select(Student.id, Student.first_name, Student.last_name, Student.student_number, Student.class_id)
        .where(Student.organization_id == tenant.organization_id, Student.deleted_at.is_(None), classroom.exists()), Student)
    allowed = await accessible_student_ids(db, tenant)
    if allowed is not None:
        query = query.where(Student.id.in_(allowed))
    if branch_id is not None:
        await repo.get_by_id(branch_id, Branch)
        query = query.where(Student.branch_id == branch_id)
    if class_id is not None:
        query = query.where(Student.class_id == class_id)
    selected = (await db.execute(query.where(Student.id == selected_id))).one_or_none() if selected_id else None
    if search and (term := search.strip()):
        query = query.where(or_((Student.first_name + " " + Student.last_name).ilike(f"%{term}%"),
            Student.student_number.ilike(f"%{term}%")))
    ordered = query.order_by(Student.first_name, Student.last_name, Student.id)
    # Keep the projection so this form cannot expose student profile fields.
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    rows = (await db.execute(ordered.offset((page - 1) * page_size).limit(page_size))).all()

    def choice(row):
        name = f"{row.first_name} {row.last_name}".strip()
        return {"id": str(row.id), "name": f"{name} · {row.student_number}" if row.student_number else name,
            "student_name": name, "class_id": str(row.class_id)}

    return success_response({**paginate([choice(row) for row in rows], total, page, page_size),
        "selected": choice(selected) if selected else None})


@router.get("/{report_id}")
async def get_daily_report(report_id: UUID, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("daily_reports.read", "academic.read"))):
    return success_response(await serialize(db, await get(db, tenant, report_id)))


@router.put("/{report_id}")
async def update_daily_report(report_id: UUID, body: ReportFields, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("daily_reports.write", "academic.write")),
    if_match: str | None = Header(None)):
    conditions = await mutation_filter(db, tenant, report_id, if_match)
    table = DailyDevelopmentReport.__table__
    result = await db.execute(update(table).where(*conditions).values(**report_fields(body),
        recorded_by=tenant.user_id, updated_at=datetime.now(UTC)).returning(table.c.id))
    if result.scalar_one_or_none() is None:
        raise stale_report()
    return success_response(await serialize(db, await get(db, tenant, report_id)))


@router.delete("/{report_id}")
async def delete_daily_report(report_id: UUID, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("daily_reports.write", "academic.write")),
    if_match: str | None = Header(None)):
    conditions = await mutation_filter(db, tenant, report_id, if_match)
    table = DailyDevelopmentReport.__table__
    result = await db.execute(delete(table).where(*conditions).returning(table.c.id))
    if result.scalar_one_or_none() is None:
        raise stale_report()
    return success_response(message="Günlük rapor silindi")
