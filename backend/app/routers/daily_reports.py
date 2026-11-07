from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.core.permissions import PermissionChecker
from app.core.responses import paginate, success_response
from app.core.student_access import accessible_student_ids, require_student_access
from app.core.tenant import TenantContext
from app.infrastructure.models.models import DailyDevelopmentReport, Student
from app.infrastructure.repositories.base import BaseRepository

router = APIRouter(prefix="/api/daily-reports", tags=["Daily Reports"])


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
    row = (await db.execute((await scoped(db, tenant)).where(DailyDevelopmentReport.id == identifier))).scalar_one_or_none()
    if row is None:
        raise NotFoundException("Günlük rapor bulunamadı")
    return row


async def serialize(db, row):
    student = await db.get(Student, row.student_id)
    return {"id": str(row.id), "student_id": str(row.student_id), "class_id": str(row.class_id),
        "student_name": f"{student.first_name} {student.last_name}" if student else None,
        "date": row.date.isoformat(), "meal_status": row.meal_status, "sleep_status": row.sleep_status,
        "mood": row.mood, "activities": row.activities, "teacher_notes": row.teacher_notes,
        "recorded_by": str(row.recorded_by) if row.recorded_by else None}


def apply_fields(row, body):
    values = body.model_dump(exclude_unset=True)
    meal_parts = [f"{label}: {values[key]}" for key, label in
        (("meal_breakfast", "Kahvaltı"), ("meal_lunch", "Öğle"), ("meal_snack", "Ara öğün")) if values.get(key)]
    if meal_parts:
        values["meal_status"] = " / ".join(meal_parts)
    for key in ("meal_status", "sleep_status", "mood", "activities", "teacher_notes"):
        if key in values:
            setattr(row, key, values[key])


async def save(db, tenant, body):
    student = await BaseRepository(db, tenant).get_by_id(body.student_id, Student)
    await require_student_access(db, tenant, student.id)
    if student.class_id is None or body.class_id and body.class_id != student.class_id:
        raise ValidationException("Öğrencinin sınıfı ile rapor sınıfı eşleşmiyor")
    existing = (await db.execute(select(DailyDevelopmentReport.id).where(
        DailyDevelopmentReport.student_id == student.id, DailyDevelopmentReport.date == body.date))).scalar_one_or_none()
    if existing:
        raise ConflictException("Bu öğrenci ve tarihe ait rapor zaten var")
    row = DailyDevelopmentReport(student_id=student.id, class_id=student.class_id, date=body.date, recorded_by=tenant.user_id)
    apply_fields(row, body)
    db.add(row); await db.flush()
    return await serialize(db, row)


@router.get("")
@router.get("/")
async def list_daily_reports(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    class_id: UUID | None = None, student_id: UUID | None = None, date: date | None = None,
    report_date: str | None = None, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("daily_reports.read", "academic.read"))):
    query = await scoped(db, tenant)
    if class_id: query = query.where(DailyDevelopmentReport.class_id == class_id)
    if student_id: query = query.where(DailyDevelopmentReport.student_id == student_id)
    if date: query = query.where(DailyDevelopmentReport.date == date)
    if report_date:
        from datetime import date as Date
        try: query = query.where(DailyDevelopmentReport.date == Date.fromisoformat(report_date))
        except ValueError as exc: raise ValidationException("Geçerli bir tarih girin") from exc
    rows, total = await BaseRepository(db, tenant).paginate(query.order_by(DailyDevelopmentReport.date.desc()), page, page_size)
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
    from app.infrastructure.models.models import ClassRoom
    if (await db.execute(class_scope(tenant).where(ClassRoom.id == body.class_id))).scalar_one_or_none() is None:
        raise ValidationException("Bu sınıfa rapor yazma yetkiniz yok")
    records = body.reports
    if records is None:
        ids = (await db.execute(select(Student.id).where(Student.class_id == body.class_id, Student.deleted_at.is_(None)))).scalars()
        values = body.model_dump(exclude={"reports"})
        records = [ReportCreate(**values, student_id=identifier) for identifier in ids]
    result = []
    for record in records:
        if record.class_id and record.class_id != body.class_id:
            raise ValidationException("Toplu rapordaki sınıflar eşleşmeli")
        result.append(await save(db, tenant, record.model_copy(update={"class_id": body.class_id, "date": body.date})))
    return success_response(result, f"{len(result)} rapor kaydedildi")


@router.get("/{report_id}")
async def get_daily_report(report_id: UUID, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("daily_reports.read", "academic.read"))):
    return success_response(await serialize(db, await get(db, tenant, report_id)))


@router.put("/{report_id}")
async def update_daily_report(report_id: UUID, body: ReportFields, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("daily_reports.write", "academic.write"))):
    row = await get(db, tenant, report_id)
    apply_fields(row, body)
    row.recorded_by = tenant.user_id
    return success_response(await serialize(db, row))


@router.delete("/{report_id}")
async def delete_daily_report(report_id: UUID, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("daily_reports.write", "academic.write"))):
    await db.delete(await get(db, tenant, report_id))
    return success_response(message="Günlük rapor silindi")
