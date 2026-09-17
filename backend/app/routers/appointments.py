"""
Appointments Module API
Handles teacher-parent appointment scheduling and management
"""
from datetime import datetime, date, time, timedelta
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_tenant_context
from app.core.permissions import PermissionChecker
from app.core.responses import success_response
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


# ==================== Teacher Endpoints ====================

@router.get("/my-appointments")
async def get_my_appointments(
    status: Optional[str] = Query(None),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("appointments.read"))
):
    """Get appointments for the current user (teacher or parent)"""
    from app.infrastructure.models.models import Appointment, Student, User as UserModel
    
    query = select(Appointment)
    
    # Filter based on user role
    if tenant.role == "TEACHER":
        query = query.where(Appointment.teacher_id == tenant.id)
    elif tenant.role == "PARENT":
        # Get parent's student IDs
        from app.infrastructure.models.models import StudentParent
        parent_result = await db.execute(
            select(StudentParent.student_id).where(StudentParent.parent_id == tenant.id)
        )
        student_ids = [r[0] for r in parent_result]
        query = query.where(Appointment.student_id.in_(student_ids))
    else:
        raise HTTPException(status_code=403, detail="Bu işlem için yetkiniz yok")
    
    # Apply filters
    conditions = []
    if status:
        conditions.append(Appointment.status == status.upper())
    if start_date:
        conditions.append(Appointment.slot_datetime >= datetime.combine(start_date, time.min))
    if end_date:
        conditions.append(Appointment.slot_datetime <= datetime.combine(end_date, time.max))
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(Appointment.slot_datetime)
    
    result = await db.execute(query)
    appointments = result.scalars().all()
    
    enriched_appointments = []
    for appointment in appointments:
        # Get teacher name
        teacher_result = await db.execute(
            select(UserModel).where(UserModel.id == appointment.teacher_id)
        )
        teacher = teacher_result.scalar_one_or_none()
        
        # Get student name
        student_result = await db.execute(
            select(Student).where(Student.id == appointment.student_id)
        )
        student = student_result.scalar_one_or_none()
        
        # Get parent name
        parent_result = await db.execute(
            select(UserModel).where(UserModel.id == appointment.parent_id)
        )
        parent = parent_result.scalar_one_or_none()
        
        enriched_appointments.append({
            "id": str(appointment.id),
            "teacher_id": str(appointment.teacher_id),
            "teacher_name": f"{teacher.first_name} {teacher.last_name}" if teacher else None,
            "student_id": str(appointment.student_id),
            "student_name": f"{student.first_name} {student.last_name}" if student else None,
            "parent_id": str(appointment.parent_id),
            "parent_name": f"{parent.first_name} {parent.last_name}" if parent else None,
            "slot_datetime": appointment.slot_datetime.isoformat(),
            "duration_minutes": appointment.duration_minutes,
            "status": appointment.status,
            "parent_note": appointment.parent_note,
            "teacher_note": appointment.teacher_note,
            "created_at": appointment.created_at.isoformat(),
            "updated_at": appointment.updated_at.isoformat()
        })
    
    return success_response(enriched_appointments)


@router.get("/teacher-slots/{teacher_id}")
async def get_teacher_available_slots(
    teacher_id: UUID,
    date: date = Query(..., description="Date to get slots for"),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("appointments.read"))
):
    """Get available time slots for a teacher on a specific date"""
    from app.infrastructure.models.models import Appointment, TimeSlot
    
    # Get existing appointments for this teacher on this date
    start_of_day = datetime.combine(date, time.min)
    end_of_day = datetime.combine(date, time.max)
    
    appointment_result = await db.execute(
        select(Appointment).where(
            and_(
                Appointment.teacher_id == teacher_id,
                Appointment.slot_datetime >= start_of_day,
                Appointment.slot_datetime <= end_of_day,
                Appointment.status.in_(["PENDING", "APPROVED"])
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
        slot_start = datetime.combine(date, slot.start_time)
        slot_end = datetime.combine(date, slot.end_time)
        
        # Check if this slot conflicts with any appointment
        is_booked = False
        for appointment in appointments:
            appointment_start = appointment.slot_datetime
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
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("appointments.write"))
):
    """Update appointment status (teacher action)"""
    from app.infrastructure.models.models import Appointment
    
    result = await db.execute(
        select(Appointment).where(Appointment.id == appointment_id)
    )
    appointment = result.scalar_one_or_none()
    
    if not appointment:
        raise HTTPException(status_code=404, detail="Randevu bulunamadı")
    
    # Verify teacher owns this appointment
    if appointment.teacher_id != tenant.id:
        raise HTTPException(status_code=403, detail="Bu randevuyu güncelleme yetkiniz yok")
    
    appointment.status = update_data.status.upper()
    appointment.teacher_note = update_data.teacher_note
    appointment.updated_at = datetime.utcnow()
    
    await db.commit()
    
    return success_response({
        "id": str(appointment.id),
        "status": appointment.status,
        "updated_at": appointment.updated_at.isoformat()
    }, "Randevu durumu güncellendi")


# ==================== Parent Endpoints ====================

@router.post("/request")
async def request_appointment(
    appointment_data: AppointmentCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("appointments.write"))
):
    """Request an appointment with a teacher"""
    from app.infrastructure.models.models import Appointment, StudentParent
    
    # Verify parent has access to this student
    parent_result = await db.execute(
        select(StudentParent).where(
            and_(
                StudentParent.parent_id == tenant.id,
                StudentParent.student_id == appointment_data.student_id
            )
        )
    )
    if not parent_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Bu öğrenciye erişiminiz yok")
    
    # Check if slot is available
    slot_start = appointment_data.slot_datetime
    slot_end = slot_start + timedelta(minutes=appointment_data.duration_minutes)
    
    from app.infrastructure.models.models import Appointment as AppointmentModel
    conflict_result = await db.execute(
        select(AppointmentModel).where(
            and_(
                AppointmentModel.teacher_id == appointment_data.teacher_id,
                AppointmentModel.status.in_(["PENDING", "APPROVED"]),
                AppointmentModel.slot_datetime < slot_end,
                (AppointmentModel.slot_datetime + timedelta(minutes=AppointmentModel.duration_minutes)) > slot_start
            )
        )
    )
    
    if conflict_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Bu saat dolu, lütfen başka bir saat seçin")
    
    # Create appointment
    new_appointment = Appointment(
        teacher_id=appointment_data.teacher_id,
        student_id=appointment_data.student_id,
        parent_id=tenant.id,
        slot_datetime=appointment_data.slot_datetime,
        duration_minutes=appointment_data.duration_minutes,
        parent_note=appointment_data.parent_note,
        status="PENDING"
    )
    
    db.add(new_appointment)
    await db.commit()
    await db.refresh(new_appointment)
    
    return success_response({
        "id": str(new_appointment.id),
        "teacher_id": str(new_appointment.teacher_id),
        "student_id": str(new_appointment.student_id),
        "slot_datetime": new_appointment.slot_datetime.isoformat(),
        "status": new_appointment.status,
        "created_at": new_appointment.created_at.isoformat()
    }, "Randevu talebi oluşturuldu")


# ==================== Time Slot Management (Teacher) ====================

@router.post("/slots")
async def create_time_slot(
    slot_data: TimeSlotCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("appointments.write"))
):
    """Create available time slot for appointments"""
    from app.infrastructure.models.models import TimeSlot
    
    # Verify teacher is creating slot for themselves
    if slot_data.teacher_id != tenant.id:
        raise HTTPException(status_code=403, detail="Sadece kendi saatlerinizi oluşturabilirsiniz")
    
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
    db: AsyncSession = Depends(get_db),
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
    if slot.teacher_id != tenant.id:
        raise HTTPException(status_code=403, detail="Bu saat dilimini silme yetkiniz yok")
    
    await db.delete(slot)
    await db.commit()
    
    return success_response({"message": "Saat dilimi silindi"})
