"""
Appointments Module API
Handles teacher-parent appointment scheduling and management
"""
from __future__ import annotations
from datetime import UTC, datetime, date, time, timedelta
from zoneinfo import ZoneInfo
from typing import Optional, List
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_tenant_context
from app.core.permissions import PermissionChecker
from app.core.responses import success_response, paginate
from app.domain.entities.user import User
from app.core.tenant import TenantContext

router = APIRouter(prefix="/api/appointments", tags=["Appointments"])


# ==================== Schemas ====================

class AppointmentCreate(BaseModel):
    teacher_id: UUID
    student_id: UUID
    slot_datetime: datetime
    parent_note: Optional[str] = None
    duration_minutes: int = Field(default=30, ge=15, le=60)


class AppointmentUpdate(BaseModel):
    status: str = Field(..., description="APPROVED, REJECTED, CANCELLED, COMPLETED")
    teacher_note: Optional[str] = None


class TimeSlotCreate(BaseModel):
    teacher_id: UUID
    date: date
    start_time: time
    end_time: time
    is_available: bool = Field(default=True)




# ==================== Admin Endpoints ====================

@router.get("")
async def list_appointments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("appointments.read"))
):
    from app.application.services import appointment_service
    rows = await appointment_service.records(db, tenant, status)
    return success_response(paginate(rows[(page - 1) * page_size:page * page_size], len(rows), page, page_size))


@router.get("/{appointment_id}")
async def get_appointment(
    appointment_id: str,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("appointments.read"))
):
    from app.application.services import appointment_service
    from app.core.exceptions import NotFoundException
    records = await appointment_service.records(db, tenant)
    record = next((row for row in records if row["id"] == appointment_id), None)
    if record is None:
        raise NotFoundException("Randevu bulunamadı")
    return success_response(record)


@router.put("/{appointment_id}")
async def update_appointment(
    appointment_id: str,
    update_data: AppointmentUpdate,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("appointments.write"))
):
    from app.application.services import appointment_service
    from app.application.schemas.common import AppointmentStatusUpdate
    return success_response(await appointment_service.update_status(db, tenant, appointment_id,
        AppointmentStatusUpdate(status=update_data.status.upper(), feedback_notes=update_data.teacher_note)))


@router.delete("/{appointment_id}")
async def delete_appointment(
    appointment_id: str,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("appointments.write"))
):
    from app.application.services import appointment_service
    await appointment_service.delete(db, tenant, appointment_id)
    return success_response(message="Randevu silindi")


@router.post("")
async def create_appointment(
    body: AppointmentCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("appointments.write"))
):
    from app.application.services import appointment_service
    from app.application.schemas.common import AppointmentCreate as PersistentCreate
    return success_response(await appointment_service.create(db, tenant,
        PersistentCreate.model_validate(body.model_dump(mode="json"))), "Randevu oluşturuldu")


# ==================== Teacher Endpoints ====================

@router.get("/my-appointments")
async def get_my_appointments(
    status: Optional[str] = Query(None),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("appointments.read"))
):
    from app.application.services import appointment_service
    records = await appointment_service.records(db, tenant, status=status, mine=True)
    if start_date:
        records = [row for row in records if row["appointment_date"] >= start_date.isoformat()]
    if end_date:
        records = [row for row in records if row["appointment_date"] <= end_date.isoformat()]
    return success_response(records)


@router.get("/teacher-slots/{teacher_id}")
async def get_teacher_available_slots(
    teacher_id: UUID,
    date: date = Query(..., description="Date to get slots for"),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("appointments.read"))
):
    """Get available time slots for a teacher on a specific date"""
    from app.infrastructure.models.models import Appointment, TimeSlot
    from app.infrastructure.repositories.base import BaseRepository
    from app.infrastructure.models.models import User as UserModel
    await BaseRepository(db, tenant).get_by_id(teacher_id, UserModel)
    
    # Get existing appointments for this teacher on this date
    school_zone = ZoneInfo("Europe/Istanbul")
    start_of_day = datetime.combine(date, time.min, school_zone).astimezone(UTC)
    end_of_day = datetime.combine(date, time.max, school_zone).astimezone(UTC)
    
    appointment_result = await db.execute(
        select(Appointment).where(
            and_(
                Appointment.teacher_id == teacher_id,
                Appointment.deleted_at.is_(None),
                Appointment.slot_datetime >= start_of_day,
                Appointment.slot_datetime <= end_of_day,
                Appointment.status.in_(["PENDING", "APPROVED", "CONFIRMED"])
            )
        )
    )
    appointments = appointment_result.scalars().all()
    
    # Get predefined time slots
    slot_result = await db.execute(
        select(TimeSlot).where(
            and_(
                TimeSlot.teacher_id == teacher_id,
                TimeSlot.date == date,
                TimeSlot.is_available == True
            )
        ).order_by(TimeSlot.start_time)
    )
    time_slots = slot_result.scalars().all()
    
    # Calculate available slots
    available_slots = []
    for slot in time_slots:
        slot_start = datetime.combine(date, slot.start_time, school_zone)
        slot_end = datetime.combine(date, slot.end_time, school_zone)
        
        # Check if this slot conflicts with any appointment
        is_booked = False
        for appointment in appointments:
            appointment_start = appointment.slot_datetime
            if appointment_start.tzinfo is None:
                appointment_start = appointment_start.replace(tzinfo=UTC)
            appointment_start = appointment_start.astimezone(school_zone)
            appointment_end = appointment_start + timedelta(minutes=appointment.duration_minutes)
            
            # Check for overlap
            if not (appointment_end <= slot_start or appointment_start >= slot_end):
                is_booked = True
                break
        
        if not is_booked:
            available_slots.append({
                "teacher_id": str(teacher_id),
                "date": date.isoformat(),
                "start_time": slot.start_time.strftime("%H:%M"),
                "end_time": slot.end_time.strftime("%H:%M"),
                "duration_minutes": (slot_end - slot_start).total_seconds() / 60
            })
    
    return success_response(available_slots)


@router.put("/{appointment_id}/status")
async def update_appointment_status(
    appointment_id: UUID,
    update_data: AppointmentUpdate,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("appointments.write"))
):
    from app.application.services import appointment_service
    from app.application.schemas.common import AppointmentStatusUpdate
    return success_response(await appointment_service.update_status(db, tenant, appointment_id,
        AppointmentStatusUpdate(status=update_data.status.upper(), feedback_notes=update_data.teacher_note)))


# ==================== Parent Endpoints ====================

@router.post("/request")
async def request_appointment(
    appointment_data: AppointmentCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("appointments.write"))
):
    from app.application.services import appointment_service
    from app.application.schemas.common import AppointmentCreate as PersistentCreate
    from app.core.student_access import require_student_access
    await require_student_access(db, tenant, appointment_data.student_id)
    return success_response(await appointment_service.create(db, tenant,
        PersistentCreate.model_validate(appointment_data.model_dump(mode="json"))), "Randevu talebi oluşturuldu")


# ==================== Time Slot Management (Teacher) ====================

@router.post("/slots")
async def create_time_slot(
    slot_data: TimeSlotCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("appointments.write"))
):
    """Create available time slot for appointments"""
    from app.infrastructure.models.models import TimeSlot
    
    # Verify teacher is creating slot for themselves
    if not tenant.is_super_admin and slot_data.teacher_id != tenant.user_id:
        raise HTTPException(status_code=403, detail="Sadece kendi saatlerinizi oluşturabilirsiniz")
    
    from app.infrastructure.repositories.base import BaseRepository
    from app.infrastructure.models.models import User as UserModel
    await BaseRepository(db, tenant).get_by_id(slot_data.teacher_id, UserModel)
    if slot_data.end_time <= slot_data.start_time:
        raise HTTPException(status_code=422, detail="Bitiş saati başlangıçtan sonra olmalı")
    new_slot = TimeSlot(
        teacher_id=slot_data.teacher_id,
        date=slot_data.date,
        start_time=slot_data.start_time,
        end_time=slot_data.end_time,
        is_available=slot_data.is_available
    )
    
    db.add(new_slot)
    await db.commit()
    await db.refresh(new_slot)
    
    return success_response({
        "id": str(new_slot.id),
        "teacher_id": str(new_slot.teacher_id),
        "date": new_slot.date.isoformat(),
        "start_time": new_slot.start_time.strftime("%H:%M"),
        "end_time": new_slot.end_time.strftime("%H:%M"),
        "is_available": new_slot.is_available
    }, "Saat dilimi oluşturuldu")


@router.delete("/slots/{slot_id}")
async def delete_time_slot(
    slot_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("appointments.write"))
):
    """Delete a time slot"""
    from app.infrastructure.models.models import TimeSlot
    
    result = await db.execute(
        select(TimeSlot).where(TimeSlot.id == slot_id)
    )
    slot = result.scalar_one_or_none()
    
    if not slot:
        raise HTTPException(status_code=404, detail="Saat dilimi bulunamadı")
    
    # Verify teacher owns this slot
    from app.infrastructure.repositories.base import BaseRepository
    from app.infrastructure.models.models import User as UserModel
    await BaseRepository(db, tenant).get_by_id(slot.teacher_id, UserModel)
    if not tenant.is_super_admin and slot.teacher_id != tenant.user_id:
        raise HTTPException(status_code=403, detail="Bu saat dilimini silme yetkiniz yok")
    
    await db.delete(slot)
    await db.commit()
    
    return success_response({"message": "Saat dilimi silindi"})
