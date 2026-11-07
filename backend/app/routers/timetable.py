"""
Timetable/Schedule Builder Module API
Handles timetable slots, classroom assignments, and conflict detection
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.infrastructure.models.models import ClassRoom as Class
from app.core.responses import success_response
from app.core.permissions import PermissionChecker
from app.core.tenant import TenantContext
from app.domain.entities import (
    TimetableSlot, ClassroomAssignment, Timetable, User
)

router = APIRouter(prefix="/api/timetable", tags=["Timetable"])


# ==================== Schemas ====================

class TimetableSlotCreate(BaseModel):
    day: str = Field(..., description="MONDAY, TUESDAY, etc.")
    start_time: str = Field(..., description="HH:MM format")
    end_time: str = Field(..., description="HH:MM format")
    is_break: bool = Field(default=False)

class TimetableSlotResponse(BaseModel):
    id: UUID
    day: str
    start_time: str
    end_time: str
    is_break: bool
    created_at: datetime
    updated_at: datetime

class ClassroomAssignmentCreate(BaseModel):
    class_id: UUID
    teacher_id: Optional[UUID] = None
    subject_id: Optional[UUID] = None
    room_number: Optional[str] = None
    capacity: int = Field(default=30, ge=1)

class ClassroomAssignmentResponse(BaseModel):
    id: UUID
    class_id: UUID
    class_name: Optional[str]
    teacher_id: Optional[UUID]
    teacher_name: Optional[str]
    subject_id: Optional[UUID]
    room_number: Optional[str]
    capacity: int
    created_at: datetime
    updated_at: datetime

class TimetableCreate(BaseModel):
    class_id: UUID
    slot_id: UUID
    classroom_assignment_id: Optional[UUID] = None
    academic_year: str = Field(..., description="e.g., 2024-2025")
    semester: str = Field(default="FALL", description="FALL, SPRING, SUMMER")

class TimetableResponse(BaseModel):
    id: UUID
    class_id: UUID
    class_name: Optional[str]
    slot_id: UUID
    slot_day: Optional[str]
    slot_start_time: Optional[str]
    slot_end_time: Optional[str]
    classroom_assignment_id: Optional[UUID]
    teacher_name: Optional[str]
    subject_id: Optional[UUID]
    room_number: Optional[str]
    academic_year: str
    semester: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

class ConflictCheckResponse(BaseModel):
    has_conflicts: bool
    conflicts: List[dict]
    message: str

class BulkTimetableSave(BaseModel):
    entries: List[TimetableCreate]
    academic_year: str
    semester: str = "FALL"


# ==================== Timetable Slots Endpoints ====================

@router.get("/slots")
async def get_timetable_slots(
    day: Optional[str] = Query(None, description="Filter by day"),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("timetable.read"))
):
    """Get all timetable slots"""
    query = select(TimetableSlot)
    
    if day:
        query = query.where(TimetableSlot.day == day.upper())
    
    query = query.order_by(TimetableSlot.day, TimetableSlot.start_time)
    
    result = await db.execute(query)
    slots = result.scalars().all()
    
    return success_response([
        {
            "id": str(slot.id),
            "day": slot.day,
            "start_time": slot.start_time.strftime("%H:%M"),
            "end_time": slot.end_time.strftime("%H:%M"),
            "is_break": slot.is_break,
            "created_at": slot.created_at.isoformat(),
            "updated_at": slot.updated_at.isoformat()
        }
        for slot in slots
    ])


@router.post("/slots")
async def create_timetable_slot(
    slot: TimetableSlotCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("timetable.write"))
):
    """Create a new timetable slot"""
    # Validate time format
    try:
        start_time = datetime.strptime(slot.start_time, "%H:%M").time()
        end_time = datetime.strptime(slot.end_time, "%H:%M").time()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid time format. Use HH:MM")
    
    if end_time <= start_time:
        raise HTTPException(status_code=400, detail="End time must be after start time")
    
    new_slot = TimetableSlot(
        day=slot.day.upper(),
        start_time=start_time,
        end_time=end_time,
        is_break=slot.is_break
    )
    db.add(new_slot)
    await db.commit()
    await db.refresh(new_slot)
    
    return success_response({
        "id": str(new_slot.id),
        "day": new_slot.day,
        "start_time": new_slot.start_time.strftime("%H:%M"),
        "end_time": new_slot.end_time.strftime("%H:%M"),
        "is_break": new_slot.is_break,
        "created_at": new_slot.created_at.isoformat(),
        "updated_at": new_slot.updated_at.isoformat()
    })


@router.delete("/slots/{slot_id}")
async def delete_timetable_slot(
    slot_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("timetable.write"))
):
    """Delete a timetable slot"""
    result = await db.execute(
        select(TimetableSlot).where(TimetableSlot.id == slot_id)
    )
    slot = result.scalar_one_or_none()
    
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    
    await db.delete(slot)
    await db.commit()
    
    return success_response({"message": "Slot deleted successfully"})


@router.put("/slots/{slot_id}")
async def update_timetable_slot(
    slot_id: UUID,
    slot: TimetableSlotCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("timetable.write"))
):
    """Update a timetable slot"""
    result = await db.execute(
        select(TimetableSlot).where(TimetableSlot.id == slot_id)
    )
    existing_slot = result.scalar_one_or_none()
    
    if not existing_slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    
    # Validate time format
    try:
        start_time = datetime.strptime(slot.start_time, "%H:%M").time()
        end_time = datetime.strptime(slot.end_time, "%H:%M").time()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid time format. Use HH:MM")
    
    if end_time <= start_time:
        raise HTTPException(status_code=400, detail="End time must be after start time")
    
    existing_slot.day = slot.day.upper()
    existing_slot.start_time = start_time
    existing_slot.end_time = end_time
    existing_slot.is_break = slot.is_break
    
    await db.commit()
    
    return success_response({
        "id": str(existing_slot.id),
        "day": existing_slot.day,
        "start_time": existing_slot.start_time.strftime("%H:%M"),
        "end_time": existing_slot.end_time.strftime("%H:%M"),
        "is_break": existing_slot.is_break,
        "updated_at": existing_slot.updated_at.isoformat()
    }, "Slot güncellendi")


# ==================== Classroom Assignments Endpoints ====================

@router.get("/classroom-assignments")
async def get_classroom_assignments(
    class_id: Optional[UUID] = Query(None),
    teacher_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("timetable.read"))
):
    """Get classroom assignments"""
    query = select(ClassroomAssignment)
    
    if class_id:
        query = query.where(ClassroomAssignment.class_id == class_id)
    if teacher_id:
        query = query.where(ClassroomAssignment.teacher_id == teacher_id)
    
    result = await db.execute(query)
    assignments = result.scalars().all()
    
    enriched_assignments = []
    for assignment in assignments:
        # Get class name
        class_name = None
        if assignment.class_id:
            class_result = await db.execute(
                select(Class).where(Class.id == assignment.class_id)
            )
            cls = class_result.scalar_one_or_none()
            if cls:
                class_name = cls.name
        
        # Get teacher name
        teacher_name = None
        if assignment.teacher_id:
            teacher_result = await db.execute(
                select(User).where(User.id == assignment.teacher_id)
            )
            teacher = teacher_result.scalar_one_or_none()
            if teacher:
                teacher_name = f"{teacher.first_name} {teacher.last_name}"
        
        enriched_assignments.append({
            "id": str(assignment.id),
            "class_id": str(assignment.class_id),
            "class_name": class_name,
            "teacher_id": str(assignment.teacher_id) if assignment.teacher_id else None,
            "teacher_name": teacher_name,
            "subject_id": str(assignment.subject_id) if assignment.subject_id else None,
            "room_number": assignment.room_number,
            "capacity": assignment.capacity,
            "created_at": assignment.created_at.isoformat(),
            "updated_at": assignment.updated_at.isoformat()
        })
    
    return success_response(enriched_assignments)


@router.post("/classroom-assignments")
async def create_classroom_assignment(
    assignment: ClassroomAssignmentCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("timetable.write"))
):
    """Create a new classroom assignment"""
    new_assignment = ClassroomAssignment(
        class_id=assignment.class_id,
        teacher_id=assignment.teacher_id,
        subject_id=assignment.subject_id,
        room_number=assignment.room_number,
        capacity=assignment.capacity
    )
    db.add(new_assignment)
    await db.commit()
    await db.refresh(new_assignment)
    
    return success_response({
        "id": str(new_assignment.id),
        "class_id": str(new_assignment.class_id),
        "teacher_id": str(new_assignment.teacher_id) if new_assignment.teacher_id else None,
        "subject_id": str(new_assignment.subject_id) if new_assignment.subject_id else None,
        "room_number": new_assignment.room_number,
        "capacity": new_assignment.capacity,
        "created_at": new_assignment.created_at.isoformat(),
        "updated_at": new_assignment.updated_at.isoformat()
    })


# ==================== Timetable Endpoints ====================

@router.get("/classes/{class_id}")
async def get_class_timetable(
    class_id: UUID,
    academic_year: str = Query(..., description="e.g., 2024-2025"),
    semester: str = Query("FALL", description="FALL, SPRING, SUMMER"),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("timetable.read"))
):
    """Get timetable for a specific class"""
    query = select(Timetable).where(
        and_(
            Timetable.class_id == class_id,
            Timetable.academic_year == academic_year,
            Timetable.semester == semester,
            Timetable.is_active == True
        )
    )
    
    result = await db.execute(query)
    timetables = result.scalars().all()
    
    enriched_timetables = []
    for timetable in timetables:
        # Get slot details
        slot_result = await db.execute(
            select(TimetableSlot).where(TimetableSlot.id == timetable.slot_id)
        )
        slot = slot_result.scalar_one_or_none()
        
        # Get classroom assignment details
        teacher_name = None
        room_number = None
        if timetable.classroom_assignment_id:
            assignment_result = await db.execute(
                select(ClassroomAssignment).where(
                    ClassroomAssignment.id == timetable.classroom_assignment_id
                )
            )
            assignment = assignment_result.scalar_one_or_none()
            if assignment:
                room_number = assignment.room_number
                if assignment.teacher_id:
                    teacher_result = await db.execute(
                        select(User).where(User.id == assignment.teacher_id)
                    )
                    teacher = teacher_result.scalar_one_or_none()
                    if teacher:
                        teacher_name = f"{teacher.first_name} {teacher.last_name}"
        
        # Get class name
        class_result = await db.execute(
            select(Class).where(Class.id == timetable.class_id)
        )
        cls = class_result.scalar_one_or_none()
        class_name = cls.name if cls else None
        
        enriched_timetables.append({
            "id": str(timetable.id),
            "class_id": str(timetable.class_id),
            "class_name": class_name,
            "slot_id": str(timetable.slot_id),
            "slot_day": slot.day if slot else None,
            "slot_start_time": slot.start_time.strftime("%H:%M") if slot else None,
            "slot_end_time": slot.end_time.strftime("%H:%M") if slot else None,
            "classroom_assignment_id": str(timetable.classroom_assignment_id) if timetable.classroom_assignment_id else None,
            "teacher_name": teacher_name,
            "subject_id": str(timetable.classroom_assignment_id) if timetable.classroom_assignment_id else None,
            "room_number": room_number,
            "academic_year": timetable.academic_year,
            "semester": timetable.semester,
            "is_active": timetable.is_active,
            "created_at": timetable.created_at.isoformat(),
            "updated_at": timetable.updated_at.isoformat()
        })
    
    return success_response(enriched_timetables)


@router.get("/teachers/{teacher_id}")
async def get_teacher_timetable(
    teacher_id: UUID,
    academic_year: str = Query(..., description="e.g., 2024-2025"),
    semester: str = Query("FALL", description="FALL, SPRING, SUMMER"),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("timetable.read"))
):
    """Get timetable for a specific teacher"""
    # Get classroom assignments for this teacher
    assignment_result = await db.execute(
        select(ClassroomAssignment).where(ClassroomAssignment.teacher_id == teacher_id)
    )
    assignments = assignment_result.scalars().all()
    
    assignment_ids = [a.id for a in assignments]
    
    if not assignment_ids:
        return success_response([])
    
    # Get timetables for these assignments
    query = select(Timetable).where(
        and_(
            Timetable.classroom_assignment_id.in_(assignment_ids),
            Timetable.academic_year == academic_year,
            Timetable.semester == semester,
            Timetable.is_active == True
        )
    )
    
    result = await db.execute(query)
    timetables = result.scalars().all()
    
    enriched_timetables = []
    for timetable in timetables:
        # Get slot details
        slot_result = await db.execute(
            select(TimetableSlot).where(TimetableSlot.id == timetable.slot_id)
        )
        slot = slot_result.scalar_one_or_none()
        
        # Get class name
        class_result = await db.execute(
            select(Class).where(Class.id == timetable.class_id)
        )
        cls = class_result.scalar_one_or_none()
        class_name = cls.name if cls else None
        
        enriched_timetables.append({
            "id": str(timetable.id),
            "class_id": str(timetable.class_id),
            "class_name": class_name,
            "slot_id": str(timetable.slot_id),
            "slot_day": slot.day if slot else None,
            "slot_start_time": slot.start_time.strftime("%H:%M") if slot else None,
            "slot_end_time": slot.end_time.strftime("%H:%M") if slot else None,
            "academic_year": timetable.academic_year,
            "semester": timetable.semester,
            "is_active": timetable.is_active
        })
    
    return success_response(enriched_timetables)


@router.post("/bulk-save")
async def bulk_save_timetable(
    request: BulkTimetableSave,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("timetable.write"))
):
    """Bulk save timetable entries with conflict checking"""
    conflicts = []
    
    for entry in request.entries:
        # Check for conflicts
        conflict = await check_conflict(
            db, entry.class_id, entry.slot_id, 
            entry.classroom_assignment_id, 
            request.academic_year, request.semester
        )
        
        if conflict:
            conflicts.append({
                "entry": entry.dict(),
                "conflict": conflict
            })
            continue
        
        # Create or update timetable entry
        existing_result = await db.execute(
            select(Timetable).where(
                and_(
                    Timetable.class_id == entry.class_id,
                    Timetable.slot_id == entry.slot_id,
                    Timetable.academic_year == request.academic_year,
                    Timetable.semester == request.semester
                )
            )
        )
        existing = existing_result.scalar_one_or_none()
        
        if existing:
            existing.classroom_assignment_id = entry.classroom_assignment_id
            existing.is_active = True
        else:
            new_timetable = Timetable(
                class_id=entry.class_id,
                slot_id=entry.slot_id,
                classroom_assignment_id=entry.classroom_assignment_id,
                academic_year=request.academic_year,
                semester=request.semester,
                is_active=True
            )
            db.add(new_timetable)
    
    await db.commit()
    
    if conflicts:
        return success_response({
            "has_conflicts": True,
            "conflicts": conflicts,
            "message": f"{len(conflicts)} conflicts detected. Some entries were not saved."
        })
    
    return success_response({
        "has_conflicts": False,
        "conflicts": [],
        "message": "All entries saved successfully."
    })


@router.post("/check-conflict")
async def check_timetable_conflict(
    class_id: UUID,
    slot_id: UUID,
    classroom_assignment_id: Optional[UUID] = None,
    academic_year: str = Query(...),
    semester: str = Query("FALL"),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("timetable.read"))
):
    """Check for timetable conflicts"""
    conflict = await check_conflict(
        db, class_id, slot_id, classroom_assignment_id, academic_year, semester
    )
    
    if conflict:
        return success_response({
            "has_conflicts": True,
            "conflicts": [conflict],
            "message": "Conflict detected"
        })
    
    return success_response({
        "has_conflicts": False,
        "conflicts": [],
        "message": "No conflicts detected"
    })


@router.delete("/{timetable_id}")
async def delete_timetable_entry(
    timetable_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("timetable.write"))
):
    """Delete a timetable entry"""
    result = await db.execute(
        select(Timetable).where(Timetable.id == timetable_id)
    )
    timetable = result.scalar_one_or_none()
    
    if not timetable:
        raise HTTPException(status_code=404, detail="Timetable entry not found")
    
    await db.delete(timetable)
    await db.commit()
    
    return success_response({"message": "Timetable entry deleted successfully"})


# ==================== Helper Functions ====================

async def check_conflict(
    db: AsyncSession,
    class_id: UUID,
    slot_id: UUID,
    classroom_assignment_id: Optional[UUID],
    academic_year: str,
    semester: str
) -> Optional[dict]:
    """Check for timetable conflicts"""
    conflicts = []
    
    # Check if class already has a class at this slot
    class_conflict = await db.execute(
        select(Timetable).where(
            and_(
                Timetable.class_id == class_id,
                Timetable.slot_id == slot_id,
                Timetable.academic_year == academic_year,
                Timetable.semester == semester,
                Timetable.is_active == True
            )
        )
    )
    if class_conflict.scalar_one_or_none():
        conflicts.append({
            "type": "CLASS_CONFLICT",
            "message": "Class already has a lesson at this time slot"
        })
    
    # Check if teacher is already assigned at this slot
    if classroom_assignment_id:
        assignment_result = await db.execute(
            select(ClassroomAssignment).where(
                ClassroomAssignment.id == classroom_assignment_id
            )
        )
        assignment = assignment_result.scalar_one_or_none()
        
        if assignment and assignment.teacher_id:
            teacher_conflict = await db.execute(
                select(Timetable).where(
                    and_(
                        Timetable.classroom_assignment_id.in_(
                            select(ClassroomAssignment.id).where(
                                ClassroomAssignment.teacher_id == assignment.teacher_id
                            )
                        ),
                        Timetable.slot_id == slot_id,
                        Timetable.academic_year == academic_year,
                        Timetable.semester == semester,
                        Timetable.is_active == True
                    )
                )
            )
            if teacher_conflict.scalar_one_or_none():
                conflicts.append({
                    "type": "TEACHER_CONFLICT",
                    "message": "Teacher is already assigned at this time slot"
                })
    
    return conflicts[0] if conflicts else None
