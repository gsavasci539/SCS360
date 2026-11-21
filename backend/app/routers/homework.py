"""Persistent class homework and submissions for web and mobile clients."""
from datetime import UTC, date, datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pathlib import Path
from uuid import uuid4
import asyncio
import os
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services import homework_service
from app.core.database import get_db
from app.core.config import get_settings
from app.core.exceptions import ConflictException, ValidationException
from app.core.permissions import PermissionChecker
from app.core.responses import paginate, success_response
from app.core.student_access import accessible_student_ids, require_student_access
from app.core.tenant import TenantContext
from app.infrastructure.models.models import ClassRoom, Homework, HomeworkSubmission, Student

router = APIRouter(prefix="/api/homework", tags=["Homework"])


class HomeworkCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    subject: str | None = Field(default=None, max_length=100)
    class_id: UUID | None = None
    due_date: date | None = None
    description: str | None = None
    attachment_url: str | None = None
    status: Literal["ACTIVE", "CLOSED", "DRAFT"] = "ACTIVE"
    request_id: UUID | None = None

    @field_validator("class_id", "due_date", mode="before")
    @classmethod
    def empty_optional(cls, value):
        return value or None


class HomeworkUpdate(HomeworkCreate):
    title: str | None = Field(default=None, min_length=1, max_length=255)


class SubmissionCreate(BaseModel):
    student_id: UUID
    homework_id: UUID | None = None
    submission_text: str | None = Field(default=None, max_length=10000)
    file_name: str | None = None
    file_size_mb: float = Field(default=0, ge=0)


class SubmissionGrade(BaseModel):
    score: float = Field(ge=0, le=100)
    teacher_feedback: str | None = None


def attachment_path(submission_id):
    return Path(get_settings().PRIVATE_UPLOAD_DIR).resolve() / "homework" / str(UUID(str(submission_id)))


def attachment_url(record):
    if record.attachment_file_name and attachment_path(record.id).is_file():
        return f"/homework/submissions/{record.id}/attachment"
    return None


@router.get("")
@router.get("/")
async def list_homework(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=1000),
    search: str | None = None, class_id: UUID | None = None, branch_id: UUID | None = None,
    tenant: TenantContext = Depends(PermissionChecker("homework.read")),
    db: AsyncSession = Depends(get_db, scope="function")):
    rows = await homework_service.list_records(db, tenant, class_id, search, branch_id=branch_id)
    return success_response(paginate(rows[(page - 1) * page_size:page * page_size], len(rows), page, page_size))


@router.get("/classes")
async def homework_classes(branch_id: UUID | None = None, tenant: TenantContext = Depends(PermissionChecker("homework.read", "homework.write")),
    db: AsyncSession = Depends(get_db, scope="function")):
    rows = (await db.execute(select(ClassRoom).where(ClassRoom.id.in_(homework_service.class_scope(tenant, branch_id)))
        .order_by(ClassRoom.name, ClassRoom.id))).scalars()
    return success_response([{"id": str(row.id), "name": row.name,
        "branch_id": str(row.branch_id) if row.branch_id else None} for row in rows])


@router.get("/submissions")
async def list_submissions(homework_id: UUID | None = None, branch_id: UUID | None = None, record_id: UUID | None = None,
    student_id: UUID | None = None,
    limit: int | None = Query(None, ge=1, le=1000), offset: int = Query(0, ge=0),
    tenant: TenantContext = Depends(PermissionChecker("homework.read", "parent.view_children")),
    db: AsyncSession = Depends(get_db, scope="function")):
    permitted = (await homework_service.scoped_query(db, tenant, branch_id)).with_only_columns(Homework.id)
    query = select(HomeworkSubmission, Student).join(Student, Student.id == HomeworkSubmission.student_id).where(HomeworkSubmission.homework_id.in_(permitted))
    if homework_id:
        query = query.where(HomeworkSubmission.homework_id == homework_id)
    if record_id:
        query = query.where(HomeworkSubmission.id == record_id)
    if student_id:
        query = query.where(HomeworkSubmission.student_id == student_id)
    ids = await accessible_student_ids(db, tenant)
    if ids is not None:
        query = query.where(Student.id.in_(ids))
    query = query.order_by(HomeworkSubmission.submitted_at.desc(), HomeworkSubmission.id).limit(limit).offset(offset)
    rows = (await db.execute(query)).all()
    return success_response([{
        "id": str(row.id), "homework_id": str(row.homework_id), "student_id": str(student.id),
        "student_name": f"{student.first_name} {student.last_name}", "student_number": student.student_number,
        "submission_text": row.submission_text, "submitted_at": row.submitted_at.isoformat(),
        "status": row.status, "score": float(row.score) if row.score is not None else None,
        "teacher_feedback": row.teacher_feedback, "attachment_file_name": row.attachment_file_name,
        "attachment_file_size_mb": float(row.attachment_file_size_mb),
        "attachment_url": attachment_url(row),
    } for row, student in rows])


@router.post("")
@router.post("/")
async def create_homework(body: HomeworkCreate, branch_id: UUID | None = None,
    tenant: TenantContext = Depends(PermissionChecker("homework.write")),
    db: AsyncSession = Depends(get_db, scope="function")):
    return success_response(await homework_service.save(db, tenant, body, branch_id=branch_id), "Ödev oluşturuldu")


@router.get("/{homework_id}")
async def get_homework(homework_id: UUID, branch_id: UUID | None = None, tenant: TenantContext = Depends(PermissionChecker("homework.read")),
    db: AsyncSession = Depends(get_db, scope="function")):
    record = await homework_service.get(db, tenant, homework_id, branch_id)
    name = (await db.execute(select(ClassRoom.name).where(ClassRoom.id == record.class_id))).scalar_one_or_none() if record.class_id else None
    return success_response(homework_service.serialize(record, name))


@router.put("/{homework_id}")
async def update_homework(homework_id: UUID, body: HomeworkUpdate, branch_id: UUID | None = None,
    tenant: TenantContext = Depends(PermissionChecker("homework.write")),
    db: AsyncSession = Depends(get_db, scope="function")):
    record = await homework_service.get(db, tenant, homework_id, branch_id)
    if "title" in body.model_fields_set and body.title is None:
        raise ValidationException("Ödev adı zorunludur")
    return success_response(await homework_service.save(db, tenant, body, record, branch_id=branch_id))


@router.delete("/{homework_id}")
async def delete_homework(homework_id: UUID, branch_id: UUID | None = None,
    tenant: TenantContext = Depends(PermissionChecker("homework.write")),
    db: AsyncSession = Depends(get_db, scope="function")):
    record = await homework_service.get(db, tenant, homework_id, branch_id)
    record.deleted_at = datetime.now(UTC)
    return success_response(message="Ödev silindi")


@router.get("/{homework_id}/students")
async def homework_students(homework_id: UUID, branch_id: UUID | None = None, search: str = Query("", max_length=100),
    tenant: TenantContext = Depends(PermissionChecker("homework.read", "parent.view_children")),
    db: AsyncSession = Depends(get_db, scope="function")):
    from app.application.services.student_choices import options
    homework = await homework_service.get(db, tenant, homework_id, branch_id)
    if homework.class_id is None or homework.status != "ACTIVE":
        return success_response({"students": [], "more_students": False})
    return success_response(await options(db, search=search.strip(), branch_id=branch_id, class_id=homework.class_id))


@router.post("/{homework_id}/submit")
async def submit_homework(homework_id: UUID, body: SubmissionCreate, branch_id: UUID | None = None,
    tenant: TenantContext = Depends(PermissionChecker("homework.read", "parent.view_children")),
    db: AsyncSession = Depends(get_db, scope="function")):
    if body.file_name or body.file_size_mb:
        raise ValidationException("Dosya içeriğini submit-file adresine yükleyin")
    if not body.submission_text or not body.submission_text.strip():
        raise ValidationException("Teslim metni veya dosya gerekli")
    if body.homework_id is not None and body.homework_id != homework_id:
        raise ValidationException("Teslim ödev kimliğiyle eşleşmiyor")
    record = await submission_record(db, tenant, homework_id, body.student_id, branch_id)
    record.submission_text = body.submission_text.strip()
    record.submitted_at = datetime.now(UTC)
    record.status = "SUBMITTED"
    await db.flush()
    return success_response({"id": str(record.id), "status": record.status})


async def submission_record(db, tenant, homework_id, student_id, branch_id=None):
    homework = await homework_service.get(db, tenant, homework_id, branch_id)
    await db.execute(update(Homework).where(Homework.id == homework_id).values(updated_at=Homework.updated_at))
    await db.refresh(homework)
    if homework.status != "ACTIVE":
        raise ConflictException("Yalnızca aktif ödevlere teslim yapılabilir")
    await require_student_access(db, tenant, student_id)
    student = (await db.execute(select(Student).where(Student.id == student_id,
        Student.organization_id == homework.organization_id, Student.deleted_at.is_(None)))).scalar_one_or_none()
    if student is None or student.class_id != homework.class_id:
        raise ValidationException("Bu ödev seçilen öğrencinin sınıfına ait değil")
    if branch_id is not None and student.branch_id != branch_id:
        raise ValidationException("Öğrenci seçili şubede bulunamadı")
    record = (await db.execute(select(HomeworkSubmission).where(
        HomeworkSubmission.homework_id == homework_id, HomeworkSubmission.student_id == student.id).with_for_update())).scalar_one_or_none()
    if record is not None and record.status == "GRADED":
        raise ConflictException("Notlandırılmış teslim yeniden değiştirilemez")
    if record is None:
        record = HomeworkSubmission(homework_id=homework_id, student_id=student.id)
        db.add(record)
    await db.flush()
    return record


@router.post("/{homework_id}/submit-file")
async def submit_homework_file(homework_id: UUID, student_id: UUID = Form(...),
    submission_text: str = Form(""), file: UploadFile = File(...), branch_id: UUID | None = None,
    tenant: TenantContext = Depends(PermissionChecker("homework.read", "parent.view_children")),
    db: AsyncSession = Depends(get_db, scope="function")):
    settings = get_settings()
    if len(submission_text) > 10000:
        raise ValidationException("Teslim metni en fazla 10000 karakter olmalı")
    filename = Path((file.filename or "").replace("\\", "/")).name
    if not filename or len(filename) > 255 or Path(filename).suffix.lstrip(".").lower() not in settings.allowed_file_types_list:
        raise ValidationException("İzin verilen bir dosya türü seçin")
    content = await file.read(settings.max_upload_size_bytes + 1)
    if not content:
        raise ValidationException("Boş dosya yüklenemez")
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(status_code=413, detail="Dosya boyutu izin verilen sınırı aşıyor")
    record = await submission_record(db, tenant, homework_id, student_id, branch_id)
    target = attachment_path(record.id)
    temporary = target.with_name(f"{target.name}.{uuid4().hex}.tmp")
    def persist():
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            temporary.write_bytes(content)
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
    await asyncio.to_thread(persist)
    record.submission_text = submission_text.strip() or None
    record.attachment_file_name = filename
    record.attachment_file_size_mb = len(content) / (1024 * 1024)
    record.submitted_at = datetime.now(UTC)
    record.status = "SUBMITTED"
    await db.flush()
    return success_response({"id": str(record.id), "status": record.status, "attachment_url": attachment_url(record)})


@router.get("/submissions/{submission_id}/attachment")
async def download_homework_attachment(submission_id: UUID, branch_id: UUID | None = None,
    tenant: TenantContext = Depends(PermissionChecker("homework.read", "parent.view_children")),
    db: AsyncSession = Depends(get_db, scope="function")):
    from app.core.exceptions import NotFoundException
    record = (await db.execute(select(HomeworkSubmission).where(HomeworkSubmission.id == submission_id))).scalar_one_or_none()
    if record is None:
        raise NotFoundException("Teslim bulunamadı")
    await homework_service.get(db, tenant, record.homework_id, branch_id)
    await require_student_access(db, tenant, record.student_id)
    if not attachment_url(record):
        raise NotFoundException("Dosya bulunamadı")
    return FileResponse(attachment_path(record.id), filename=record.attachment_file_name,
        media_type="application/octet-stream", headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


@router.put("/submissions/{submission_id}/grade")
async def grade_submission(submission_id: UUID, body: SubmissionGrade, branch_id: UUID | None = None,
    tenant: TenantContext = Depends(PermissionChecker("homework.write")),
    db: AsyncSession = Depends(get_db, scope="function")):
    record = (await db.execute(select(HomeworkSubmission).where(HomeworkSubmission.id == submission_id).with_for_update())).scalar_one_or_none()
    if record is None:
        from app.core.exceptions import NotFoundException
        raise NotFoundException("Teslim bulunamadı")
    await homework_service.get(db, tenant, record.homework_id, branch_id)
    record.score, record.teacher_feedback, record.status = body.score, body.teacher_feedback, "GRADED"
    return success_response({"id": str(record.id), "status": record.status, "score": body.score})
