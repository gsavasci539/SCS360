"""Persisted health files, clinic visits, reviewed requests and daily dose logs."""
from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
import json
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services import infirmary_service as service
from app.core.database import get_db
from app.core.dates import school_datetime, school_time, school_today
from app.core.permissions import PermissionChecker
from app.core.responses import success_response
from app.core.tenant import TenantContext
from app.domain.entities.health import HealthRecord, InfirmaryVisit, MedicationLog, MedicationSchedule
from app.infrastructure.models.models import Student

router = APIRouter(prefix="/api/infirmary", tags=["Infirmary"])
# Import compatibility for older portal callers.
medicine_request_status = service.medicine_request_status


class Input(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, allow_inf_nan=False)


class HealthRecordCreate(Input):
    student_id: UUID | None = None
    blood_type: str | None = Field(None, max_length=5)
    allergies: str | None = Field(None, max_length=1000)
    chronic_conditions: str | None = Field(None, max_length=1000)
    emergency_contact_name: str | None = Field(None, max_length=255)
    emergency_contact_phone: str | None = Field(None, max_length=20)
    emergency_contact_relation: str | None = Field(None, max_length=50)
    insurance_info: dict | None = Field(None, max_length=100)
    last_checkup_date: date | None = None

    @model_validator(mode="after")
    def insurance_size(self):
        if self.insurance_info is not None and len(json.dumps(self.insurance_info, allow_nan=False)) > 10000:
            raise ValueError("Sigorta bilgisi en fazla 10000 karakter olabilir")
        return self


class MedicationScheduleCreate(Input):
    student_id: UUID
    medication_name: str = Field(min_length=1, max_length=255)
    dosage: str = Field(min_length=1, max_length=100)
    frequency: str = Field(min_length=1, max_length=100)
    instruction: Literal["BEFORE_MEAL", "AFTER_MEAL", "WITH_MEAL", "EMPTY_STOMACH", "NOT_SPECIFIED"] = "NOT_SPECIFIED"
    start_date: date
    end_date: date | None = None
    parent_notes: str | None = Field(None, max_length=1000)

    @model_validator(mode="after")
    def dates(self):
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("Bitiş tarihi başlangıçtan önce olamaz")
        return self


class MedicationLogCreate(Input):
    schedule_id: UUID
    student_id: UUID
    scheduled_date: date = Field(default_factory=school_today)
    scheduled_time: time
    given_time: AwareDatetime | None = None
    status: Literal["SCHEDULED", "GIVEN", "SKIPPED", "CANCELLED"] = "GIVEN"
    given_by: UUID | None = Field(None, description="Uyumluluk alanı; yetkili oturumdan alınır")
    notes: str | None = Field(None, max_length=1000)

    @model_validator(mode="after")
    def clock(self):
        if self.scheduled_time.tzinfo is not None:
            raise ValueError("Plan saati okul yerel saatinde girilmeli")
        if self.status != "GIVEN" and self.given_time is not None:
            raise ValueError("Yalnız uygulandı kaydında uygulama zamanı girilebilir")
        return self


class InfirmaryVisitCreate(Input):
    student_id: UUID
    branch_id: UUID | None = None
    visit_date: date = Field(default_factory=school_today)
    visit_time: time = Field(default_factory=school_time)
    complaint: str | None = Field(None, max_length=1000)
    temperature: float | None = Field(None, ge=35.0, le=42.0)
    blood_pressure_systolic: int | None = Field(None, ge=70, le=200)
    blood_pressure_diastolic: int | None = Field(None, ge=40, le=130)
    severity: Literal["LOW", "MEDIUM", "HIGH", "EMERGENCY"] = "LOW"
    treatment_given: str | None = Field(None, max_length=1000)
    follow_up_required: bool = False
    follow_up_notes: str | None = Field(None, max_length=1000)
    parent_notified: bool = False
    notification_method: str | None = Field(None, max_length=50)
    examined_by: UUID | None = Field(None, description="Uyumluluk alanı; yetkili oturumdan alınır")

    @model_validator(mode="after")
    def clock_and_notification(self):
        if self.visit_time.tzinfo is not None:
            raise ValueError("Ziyaret saati okul yerel saatinde girilmeli")
        if self.parent_notified and not self.notification_method:
            raise ValueError("Manuel veli bilgilendirmesinin yöntemini girin")
        return self


class MedicineRequestDecision(Input):
    status: Literal["APPROVED", "REJECTED", "COMPLETED"]


class VisitFollowUp(Input):
    follow_up_notes: str = Field(min_length=1, max_length=1000)


@router.get("/options")
async def options(student_id: UUID | None = None, search: str = Query("", max_length=100), db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("health.read"))):
    return success_response(await service.options(db, student_id, search.strip()))


@router.get("/summary")
async def summary(student_id: UUID | None = None, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("health.read"))):
    return success_response(await service.summary(db, student_id))


@router.get("/health-records")
async def get_health_records(student_id: UUID | None = None, limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db, scope="function"), tenant: TenantContext = Depends(PermissionChecker("health.read"))):
    query = select(HealthRecord)
    if student_id:
        query = query.where(HealthRecord.student_id == student_id)
    rows = (await db.execute(query.order_by(HealthRecord.updated_at.desc(), HealthRecord.id).limit(limit).offset(offset))).scalars().all()
    return success_response(await service.enrich(db, rows))


async def health_file(db, student_id):
    rows = (await db.execute(select(HealthRecord).where(HealthRecord.student_id == student_id).limit(2))).scalars().all()
    if len(rows) > 1:
        raise HTTPException(409, "Öğrencinin birden fazla eski sağlık dosyası var; kayıtlar birleştirilmeden incelenmeli")
    return rows[0] if rows else None


@router.get("/health-records/{student_id}")
async def get_health_record(student_id: UUID, db: AsyncSession = Depends(get_db, scope="function"), tenant: TenantContext = Depends(PermissionChecker("health.read"))):
    await service.student(db, student_id)
    row = await health_file(db, student_id)
    if row is None:
        raise HTTPException(404, "Sağlık dosyası henüz oluşturulmadı")
    return success_response(service.data(row))


@router.put("/health-records/{student_id}")
async def update_health_record(student_id: UUID, body: HealthRecordCreate, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("health.write"))):
    if body.student_id is not None and body.student_id != student_id:
        raise HTTPException(422, "Yol ve gövdedeki öğrenci aynı olmalı")
    child = await service.student(db, student_id)
    await service.lock(db, Student, child.id)
    row = await health_file(db, student_id)
    if row is None:
        row = HealthRecord(student_id=student_id); db.add(row)
    # Omitted fields, including older insurance data, are preserved.
    for key, value in body.model_dump(exclude={"student_id"}, exclude_unset=True).items():
        setattr(row, key, value)
    row.updated_by = tenant.user_id
    await db.flush()
    service.audit(db, tenant, child, row, "HEALTH_FILE_UPDATED", {"fields": sorted(body.model_fields_set - {"student_id"})})
    await db.commit(); await db.refresh(row)
    return success_response(service.data(row))


@router.get("/medication-schedules")
async def get_medication_schedules(student_id: UUID | None = None, is_active: bool | None = True,
    day: date | None = Query(None, alias="date"), limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db, scope="function"), tenant: TenantContext = Depends(PermissionChecker("health.read"))):
    query = select(MedicationSchedule)
    if student_id:
        query = query.where(MedicationSchedule.student_id == student_id)
    if is_active is not None:
        query = query.where(MedicationSchedule.is_active == is_active)
    if day:
        query = query.where(MedicationSchedule.start_date <= day, or_(MedicationSchedule.end_date.is_(None), MedicationSchedule.end_date >= day))
    rows = (await db.execute(query.order_by(MedicationSchedule.start_date.desc(), MedicationSchedule.id).limit(limit).offset(offset))).scalars().all()
    return success_response(await service.enrich(db, rows))


@router.post("/medication-schedules")
async def create_medication_schedule(body: MedicationScheduleCreate, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("health.write"))):
    child = await service.student(db, body.student_id)
    row = MedicationSchedule(**body.model_dump(), is_active=True, request_status="APPROVED", created_by=tenant.user_id, updated_by=tenant.user_id)
    db.add(row); await db.flush()
    service.audit(db, tenant, child, row, "MEDICATION_SCHEDULE_CREATED", {"status": "APPROVED"})
    await db.commit(); await db.refresh(row)
    return success_response(service.data(row))


@router.post("/medication/mark-given")
async def mark_medication_given(body: MedicationLogCreate, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("health.write"))):
    child = await service.student(db, body.student_id)
    schedule = await service.get_record(db, MedicationSchedule, body.schedule_id)
    if schedule.student_id != child.id:
        raise HTTPException(403, "İlaç programı bu öğrenciye ait değil")
    schedule = await service.lock(db, MedicationSchedule, schedule.id)
    if not schedule.is_active or service.medicine_request_status(schedule) != "APPROVED":
        raise HTTPException(409, "Yalnız onaylı ve açık program için doz kaydı tutulabilir")
    if body.scheduled_date < schedule.start_date or (schedule.end_date and body.scheduled_date > schedule.end_date):
        raise HTTPException(422, "Doz günü programın tarih aralığında olmalı")
    rows = (await db.execute(select(MedicationLog).where(MedicationLog.schedule_id == schedule.id,
        MedicationLog.student_id == child.id, MedicationLog.scheduled_time == body.scheduled_time, service.dose_day(body.scheduled_date)).limit(2))).scalars().all()
    if len(rows) > 1:
        raise HTTPException(409, "Bu gün ve saatte birden fazla eski kayıt var; geçmiş incelenmeli")
    row = rows[0] if rows else None
    if row and row.status != "SCHEDULED":
        if row.status != body.status:
            raise HTTPException(409, "Kesinleşmiş doz kaydı farklı bir sonuca çevrilemez")
        return success_response(service.data(row))
    instant = body.given_time.astimezone(UTC) if body.given_time else datetime.now(UTC)
    if body.status == "GIVEN" and (school_datetime(instant).date() != body.scheduled_date or instant > datetime.now(UTC) + timedelta(minutes=5)):
        raise HTTPException(422, "Uygulama zamanı doz gününde ve gelecekte olmayacak şekilde girilmeli")
    if row is None:
        row = MedicationLog(schedule_id=schedule.id, student_id=child.id, scheduled_date=body.scheduled_date, scheduled_time=body.scheduled_time)
        db.add(row)
    row.status = body.status; row.given_time = instant if body.status == "GIVEN" else None
    row.given_by = tenant.user_id; row.notes = body.notes
    await db.flush()
    service.audit(db, tenant, child, row, "MEDICATION_DOSE_RECORDED", {"status": row.status, "scheduled_date": str(body.scheduled_date), "schedule_id": str(schedule.id)})
    await db.commit(); await db.refresh(row)
    return success_response(service.data(row))


@router.get("/medication-logs")
async def get_medication_logs(student_id: UUID | None = None, day: date | None = Query(None, alias="date"),
    status: Literal["SCHEDULED", "GIVEN", "SKIPPED", "CANCELLED"] | None = None, limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db, scope="function"), tenant: TenantContext = Depends(PermissionChecker("health.read"))):
    query = select(MedicationLog).join(MedicationSchedule, and_(MedicationSchedule.id == MedicationLog.schedule_id,
        MedicationSchedule.student_id == MedicationLog.student_id))
    if student_id:
        query = query.where(MedicationLog.student_id == student_id)
    if day:
        query = query.where(service.dose_day(day))
    if status:
        query = query.where(MedicationLog.status == status)
    rows = (await db.execute(query.order_by(MedicationLog.created_at.desc(), MedicationLog.scheduled_time, MedicationLog.id).limit(limit).offset(offset))).scalars().all()
    return success_response(await service.enrich(db, rows))


@router.post("/infirmary-visits")
async def create_infirmary_visit(body: InfirmaryVisitCreate, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("health.write"))):
    child = await service.student(db, body.student_id)
    if body.branch_id and body.branch_id != child.branch_id:
        raise HTTPException(403, "Ziyaret şubesi öğrencinin şubesiyle aynı olmalı")
    row = InfirmaryVisit(**body.model_dump(exclude={"branch_id", "examined_by", "notification_method"}), branch_id=child.branch_id,
        examined_by=tenant.user_id, notification_method=body.notification_method if body.parent_notified else None)
    db.add(row); await db.flush()
    service.audit(db, tenant, child, row, "INFIRMARY_VISIT_CREATED", {"follow_up_required": row.follow_up_required})
    await db.commit(); await db.refresh(row)
    return success_response(service.data(row))


@router.get("/infirmary-visits")
async def get_infirmary_visits(student_id: UUID | None = None, branch_id: UUID | None = None, start_date: date | None = None, end_date: date | None = None,
    severity: Literal["LOW", "MEDIUM", "HIGH", "EMERGENCY"] | None = None, limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db, scope="function"), tenant: TenantContext = Depends(PermissionChecker("health.read"))):
    if start_date and end_date and end_date < start_date:
        raise HTTPException(422, "Bitiş tarihi başlangıçtan önce olamaz")
    query = select(InfirmaryVisit)
    for value, condition in ((student_id, InfirmaryVisit.student_id == student_id), (branch_id, InfirmaryVisit.branch_id == branch_id),
        (start_date, InfirmaryVisit.visit_date >= start_date if start_date else True), (end_date, InfirmaryVisit.visit_date <= end_date if end_date else True), (severity, InfirmaryVisit.severity == severity)):
        if value is not None:
            query = query.where(condition)
    rows = (await db.execute(query.order_by(InfirmaryVisit.visit_date.desc(), InfirmaryVisit.visit_time.desc(), InfirmaryVisit.id).limit(limit).offset(offset))).scalars().all()
    return success_response(await service.enrich(db, rows))


@router.post("/infirmary-visits/{visit_id}/follow-up")
async def complete_follow_up(visit_id: UUID, body: VisitFollowUp, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("health.write"))):
    visit = await service.get_record(db, InfirmaryVisit, visit_id)
    child = await service.student(db, visit.student_id)
    visit = await service.lock(db, InfirmaryVisit, visit_id)
    if visit.follow_up_required:
        visit.follow_up_required = False; visit.follow_up_notes = body.follow_up_notes
        service.audit(db, tenant, child, visit, "INFIRMARY_FOLLOW_UP_COMPLETED", {"follow_up_required": False})
    await db.commit()
    return success_response(service.data(visit))


@router.get("/daily-medication-schedule")
async def get_daily_medication_schedule(day: date = Query(..., alias="date"), student_id: UUID | None = None,
    limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0), db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("health.read"))):
    query = select(MedicationSchedule).where(MedicationSchedule.is_active.is_(True), service.status_expression() == "APPROVED",
        MedicationSchedule.start_date <= day, or_(MedicationSchedule.end_date.is_(None), MedicationSchedule.end_date >= day))
    if student_id:
        query = query.where(MedicationSchedule.student_id == student_id)
    rows = (await db.execute(query.order_by(MedicationSchedule.student_id, MedicationSchedule.id).limit(limit).offset(offset))).scalars().all()
    enriched = await service.enrich(db, rows)
    logs = (await db.execute(select(MedicationLog).where(MedicationLog.schedule_id.in_([row.id for row in rows]), service.dose_day(day))
        .order_by(MedicationLog.scheduled_time, MedicationLog.id))).scalars().all() if rows else []
    for item, row in zip(enriched, rows):
        doses = [service.data(log) for log in logs if log.schedule_id == row.id and log.student_id == row.student_id]
        item.update({"schedule_id": str(row.id), "logs": doses,
            "status": "GIVEN" if doses and all(dose["status"] == "GIVEN" for dose in doses) else "PARTIAL" if any(dose["status"] == "GIVEN" for dose in doses) else "SCHEDULED"})
    return success_response(enriched)


@router.get("/medicine-requests")
async def get_medicine_requests(student_id: UUID | None = None, status: Literal["PENDING", "APPROVED", "REJECTED", "COMPLETED"] | None = None,
    limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0), db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("health.read"))):
    query = select(MedicationSchedule)
    if student_id:
        query = query.where(MedicationSchedule.student_id == student_id)
    if status:
        query = query.where(service.status_expression() == status)
    rows = (await db.execute(query.order_by(MedicationSchedule.created_at.desc(), MedicationSchedule.id).limit(limit).offset(offset))).scalars().all()
    items = await service.enrich(db, rows)
    for item, row in zip(items, rows):
        item.update({"medicine_name": row.medication_name, "time_to_give": row.frequency, "instructions": service.instructions(row)})
    return success_response(items)


@router.put("/medicine-requests/{request_id}")
async def update_medicine_request(request_id: UUID, body: MedicineRequestDecision, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("health.write"))):
    return success_response(service.data(await service.decide_request(db, tenant, request_id, body.status)))
