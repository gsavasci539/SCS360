"""Etüt sessions, decisions and teacher availability."""
from __future__ import annotations

from datetime import UTC, date, datetime, time
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services import tutoring_service as service
from app.application.services.consent_service import utc_iso
from app.core.database import get_db
from app.core.permissions import PermissionChecker
from app.core.responses import success_response
from app.core.tenant import TenantContext
from app.domain.entities.tutoring import TeacherAvailability, TutoringRequest, TutoringSession
from app.infrastructure.models.models import Student, User

router = APIRouter(prefix="/api/tutoring", tags=["Tutoring"])


def validate_times(start, end):
    if (start is None) != (end is None):
        raise ValueError("Başlangıç ve bitiş saati birlikte girilmeli")
    if start is not None and (start.tzinfo is not None or end.tzinfo is not None or start >= end):
        raise ValueError("Okul yerel saatinde bitiş başlangıçtan sonra olmalı")


class Input(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class TutoringSessionCreate(Input):
    teacher_id: UUID
    student_id: UUID
    subject: str | None = Field(None, max_length=100)
    session_date: date
    start_time: time
    end_time: time
    location: str | None = Field(None, max_length=255)
    notes: str | None = Field(None, max_length=4000)

    @model_validator(mode="after")
    def valid_times(self):
        validate_times(self.start_time, self.end_time)
        return self


class TutoringRequestCreate(Input):
    student_id: UUID
    teacher_id: UUID | None = None
    subject: str | None = Field(None, max_length=100)
    requested_date: date
    preferred_time_start: time | None = None
    preferred_time_end: time | None = None
    reason: str | None = Field(None, max_length=4000)

    @model_validator(mode="after")
    def valid_times(self):
        validate_times(self.preferred_time_start, self.preferred_time_end)
        return self


class TeacherAvailabilityCreate(Input):
    teacher_id: UUID
    day_of_week: int = Field(ge=0, le=6)
    start_time: time
    end_time: time
    max_students: int = Field(default=1, ge=1, le=100)

    @model_validator(mode="after")
    def valid_times(self):
        validate_times(self.start_time, self.end_time)
        return self


class SessionAttendanceUpdate(Input):
    attendance_status: Literal["PRESENT", "ABSENT", "LATE"]
    progress_score: int | None = Field(None, ge=0, le=100)
    notes: str | None = Field(None, max_length=4000)


class RequestApproval(Input):
    teacher_id: UUID | None = None


class RequestRejection(Input):
    rejection_reason: str = Field(min_length=1, max_length=2000)


def data(row):
    output = {column.name: getattr(row, column.name) for column in row.__table__.columns}
    for key, value in output.items():
        if isinstance(value, UUID):
            output[key] = str(value)
        elif isinstance(value, datetime):
            output[key] = utc_iso(value)
        elif isinstance(value, date):
            output[key] = value.isoformat()
        elif isinstance(value, time):
            output[key] = value.strftime("%H:%M")
    return output


async def enrich(db, rows):
    teachers = await service.names(db, User, {row.teacher_id for row in rows if row.teacher_id})
    students = await service.names(db, Student, {row.student_id for row in rows if hasattr(row, "student_id")})
    approvers = await service.names(db, User, {row.approved_by for row in rows if getattr(row, "approved_by", None)})
    output = []
    for row in rows:
        item = data(row)
        item["teacher_name"] = teachers.get(row.teacher_id)
        if hasattr(row, "student_id"):
            item["student_name"] = students.get(row.student_id)
        if hasattr(row, "approved_by"):
            item["approved_by_name"] = approvers.get(row.approved_by)
        output.append(item)
    return output


async def get_record(db, model, identifier):
    row = (await db.execute(select(model).where(model.id == identifier))).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "Kayıt bulunamadı veya erişim kapsamı dışında")
    return row


@router.get("/options")
async def options(student_id: UUID | None = None, teacher_id: UUID | None = None, search: str = Query("", max_length=100),
    teacher_search: str = Query("", max_length=100), db: AsyncSession = Depends(get_db, scope="function"), tenant: TenantContext = Depends(PermissionChecker("tutoring.read"))):
    return success_response(await service.options(db, tenant, student_id, search.strip(), teacher_search.strip(), teacher_id))


@router.get("/summary")
async def summary(student_id: UUID | None = None, teacher_id: UUID | None = None,
    db: AsyncSession = Depends(get_db, scope="function"), tenant: TenantContext = Depends(PermissionChecker("tutoring.read"))):
    return success_response(await service.summary(db, student_id, teacher_id))


@router.get("/sessions")
async def get_tutoring_sessions(teacher_id: UUID | None = None, student_id: UUID | None = None,
    start_date: date | None = None, end_date: date | None = None, status: Literal["SCHEDULED", "COMPLETED", "CANCELLED"] | None = None,
    limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0), db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("tutoring.read"))):
    if start_date and end_date and end_date < start_date:
        raise HTTPException(422, "Bitiş tarihi başlangıçtan önce olamaz")
    query = select(TutoringSession)
    for value, condition in ((teacher_id, TutoringSession.teacher_id == teacher_id), (student_id, TutoringSession.student_id == student_id),
        (start_date, TutoringSession.session_date >= start_date if start_date else True),
        (end_date, TutoringSession.session_date <= end_date if end_date else True), (status, TutoringSession.status == status)):
        if value is not None:
            query = query.where(condition)
    rows = (await db.execute(query.order_by(TutoringSession.session_date.desc(), TutoringSession.start_time, TutoringSession.id).limit(limit).offset(offset))).scalars().all()
    return success_response(await enrich(db, rows))


@router.post("/sessions")
async def create_tutoring_session(body: TutoringSessionCreate, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("tutoring.write"))):
    service.require_calendar_owner(tenant, body.teacher_id)
    student = await service.require_student(db, body.student_id)
    await service.require_teacher(db, tenant, body.teacher_id, student)
    await service.lock_calendar(db, [body.teacher_id], [body.student_id])
    await service.check_booking(db, body)
    row = TutoringSession(**body.model_dump(), status="SCHEDULED")
    db.add(row); await db.commit(); await db.refresh(row)
    return success_response(data(row))


@router.put("/sessions/{session_id}")
async def update_tutoring_session(session_id: UUID, body: TutoringSessionCreate, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("tutoring.write"))):
    row = await get_record(db, TutoringSession, session_id)
    service.require_calendar_owner(tenant, body.teacher_id)
    student = await service.require_student(db, body.student_id)
    await service.require_teacher(db, tenant, body.teacher_id, student)
    await service.lock_calendar(db, [row.teacher_id, body.teacher_id], [row.student_id, body.student_id])
    row = await service.lock_record(db, TutoringSession, session_id)
    if row.status != "SCHEDULED":
        raise HTTPException(409, "Yalnız planlanmış dersin zamanı değiştirilebilir")
    await service.check_booking(db, body, row.id)
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    await db.commit(); await db.refresh(row)
    return success_response(data(row))


@router.post("/sessions/{session_id}/cancel")
async def cancel_tutoring_session(session_id: UUID, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("tutoring.write"))):
    row = await get_record(db, TutoringSession, session_id)
    await service.lock_calendar(db, [row.teacher_id], [row.student_id])
    row = await service.lock_record(db, TutoringSession, session_id)
    if row.status == "COMPLETED":
        raise HTTPException(409, "Devam kaydı olan ders iptal edilemez")
    row.status = "CANCELLED"
    await db.commit()
    return success_response(data(row))


@router.post("/sessions/{session_id}/attendance")
async def mark_session_attendance(session_id: UUID, body: SessionAttendanceUpdate, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("tutoring.write"))):
    row = await get_record(db, TutoringSession, session_id)
    await service.lock_calendar(db, [row.teacher_id], [row.student_id])
    row = await service.lock_record(db, TutoringSession, session_id)
    if row.status == "CANCELLED":
        raise HTTPException(409, "İptal edilmiş dersin devamı kaydedilemez")
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    row.status = "COMPLETED"
    await db.commit()
    return success_response(data(row))


@router.get("/requests")
async def get_tutoring_requests(student_id: UUID | None = None, teacher_id: UUID | None = None,
    status: Literal["PENDING", "APPROVED", "REJECTED"] | None = None, limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db, scope="function"), tenant: TenantContext = Depends(PermissionChecker("tutoring.read"))):
    query = select(TutoringRequest)
    for value, condition in ((teacher_id, TutoringRequest.teacher_id == teacher_id), (student_id, TutoringRequest.student_id == student_id), (status, TutoringRequest.status == status)):
        if value is not None:
            query = query.where(condition)
    rows = (await db.execute(query.order_by(TutoringRequest.created_at.desc(), TutoringRequest.id).limit(limit).offset(offset))).scalars().all()
    return success_response(await enrich(db, rows))


@router.post("/requests")
async def create_tutoring_request(body: TutoringRequestCreate, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("tutoring.write"))):
    student = await service.require_student(db, body.student_id)
    if body.teacher_id:
        await service.require_teacher(db, tenant, body.teacher_id, student)
    row = TutoringRequest(**body.model_dump(), status="PENDING")
    db.add(row); await db.commit(); await db.refresh(row)
    return success_response(data(row))


@router.post("/requests/{request_id}/approve")
async def approve_tutoring_request(request_id: UUID, body: RequestApproval | None = Body(None), db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("tutoring.write"))):
    await get_record(db, TutoringRequest, request_id)
    row = await service.lock_record(db, TutoringRequest, request_id)
    teacher_id = body.teacher_id if body and body.teacher_id else row.teacher_id or (tenant.user_id if service.self_only(tenant) else None)
    if row.status == "APPROVED":
        if teacher_id != row.teacher_id:
            raise HTTPException(409, "Onaylanmış talebin öğretmeni değiştirilemez")
        return success_response(data(row))
    if row.status != "PENDING":
        raise HTTPException(409, "Yalnız bekleyen talep onaylanabilir")
    if teacher_id is None:
        raise HTTPException(422, "Onay için öğretmen seçin")
    student = await service.require_student(db, row.student_id)
    await service.require_teacher(db, tenant, teacher_id, student)
    row.teacher_id = teacher_id; row.status = "APPROVED"
    row.approved_by = tenant.user_id; row.approved_at = datetime.now(UTC)
    await db.commit()
    return success_response(data(row))


@router.post("/requests/{request_id}/reject")
async def reject_tutoring_request(request_id: UUID, body: RequestRejection | None = Body(None),
    rejection_reason: str | None = Query(None, min_length=1, max_length=2000, deprecated=True), db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("tutoring.write"))):
    await get_record(db, TutoringRequest, request_id)
    row = await service.lock_record(db, TutoringRequest, request_id)
    if row.status == "REJECTED":
        return success_response(data(row))
    if row.status != "PENDING":
        raise HTTPException(409, "Yalnız bekleyen talep reddedilebilir")
    reason = body.rejection_reason if body else (rejection_reason or "").strip()
    if not reason:
        raise HTTPException(422, "Ret gerekçesi girin")
    row.status = "REJECTED"; row.rejection_reason = reason
    await db.commit()
    return success_response(data(row))


@router.get("/availability")
async def get_teacher_availability(teacher_id: UUID | None = None, day_of_week: int | None = Query(None, ge=0, le=6),
    limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0), db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("tutoring.read"))):
    query = select(TeacherAvailability)
    if teacher_id:
        query = query.where(TeacherAvailability.teacher_id == teacher_id)
    if day_of_week is not None:
        query = query.where(TeacherAvailability.day_of_week == day_of_week)
    rows = (await db.execute(query.order_by(TeacherAvailability.day_of_week, TeacherAvailability.start_time, TeacherAvailability.id).limit(limit).offset(offset))).scalars().all()
    return success_response(await enrich(db, rows))


@router.post("/availability")
async def create_teacher_availability(body: TeacherAvailabilityCreate, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("tutoring.write"))):
    await service.require_teacher(db, tenant, body.teacher_id)
    await service.lock_calendar(db, [body.teacher_id])
    overlap = (await db.execute(select(TeacherAvailability.id).where(TeacherAvailability.teacher_id == body.teacher_id,
        TeacherAvailability.day_of_week == body.day_of_week, TeacherAvailability.is_available.is_(True),
        TeacherAvailability.start_time < body.end_time, TeacherAvailability.end_time > body.start_time).limit(1))).first()
    if overlap:
        raise HTTPException(409, "Bu öğretmenin aynı gün çakışan aktif müsaitliği var")
    row = TeacherAvailability(**body.model_dump(), is_available=True)
    db.add(row); await db.commit(); await db.refresh(row)
    return success_response(data(row))


@router.delete("/availability/{availability_id}")
async def disable_teacher_availability(availability_id: UUID, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("tutoring.write"))):
    row = await get_record(db, TeacherAvailability, availability_id)
    await service.lock_calendar(db, [row.teacher_id])
    row = await service.lock_record(db, TeacherAvailability, availability_id)
    # History is preserved. Existing bookings remain valid; disabling blocks new bookings.
    row.is_available = False
    await db.commit()
    return success_response(data(row))
