"""Exam, grade and report card API with school-scoped history."""
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services import exam_management as service
from app.application.services.academic_records import numeric
from app.application.services.consent_service import utc_iso
from app.core.database import get_db
from app.core.exceptions import ForbiddenException, NotFoundException, ValidationException
from app.core.permissions import PermissionChecker
from app.core.responses import paginate, success_response
from app.core.tenant import TenantContext
from app.domain.entities.exams import Exam, ExamResult, ReportCard
from app.infrastructure.models.models import Branch, ClassRoom, Student, User
from app.infrastructure.repositories.base import BaseRepository

router = APIRouter(prefix="/api/exams", tags=["Exams"])
ExamCreate = service.ExamFields
BulkGradeEntry = service.BulkGrades
ExamResultCreate = service.ResultFields
ReportCardGenerate = service.CardFields


async def names(db, model, identifiers):
    rows = (await db.execute(select(model).where(model.id.in_(set(identifiers) - {None})))).scalars().all()
    return {row.id: row.name if isinstance(row, ClassRoom) else f"{row.first_name} {row.last_name}" for row in rows}


def exam_data(exam, class_name=None, teacher_name=None, result_count=0, branch_id=None):
    return {"id": str(exam.id), "class_id": str(exam.class_id), "class_name": class_name,
        "subject_id": str(exam.subject_id) if exam.subject_id else None,
        "teacher_id": str(exam.teacher_id) if exam.teacher_id else None, "teacher_name": teacher_name,
        "title": exam.title, "exam_type": exam.exam_type, "status": exam.status, "exam_date": exam.exam_date,
        "start_time": exam.start_time, "duration_minutes": exam.duration_minutes,
        "max_score": numeric(exam.max_score),
        "weight": numeric(exam.weight), "description": exam.description,
        "created_at": utc_iso(exam.created_at), "updated_at": utc_iso(exam.updated_at),
        "result_count": result_count, "branch_id": str(branch_id) if branch_id else None}


async def check_branch(db, tenant, branch_id):
    if tenant.is_super_admin or tenant.organization_id is None:
        raise ForbiddenException("Önce kurum çalışma alanını seçin")
    if branch_id is not None:
        await BaseRepository(db, tenant).get_by_id(branch_id, Branch)


@router.get("/class-options")
async def get_exam_class_options(
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100),
    search: str | None = Query(None, max_length=200), selected_id: UUID | None = None, exam_id: UUID | None = None,
    branch_id: UUID | None = None,
    db: AsyncSession = Depends(get_db, scope="function"), tenant: TenantContext = Depends(PermissionChecker("exam.read", "exam.write")),
):
    await check_branch(db, tenant, branch_id)
    return success_response(await service.class_options(db, tenant, page, page_size, search, selected_id, exam_id, branch_id))


@router.get("")
async def get_exams(
    class_id: UUID | None = None, teacher_id: UUID | None = None,
    record_id: UUID | None = None, branch_id: UUID | None = None,
    exam_type: str | None = Query(None, max_length=20), status: str | None = Query(None, max_length=20),
    start_date: date | None = None, end_date: date | None = None,
    limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0),
    page: int | None = Query(None, ge=1), page_size: int = Query(25, ge=1, le=100),
    search: str | None = Query(None, max_length=200),
    db: AsyncSession = Depends(get_db, scope="function"), tenant: TenantContext = Depends(PermissionChecker("exam.read", "exam.write")),
):
    await check_branch(db, tenant, branch_id)
    if start_date and end_date and start_date > end_date:
        raise ValidationException("Başlangıç tarihi bitiş tarihinden sonra olamaz")
    query = select(Exam)
    for value, column in ((class_id, Exam.class_id), (teacher_id, Exam.teacher_id), (record_id, Exam.id)):
        if value:
            query = query.where(column == value)
    if branch_id is not None:
        query = query.where(Exam.class_id.in_(select(ClassRoom.id).where(ClassRoom.branch_id == branch_id)))
    for value, column in ((exam_type, Exam.exam_type), (status, Exam.status)):
        if value:
            query = query.where(column == value.upper())
    if start_date:
        query = query.where(Exam.exam_date >= start_date)
    if end_date:
        query = query.where(Exam.exam_date <= end_date)
    if search:
        query = query.where(Exam.title.ilike(f"%{search.strip()}%"))
    total = await db.scalar(select(func.count()).select_from(query.subquery())) if page else 0
    rows = (await db.execute(query.order_by(Exam.exam_date.desc(), Exam.id)
        .offset((page - 1) * page_size if page else offset).limit(page_size if page else limit))).scalars().all()
    places = (await db.execute(select(ClassRoom.id, ClassRoom.name, ClassRoom.branch_id)
        .where(ClassRoom.id.in_({row.class_id for row in rows})))).all()
    classes = {room.id: (room.name, room.branch_id) for room in places}
    teachers = await names(db, User, [row.teacher_id for row in rows])
    result_table = ExamResult.__table__
    counts = dict((await db.execute(select(result_table.c.exam_id, func.count()).where(
        result_table.c.exam_id.in_([row.id for row in rows])).group_by(result_table.c.exam_id))).all())
    data = []
    for row in rows:
        name, branch = classes.get(row.class_id, (None, None))
        data.append(exam_data(row, name, teachers.get(row.teacher_id), counts.get(row.id, 0), branch))
    return success_response(paginate(data, total, page, page_size) if page else data)


@router.post("")
async def create_exam(
    exam: ExamCreate, branch_id: UUID | None = None, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("exam.write")),
):
    await check_branch(db, tenant, branch_id)
    row = await service.save_exam(db, tenant, exam, branch_id=branch_id)
    return success_response(exam_data(row), "Sınav oluşturuldu")


@router.put("/{exam_id}")
async def update_exam(
    exam_id: UUID, exam: ExamCreate, branch_id: UUID | None = None, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("exam.write")),
):
    await check_branch(db, tenant, branch_id)
    row = await service.save_exam(db, tenant, exam, exam_id, branch_id)
    return success_response(exam_data(row), "Sınav güncellendi")


@router.delete("/{exam_id}")
async def delete_exam(
    exam_id: UUID, branch_id: UUID | None = None, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("exam.write")),
):
    await check_branch(db, tenant, branch_id)
    row = await service.cancel_exam(db, tenant, exam_id, branch_id)
    return success_response({"id": str(row.id), "status": row.status}, "Sınav iptal edildi; not geçmişi korundu")


@router.get("/{exam_id}/roster")
async def get_exam_roster(
    exam_id: UUID, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100),
    branch_id: UUID | None = None,
    search: str | None = Query(None, max_length=200), db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("exam.read", "exam.write")),
):
    await check_branch(db, tenant, branch_id)
    return success_response(await service.roster(db, tenant, exam_id, page, page_size, search, branch_id))


@router.get("/{exam_id}/results")
async def get_exam_results(
    exam_id: UUID, branch_id: UUID | None = None, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("exam.read", "exam.write")),
):
    await check_branch(db, tenant, branch_id)
    exam = await service.exam_record(db, tenant, exam_id, branch_id)
    rows = (await db.execute(select(ExamResult).where(ExamResult.exam_id == exam.id).order_by(ExamResult.id))).scalars().all()
    students = await names(db, Student, [row.student_id for row in rows])
    actors = await names(db, User, [row.submitted_by for row in rows])
    return success_response([service.result_data(row, students.get(row.student_id), exam.title, actors.get(row.submitted_by)) for row in rows])


@router.post("/bulk-grade-entry")
async def bulk_grade_entry(
    request: BulkGradeEntry, branch_id: UUID | None = None, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("exam.write")),
):
    await check_branch(db, tenant, branch_id)
    created, updated, rows = await service.write_grades(db, tenant, request, branch_id=branch_id)
    return success_response({"created": created, "updated": updated, "items": [service.result_data(row) for row in rows]},
        "Notlar kaydedildi")


@router.put("/results/{result_id}")
async def update_exam_result(
    result_id: UUID, result: ExamResultCreate, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("exam.write")),
):
    existing = (await db.execute(select(ExamResult).where(ExamResult.id == result_id))).scalar_one_or_none()
    if existing is None:
        raise NotFoundException("Not bulunamadı")
    if existing.exam_id != result.exam_id or existing.student_id != result.student_id:
        raise ValidationException("Notun sınavı ve öğrencisi değiştirilemez")
    _, _, rows = await service.write_grades(db, tenant, result, result_id=result_id)
    return success_response(service.result_data(rows[0]), "Not güncellendi")


@router.post("/report-cards/generate")
async def generate_report_card(
    request: ReportCardGenerate, branch_id: UUID | None = None, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("exam.write")),
):
    await check_branch(db, tenant, branch_id)
    card = await service.generate_card(db, tenant, request, branch_id)
    return success_response(service.card_data(card), "Karne taslağı oluşturuldu")


@router.get("/report-cards/{student_id}")
async def get_student_report_cards(
    student_id: UUID, academic_year: str | None = Query(None, max_length=20),
    branch_id: UUID | None = None,
    db: AsyncSession = Depends(get_db, scope="function"), tenant: TenantContext = Depends(PermissionChecker("exam.read", "exam.write")),
):
    await check_branch(db, tenant, branch_id)
    student = (await db.execute(select(Student).where(Student.id == student_id, Student.deleted_at.is_(None)))).scalar_one_or_none()
    if student is None or (branch_id is not None and student.branch_id != branch_id):
        raise NotFoundException("Öğrenci bulunamadı")
    query = select(ReportCard).where(ReportCard.student_id == student_id)
    if academic_year:
        query = query.where(ReportCard.academic_year == academic_year)
    rows = (await db.execute(query.order_by(ReportCard.academic_year.desc(), ReportCard.semester, ReportCard.id))).scalars().all()
    actors = await names(db, User, [row.generated_by for row in rows])
    return success_response([service.card_data(row, f"{student.first_name} {student.last_name}", actors.get(row.generated_by)) for row in rows])


@router.put("/report-cards/{card_id}/publish")
async def publish_report_card(
    card_id: UUID, branch_id: UUID | None = None, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("exam.write")),
):
    await check_branch(db, tenant, branch_id)
    await service.lock_school(db, tenant)
    row = (await db.execute(select(ReportCard).where(ReportCard.id == card_id))).scalar_one_or_none()
    if row is None:
        raise NotFoundException("Karne bulunamadı")
    if branch_id is not None and await db.scalar(select(Student.id).where(
        Student.id == row.student_id, Student.branch_id == branch_id, Student.deleted_at.is_(None)
    )) is None:
        raise NotFoundException("Karne seçili şubede bulunamadı")
    row.is_published = True
    await db.flush()
    return success_response(service.card_data(row), "Karne veliye yayımlandı")

