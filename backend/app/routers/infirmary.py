"""
Infirmary & Medication Log Module API
Handles health records, medication schedules, and infirmary visits
"""
from datetime import datetime, date, time
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.responses import success_response
from app.core.security import PermissionChecker, TenantContext
from app.domain.entities import Student, User, Branch

router = APIRouter(prefix="/api/infirmary", tags=["Infirmary"])


# ==================== Schemas ====================

class HealthRecordCreate(BaseModel):
    student_id: UUID
    blood_type: Optional[str] = Field(None, max_length=5)
    allergies: Optional[str] = None
    chronic_conditions: Optional[str] = None
    emergency_contact_name: Optional[str] = Field(None, max_length=255)
    emergency_contact_phone: Optional[str] = Field(None, max_length=20)
    emergency_contact_relation: Optional[str] = Field(None, max_length=50)
    insurance_info: Optional[dict] = None
    last_checkup_date: Optional[date] = None

class MedicationScheduleCreate(BaseModel):
    student_id: UUID
    medication_name: str = Field(..., max_length=255)
    dosage: str = Field(..., max_length=100)
    frequency: str = Field(..., max_length=100)
    instruction: str = Field(default="AFTER_MEAL", description="BEFORE_MEAL, AFTER_MEAL, WITH_MEAL, EMPTY_STOMACH")
    start_date: date = Field(..., description="Start date for medication")
    end_date: Optional[date] = None
    parent_notes: Optional[str] = None

class MedicationLogCreate(BaseModel):
    schedule_id: UUID
    student_id: UUID
    scheduled_time: time = Field(..., description="Scheduled time for medication")
    given_time: Optional[datetime] = None
    status: str = Field(default="SCHEDULED", description="SCHEDULED, GIVEN, SKIPPED, CANCELLED")
    given_by: Optional[UUID] = None
    notes: Optional[str] = None

class InfirmaryVisitCreate(BaseModel):
    student_id: UUID
    branch_id: Optional[UUID] = None
    visit_date: date = Field(default_factory=lambda: date.today())
    visit_time: time = Field(default_factory=lambda: datetime.now().time())
    complaint: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=35.0, le=42.0)
    blood_pressure_systolic: Optional[int] = Field(None, ge=70, le=200)
    blood_pressure_diastolic: Optional[int] = Field(None, ge=40, le=130)
    severity: str = Field(default="LOW", description="LOW, MEDIUM, HIGH, EMERGENCY")
    treatment_given: Optional[str] = None
    follow_up_required: bool = Field(default=False)
    follow_up_notes: Optional[str] = None
    parent_notified: bool = Field(default=False)
    notification_method: Optional[str] = None
    examined_by: Optional[UUID] = None


# ==================== Health Records Endpoints ====================

@router.get("/health-records")
async def get_health_records(
    student_id: Optional[UUID] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("health.read"))
):
    """Get health records list"""
    from app.domain.entities.health import HealthRecord
    
    query = select(HealthRecord)
    
    if student_id:
        query = query.where(HealthRecord.student_id == student_id)
    
    query = query.order_by(HealthRecord.updated_at.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    records = result.scalars().all()
    
    enriched_records = []
    for record in records:
        student_name = None
        if record.student_id:
            student_result = await db.execute(
                select(Student).where(Student.id == record.student_id)
            )
            student = student_result.scalar_one_or_none()
            if student:
                student_name = f"{student.first_name} {student.last_name}"
        
        enriched_records.append({
            "id": str(record.id),
            "student_id": str(record.student_id),
            "student_name": student_name,
            "blood_type": record.blood_type,
            "allergies": record.allergies,
            "chronic_conditions": record.chronic_conditions,
            "emergency_contact_name": record.emergency_contact_name,
            "emergency_contact_phone": record.emergency_contact_phone,
            "emergency_contact_relation": record.emergency_contact_relation,
            "insurance_info": record.insurance_info,
            "last_checkup_date": record.last_checkup_date.isoformat() if record.last_checkup_date else None,
            "updated_at": record.updated_at.isoformat()
        })
    
    return success_response(enriched_records)


@router.get("/health-records/{student_id}")
async def get_health_record(
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("health.read"))
):
    """Get health record for a student"""
    # Import models here to avoid circular imports
    from app.domain.entities.health import HealthRecord
    
    result = await db.execute(
        select(HealthRecord).where(HealthRecord.student_id == student_id)
    )
    record = result.scalar_one_or_none()
    
    if not record:
        raise HTTPException(status_code=404, detail="Health record not found")
    
    return success_response({
        "id": str(record.id),
        "student_id": str(record.student_id),
        "blood_type": record.blood_type,
        "allergies": record.allergies,
        "chronic_conditions": record.chronic_conditions,
        "emergency_contact_name": record.emergency_contact_name,
        "emergency_contact_phone": record.emergency_contact_phone,
        "emergency_contact_relation": record.emergency_contact_relation,
        "insurance_info": record.insurance_info,
        "last_checkup_date": record.last_checkup_date.isoformat() if record.last_checkup_date else None,
        "updated_at": record.updated_at.isoformat()
    })


@router.put("/health-records/{student_id}")
async def update_health_record(
    student_id: UUID,
    record: HealthRecordCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("health.write"))
):
    """Update health record for a student"""
    from app.domain.entities.health import HealthRecord
    
    result = await db.execute(
        select(HealthRecord).where(HealthRecord.student_id == student_id)
    )
    existing_record = result.scalar_one_or_none()
    
    if existing_record:
        existing_record.blood_type = record.blood_type
        existing_record.allergies = record.allergies
        existing_record.chronic_conditions = record.chronic_conditions
        existing_record.emergency_contact_name = record.emergency_contact_name
        existing_record.emergency_contact_phone = record.emergency_contact_phone
        existing_record.emergency_contact_relation = record.emergency_contact_relation
        existing_record.insurance_info = record.insurance_info
        existing_record.last_checkup_date = record.last_checkup_date
    else:
        new_record = HealthRecord(
            student_id=record.student_id,
            blood_type=record.blood_type,
            allergies=record.allergies,
            chronic_conditions=record.chronic_conditions,
            emergency_contact_name=record.emergency_contact_name,
            emergency_contact_phone=record.emergency_contact_phone,
            emergency_contact_relation=record.emergency_contact_relation,
            insurance_info=record.insurance_info,
            last_checkup_date=record.last_checkup_date
        )
        db.add(new_record)
    
    await db.commit()
    
    return success_response({"message": "Health record updated successfully"})


# ==================== Medication Schedules Endpoints ====================

@router.get("/medication-schedules")
async def get_medication_schedules(
    student_id: Optional[UUID] = Query(None),
    is_active: Optional[bool] = Query(True),
    date: Optional[date] = Query(None, description="Filter by date"),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("health.read"))
):
    """Get medication schedules with filtering"""
    from app.domain.entities.health import MedicationSchedule
    
    query = select(MedicationSchedule)
    
    conditions = []
    if student_id:
        conditions.append(MedicationSchedule.student_id == student_id)
    if is_active is not None:
        conditions.append(MedicationSchedule.is_active == is_active)
    if date:
        conditions.append(MedicationSchedule.start_date <= date)
        conditions.append((MedicationSchedule.end_date.is_(None)) | (MedicationSchedule.end_date >= date))
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(MedicationSchedule.start_time)
    
    result = await db.execute(query)
    schedules = result.scalars().all()
    
    enriched_schedules = []
    for schedule in schedules:
        # Get student name
        student_name = None
        if schedule.student_id:
            student_result = await db.execute(
                select(Student).where(Student.id == schedule.student_id)
            )
            student = student_result.scalar_one_or_none()
            if student:
                student_name = f"{student.first_name} {student.last_name}"
        
        enriched_schedules.append({
            "id": str(schedule.id),
            "student_id": str(schedule.student_id),
            "student_name": student_name,
            "medication_name": schedule.medication_name,
            "dosage": schedule.dosage,
            "frequency": schedule.frequency,
            "instruction": schedule.instruction,
            "start_date": schedule.start_date.isoformat(),
            "end_date": schedule.end_date.isoformat() if schedule.end_date else None,
            "parent_notes": schedule.parent_notes,
            "is_active": schedule.is_active,
            "created_at": schedule.created_at.isoformat()
        })
    
    return success_response(enriched_schedules)


@router.post("/medication-schedules")
async def create_medication_schedule(
    schedule: MedicationScheduleCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("health.write"))
):
    """Create a new medication schedule"""
    from app.domain.entities.health import MedicationSchedule
    
    new_schedule = MedicationSchedule(
        student_id=schedule.student_id,
        medication_name=schedule.medication_name,
        dosage=schedule.dosage,
        frequency=schedule.frequency,
        instruction=schedule.instruction,
        start_date=schedule.start_date,
        end_date=schedule.end_date,
        parent_notes=schedule.parent_notes,
        is_active=True
    )
    db.add(new_schedule)
    await db.commit()
    await db.refresh(new_schedule)
    
    return success_response({
        "id": str(new_schedule.id),
        "medication_name": new_schedule.medication_name,
        "created_at": new_schedule.created_at.isoformat()
    })


@router.post("/medication/mark-given")
async def mark_medication_given(
    log: MedicationLogCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("health.write"))
):
    """Mark medication as given"""
    from app.domain.entities.health import MedicationLog
    
    # Create or update medication log
    existing_result = await db.execute(
        select(MedicationLog).where(
            and_(
                MedicationLog.schedule_id == log.schedule_id,
                MedicationLog.student_id == log.student_id,
                MedicationLog.scheduled_time == log.scheduled_time
            )
        )
    )
    existing = existing_result.scalar_one_or_none()
    
    if existing:
        existing.status = log.status
        existing.given_time = log.given_time or datetime.utcnow()
        existing.given_by = log.given_by
        existing.notes = log.notes
    else:
        new_log = MedicationLog(
            schedule_id=log.schedule_id,
            student_id=log.student_id,
            scheduled_time=log.scheduled_time,
            given_time=log.given_time or datetime.utcnow(),
            status=log.status,
            given_by=log.given_by,
            notes=log.notes
        )
        db.add(new_log)
    
    await db.commit()
    
    return success_response({
        "message": "Medication marked as given",
        "status": log.status,
        "given_time": (log.given_time or datetime.utcnow()).isoformat()
    })


@router.get("/medication-logs")
async def get_medication_logs(
    student_id: Optional[UUID] = Query(None),
    date: Optional[date] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("health.read"))
):
    """Get medication logs"""
    from app.domain.entities.health import MedicationLog
    
    query = select(MedicationLog)
    
    conditions = []
    if student_id:
        conditions.append(MedicationLog.student_id == student_id)
    if date:
        conditions.append(MedicationLog.created_at >= date)
        conditions.append(MedicationLog.created_at < date + timedelta(days=1))
    if status:
        conditions.append(MedicationLog.status == status.upper())
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(MedicationLog.scheduled_time.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    enriched_logs = []
    for log in logs:
        # Get student name
        student_name = None
        if log.student_id:
            student_result = await db.execute(
                select(Student).where(Student.id == log.student_id)
            )
            student = student_result.scalar_one_or_none()
            if student:
                student_name = f"{student.first_name} {student.last_name}"
        
        # Get given by name
        given_by_name = None
        if log.given_by:
            user_result = await db.execute(
                select(User).where(User.id == log.given_by)
            )
            user = user_result.scalar_one_or_none()
            if user:
                given_by_name = f"{user.first_name} {user.last_name}"
        
        enriched_logs.append({
            "id": str(log.id),
            "schedule_id": str(log.schedule_id),
            "student_id": str(log.student_id),
            "student_name": student_name,
            "scheduled_time": log.scheduled_time.strftime("%H:%M"),
            "given_time": log.given_time.isoformat() if log.given_time else None,
            "status": log.status,
            "given_by": str(log.given_by) if log.given_by else None,
            "given_by_name": given_by_name,
            "notes": log.notes,
            "created_at": log.created_at.isoformat()
        })
    
    return success_response(enriched_logs)


# ==================== Infirmary Visits Endpoints ====================

@router.post("/infirmary-visits")
async def create_infirmary_visit(
    visit: InfirmaryVisitCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("health.write"))
):
    """Create a new infirmary visit"""
    from app.domain.entities.health import InfirmaryVisit
    
    new_visit = InfirmaryVisit(
        student_id=visit.student_id,
        branch_id=visit.branch_id,
        visit_date=visit.visit_date,
        visit_time=visit.visit_time,
        complaint=visit.complaint,
        temperature=visit.temperature,
        blood_pressure_systolic=visit.blood_pressure_systolic,
        blood_pressure_diastolic=visit.blood_pressure_diastolic,
        severity=visit.severity.upper(),
        treatment_given=visit.treatment_given,
        follow_up_required=visit.follow_up_required,
        follow_up_notes=visit.follow_up_notes,
        parent_notified=visit.parent_notified,
        notification_method=visit.notification_method,
        examined_by=visit.examined_by
    )
    db.add(new_visit)
    await db.commit()
    await db.refresh(new_visit)
    
    # TODO: Trigger parent notification if parent_notified is True
    
    return success_response({
        "id": str(new_visit.id),
        "visit_date": new_visit.visit_date.isoformat(),
        "visit_time": new_visit.visit_time.strftime("%H:%M"),
        "severity": new_visit.severity,
        "created_at": new_visit.created_at.isoformat()
    })


@router.get("/infirmary-visits")
async def get_infirmary_visits(
    student_id: Optional[UUID] = Query(None),
    branch_id: Optional[UUID] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("health.read"))
):
    """Get infirmary visits with filtering"""
    from app.domain.entities.health import InfirmaryVisit
    
    query = select(InfirmaryVisit)
    
    conditions = []
    if student_id:
        conditions.append(InfirmaryVisit.student_id == student_id)
    if branch_id:
        conditions.append(InfirmaryVisit.branch_id == branch_id)
    if start_date:
        conditions.append(InfirmaryVisit.visit_date >= start_date)
    if end_date:
        conditions.append(InfirmaryVisit.visit_date <= end_date)
    if severity:
        conditions.append(InfirmaryVisit.severity == severity.upper())
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(InfirmaryVisit.visit_date.desc(), InfirmaryVisit.visit_time.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    visits = result.scalars().all()
    
    enriched_visits = []
    for visit in visits:
        # Get student name
        student_name = None
        if visit.student_id:
            student_result = await db.execute(
                select(Student).where(Student.id == visit.student_id)
            )
            student = student_result.scalar_one_or_none()
            if student:
                student_name = f"{student.first_name} {student.last_name}"
        
        # Get branch name
        branch_name = None
        if visit.branch_id:
            branch_result = await db.execute(
                select(Branch).where(Branch.id == visit.branch_id)
            )
            branch = branch_result.scalar_one_or_none()
            if branch:
                branch_name = branch.name
        
        # Get examined by name
        examined_by_name = None
        if visit.examined_by:
            user_result = await db.execute(
                select(User).where(User.id == visit.examined_by)
            )
            user = user_result.scalar_one_or_none()
            if user:
                examined_by_name = f"{user.first_name} {user.last_name}"
        
        enriched_visits.append({
            "id": str(visit.id),
            "student_id": str(visit.student_id),
            "student_name": student_name,
            "branch_id": str(visit.branch_id) if visit.branch_id else None,
            "branch_name": branch_name,
            "visit_date": visit.visit_date.isoformat(),
            "visit_time": visit.visit_time.strftime("%H:%M"),
            "complaint": visit.complaint,
            "temperature": float(visit.temperature) if visit.temperature else None,
            "blood_pressure_systolic": visit.blood_pressure_systolic,
            "blood_pressure_diastolic": visit.blood_pressure_diastolic,
            "severity": visit.severity,
            "treatment_given": visit.treatment_given,
            "follow_up_required": visit.follow_up_required,
            "follow_up_notes": visit.follow_up_notes,
            "parent_notified": visit.parent_notified,
            "notification_method": visit.notification_method,
            "examined_by": str(visit.examined_by) if visit.examined_by else None,
            "examined_by_name": examined_by_name,
            "created_at": visit.created_at.isoformat()
        })
    
    return success_response(enriched_visits)


@router.get("/daily-medication-schedule")
async def get_daily_medication_schedule(
    date: date = Query(..., description="Date to get schedule for"),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("health.read"))
):
    """Get daily medication schedule for all students"""
    from app.domain.entities.health import MedicationSchedule, MedicationLog
    
    # Get active schedules for the date
    result = await db.execute(
        select(MedicationSchedule).where(
            and_(
                MedicationSchedule.is_active == True,
                MedicationSchedule.start_date <= date,
                (MedicationSchedule.end_date.is_(None)) | (MedicationSchedule.end_date >= date)
            )
        )
    )
    schedules = result.scalars().all()
    
    daily_schedule = []
    for schedule in schedules:
        # Get student name
        student_result = await db.execute(
            select(Student).where(Student.id == schedule.student_id)
        )
        student = student_result.scalar_one_or_none()
        
        # Check if already given today
        log_result = await db.execute(
            select(MedicationLog).where(
                and_(
                    MedicationLog.schedule_id == schedule.id,
                    MedicationLog.student_id == schedule.student_id,
                    MedicationLog.created_at >= date,
                    MedicationLog.created_at < date + timedelta(days=1)
                )
            )
        )
        log = log_result.scalar_one_or_none()
        
        daily_schedule.append({
            "schedule_id": str(schedule.id),
            "student_id": str(schedule.student_id),
            "student_name": f"{student.first_name} {student.last_name}" if student else None,
            "medication_name": schedule.medication_name,
            "dosage": schedule.dosage,
            "frequency": schedule.frequency,
            "instruction": schedule.instruction,
            "status": log.status if log else "SCHEDULED",
            "given_time": log.given_time.isoformat() if log and log.given_time else None,
            "given_by": str(log.given_by) if log and log.given_by else None
        })
    
    return success_response(daily_schedule)


# Import timedelta for date calculations
from datetime import timedelta


# ==================== Medicine Requests Endpoints (for frontend compatibility) ====================

@router.get("/medicine-requests")
async def get_medicine_requests(
    student_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("health.read"))
):
    """Get medicine requests (alias for medication schedules)"""
    from app.domain.entities.health import MedicationSchedule
    
    query = select(MedicationSchedule)
    
    conditions = []
    if student_id:
        conditions.append(MedicationSchedule.student_id == student_id)
    if status:
        # Map frontend status to backend is_active
        if status == "PENDING":
            conditions.append(MedicationSchedule.is_active == True)
        elif status == "COMPLETED":
            conditions.append(MedicationSchedule.is_active == False)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(MedicationSchedule.start_date.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    schedules = result.scalars().all()
    
    enriched_requests = []
    for schedule in schedules:
        student_name = None
        if schedule.student_id:
            student_result = await db.execute(
                select(Student).where(Student.id == schedule.student_id)
            )
            student = student_result.scalar_one_or_none()
            if student:
                student_name = f"{student.first_name} {student.last_name}"
        
        enriched_requests.append({
            "id": str(schedule.id),
            "student_id": str(schedule.student_id),
            "student_name": student_name,
            "medicine_name": schedule.medication_name,
            "dosage": schedule.dosage,
            "time_to_give": schedule.frequency,
            "instructions": schedule.instruction,
            "status": "APPROVED" if schedule.is_active else "COMPLETED",
            "created_at": schedule.created_at.isoformat()
        })
    
    return success_response(enriched_requests)


@router.put("/medicine-requests/{request_id}")
async def update_medicine_request(
    request_id: UUID,
    status_data: dict,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("health.write"))
):
    """Update medicine request status"""
    from app.domain.entities.health import MedicationSchedule
    
    result = await db.execute(
        select(MedicationSchedule).where(MedicationSchedule.id == request_id)
    )
    schedule = result.scalar_one_or_none()
    
    if not schedule:
        raise HTTPException(status_code=404, detail="İlaç talebi bulunamadı")
    
    status = status_data.get("status", "COMPLETED")
    if status == "COMPLETED":
        schedule.is_active = False
    elif status == "APPROVED":
        schedule.is_active = True
    
    await db.commit()
    
    return success_response({
        "id": str(schedule.id),
        "status": status
    }, "İlaç talebi güncellendi")
