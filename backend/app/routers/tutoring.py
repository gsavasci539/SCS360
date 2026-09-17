"""
Etüt & Birebir Ders Yönetimi Module API
Handles tutoring sessions, requests, and teacher availability
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
from app.domain.entities import Student, User

router = APIRouter(prefix="/api/tutoring", tags=["Tutoring"])


# ==================== Schemas ====================

class TutoringSessionCreate(BaseModel):
    teacher_id: UUID
    student_id: UUID
    subject: Optional[str] = None
    session_date: date = Field(..., description="Session date")
    start_time: time = Field(..., description="Start time")
    end_time: time = Field(..., description="End time")
    location: Optional[str] = None
    notes: Optional[str] = None

class TutoringRequestCreate(BaseModel):
    student_id: UUID
    teacher_id: Optional[UUID] = None
    subject: Optional[str] = None
    requested_date: date = Field(..., description="Requested date")
    preferred_time_start: Optional[time] = None
    preferred_time_end: Optional[time] = None
    reason: Optional[str] = None

class TeacherAvailabilityCreate(BaseModel):
    teacher_id: UUID
    day_of_week: int = Field(..., ge=0, le=6, description="0=Monday, 6=Sunday")
    start_time: time = Field(..., description="Available start time")
    end_time: time = Field(..., description="Available end time")
    max_students: int = Field(default=1, ge=1)

class SessionAttendanceUpdate(BaseModel):
    attendance_status: str = Field(..., description="PRESENT, ABSENT, LATE")
    progress_score: Optional[int] = Field(None, ge=0, le=100)
    notes: Optional[str] = None


# ==================== Tutoring Sessions Endpoints ====================

@router.get("/sessions")
async def get_tutoring_sessions(
    teacher_id: Optional[UUID] = Query(None),
    student_id: Optional[UUID] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("tutoring.read"))
):
    """Get tutoring sessions with filtering"""
    from app.domain.entities.tutoring import TutoringSession
    
    query = select(TutoringSession)
    
    conditions = []
    if teacher_id:
        conditions.append(TutoringSession.teacher_id == teacher_id)
    if student_id:
        conditions.append(TutoringSession.student_id == student_id)
    if start_date:
        conditions.append(TutoringSession.session_date >= start_date)
    if end_date:
        conditions.append(TutoringSession.session_date <= end_date)
    if status:
        conditions.append(TutoringSession.status == status.upper())
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(TutoringSession.session_date.desc(), TutoringSession.start_time).limit(limit).offset(offset)
    
    result = await db.execute(query)
    sessions = result.scalars().all()
    
    enriched_sessions = []
    for session in sessions:
        # Get teacher name
        teacher_name = None
        if session.teacher_id:
            teacher_result = await db.execute(
                select(User).where(User.id == session.teacher_id)
            )
            teacher = teacher_result.scalar_one_or_none()
            if teacher:
                teacher_name = f"{teacher.first_name} {teacher.last_name}"
        
        # Get student name
        student_name = None
        if session.student_id:
            student_result = await db.execute(
                select(Student).where(Student.id == session.student_id)
            )
            student = student_result.scalar_one_or_none()
            if student:
                student_name = f"{student.first_name} {student.last_name}"
        
        enriched_sessions.append({
            "id": str(session.id),
            "teacher_id": str(session.teacher_id),
            "teacher_name": teacher_name,
            "student_id": str(session.student_id),
            "student_name": student_name,
            "subject": session.subject,
            "session_date": session.session_date.isoformat(),
            "start_time": session.start_time.strftime("%H:%M"),
            "end_time": session.end_time.strftime("%H:%M"),
            "location": session.location,
            "status": session.status,
            "notes": session.notes,
            "attendance_status": session.attendance_status,
            "progress_score": session.progress_score,
            "created_at": session.created_at.isoformat()
        })
    
    return success_response(enriched_sessions)


@router.post("/sessions")
async def create_tutoring_session(
    session: TutoringSessionCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("tutoring.write"))
):
    """Create a new tutoring session"""
    from app.domain.entities.tutoring import TutoringSession
    
    new_session = TutoringSession(
        teacher_id=session.teacher_id,
        student_id=session.student_id,
        subject=session.subject,
        session_date=session.session_date,
        start_time=session.start_time,
        end_time=session.end_time,
        location=session.location,
        notes=session.notes,
        status="SCHEDULED"
    )
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)
    
    return success_response({
        "id": str(new_session.id),
        "session_date": new_session.session_date.isoformat(),
        "status": new_session.status,
        "created_at": new_session.created_at.isoformat()
    })


@router.put("/sessions/{session_id}")
async def update_tutoring_session(
    session_id: UUID,
    session: TutoringSessionCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("tutoring.write"))
):
    """Update a tutoring session"""
    from app.domain.entities.tutoring import TutoringSession
    
    result = await db.execute(
        select(TutoringSession).where(TutoringSession.id == session_id)
    )
    existing_session = result.scalar_one_or_none()
    
    if not existing_session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    existing_session.teacher_id = session.teacher_id
    existing_session.student_id = session.student_id
    existing_session.subject = session.subject
    existing_session.session_date = session.session_date
    existing_session.start_time = session.start_time
    existing_session.end_time = session.end_time
    existing_session.location = session.location
    existing_session.notes = session.notes
    
    await db.commit()
    
    return success_response({
        "id": str(existing_session.id),
        "updated_at": existing_session.updated_at.isoformat()
    })


@router.post("/sessions/{session_id}/attendance")
async def mark_session_attendance(
    session_id: UUID,
    attendance: SessionAttendanceUpdate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("tutoring.write"))
):
    """Mark attendance and progress for a tutoring session"""
    from app.domain.entities.tutoring import TutoringSession
    
    result = await db.execute(
        select(TutoringSession).where(TutoringSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session.attendance_status = attendance.attendance_status.upper()
    session.progress_score = attendance.progress_score
    session.notes = attendance.notes
    session.status = "COMPLETED"
    
    await db.commit()
    
    return success_response({
        "id": str(session.id),
        "attendance_status": session.attendance_status,
        "progress_score": session.progress_score,
        "status": session.status
    })


# ==================== Tutoring Requests Endpoints ====================

@router.get("/requests")
async def get_tutoring_requests(
    student_id: Optional[UUID] = Query(None),
    teacher_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("tutoring.read"))
):
    """Get tutoring requests with filtering"""
    from app.domain.entities.tutoring import TutoringRequest
    
    query = select(TutoringRequest)
    
    conditions = []
    if student_id:
        conditions.append(TutoringRequest.student_id == student_id)
    if teacher_id:
        conditions.append(TutoringRequest.teacher_id == teacher_id)
    if status:
        conditions.append(TutoringRequest.status == status.upper())
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(TutoringRequest.created_at.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    requests = result.scalars().all()
    
    enriched_requests = []
    for req in requests:
        # Get student name
        student_name = None
        if req.student_id:
            student_result = await db.execute(
                select(Student).where(Student.id == req.student_id)
            )
            student = student_result.scalar_one_or_none()
            if student:
                student_name = f"{student.first_name} {student.last_name}"
        
        # Get teacher name
        teacher_name = None
        if req.teacher_id:
            teacher_result = await db.execute(
                select(User).where(User.id == req.teacher_id)
            )
            teacher = teacher_result.scalar_one_or_none()
            if teacher:
                teacher_name = f"{teacher.first_name} {teacher.last_name}"
        
        # Get approved by name
        approved_by_name = None
        if req.approved_by:
            user_result = await db.execute(
                select(User).where(User.id == req.approved_by)
            )
            user = user_result.scalar_one_or_none()
            if user:
                approved_by_name = f"{user.first_name} {user.last_name}"
        
        enriched_requests.append({
            "id": str(req.id),
            "student_id": str(req.student_id),
            "student_name": student_name,
            "teacher_id": str(req.teacher_id) if req.teacher_id else None,
            "teacher_name": teacher_name,
            "subject": req.subject,
            "requested_date": req.requested_date.isoformat(),
            "preferred_time_start": req.preferred_time_start.strftime("%H:%M") if req.preferred_time_start else None,
            "preferred_time_end": req.preferred_time_end.strftime("%H:%M") if req.preferred_time_end else None,
            "reason": req.reason,
            "status": req.status,
            "approved_by": str(req.approved_by) if req.approved_by else None,
            "approved_by_name": approved_by_name,
            "approved_at": req.approved_at.isoformat() if req.approved_at else None,
            "rejection_reason": req.rejection_reason,
            "created_at": req.created_at.isoformat()
        })
    
    return success_response(enriched_requests)


@router.post("/requests")
async def create_tutoring_request(
    request: TutoringRequestCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("tutoring.write"))
):
    """Create a new tutoring request"""
    from app.domain.entities.tutoring import TutoringRequest
    
    new_request = TutoringRequest(
        student_id=request.student_id,
        teacher_id=request.teacher_id,
        subject=request.subject,
        requested_date=request.requested_date,
        preferred_time_start=request.preferred_time_start,
        preferred_time_end=request.preferred_time_end,
        reason=request.reason,
        status="PENDING"
    )
    db.add(new_request)
    await db.commit()
    await db.refresh(new_request)
    
    return success_response({
        "id": str(new_request.id),
        "requested_date": new_request.requested_date.isoformat(),
        "status": new_request.status,
        "created_at": new_request.created_at.isoformat()
    })


@router.post("/requests/{request_id}/approve")
async def approve_tutoring_request(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("tutoring.write"))
):
    """Approve a tutoring request"""
    from app.domain.entities.tutoring import TutoringRequest
    
    result = await db.execute(
        select(TutoringRequest).where(TutoringRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    
    req.status = "APPROVED"
    req.approved_by = None  # Will be set from current user context
    req.approved_at = datetime.utcnow()
    
    await db.commit()
    
    return success_response({
        "id": str(req.id),
        "status": "APPROVED",
        "approved_at": req.approved_at.isoformat()
    })


@router.post("/requests/{request_id}/reject")
async def reject_tutoring_request(
    request_id: UUID,
    rejection_reason: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("tutoring.write"))
):
    """Reject a tutoring request"""
    from app.domain.entities.tutoring import TutoringRequest
    
    result = await db.execute(
        select(TutoringRequest).where(TutoringRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    
    req.status = "REJECTED"
    req.rejection_reason = rejection_reason
    
    await db.commit()
    
    return success_response({
        "id": str(req.id),
        "status": "REJECTED",
        "rejection_reason": rejection_reason
    })


# ==================== Teacher Availability Endpoints ====================

@router.get("/availability")
async def get_teacher_availability(
    teacher_id: Optional[UUID] = Query(None),
    day_of_week: Optional[int] = Query(None, ge=0, le=6),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("tutoring.read"))
):
    """Get teacher availability"""
    from app.domain.entities.tutoring import TeacherAvailability
    
    query = select(TeacherAvailability)
    
    conditions = []
    if teacher_id:
        conditions.append(TeacherAvailability.teacher_id == teacher_id)
    if day_of_week is not None:
        conditions.append(TeacherAvailability.day_of_week == day_of_week)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(TeacherAvailability.day_of_week, TeacherAvailability.start_time)
    
    result = await db.execute(query)
    availabilities = result.scalars().all()
    
    enriched_availabilities = []
    for avail in availabilities:
        # Get teacher name
        teacher_name = None
        if avail.teacher_id:
            teacher_result = await db.execute(
                select(User).where(User.id == avail.teacher_id)
            )
            teacher = teacher_result.scalar_one_or_none()
            if teacher:
                teacher_name = f"{teacher.first_name} {teacher.last_name}"
        
        enriched_availabilities.append({
            "id": str(avail.id),
            "teacher_id": str(avail.teacher_id),
            "teacher_name": teacher_name,
            "day_of_week": avail.day_of_week,
            "start_time": avail.start_time.strftime("%H:%M"),
            "end_time": avail.end_time.strftime("%H:%M"),
            "is_available": avail.is_available,
            "max_students": avail.max_students,
            "created_at": avail.created_at.isoformat()
        })
    
    return success_response(enriched_availabilities)


@router.post("/availability")
async def create_teacher_availability(
    availability: TeacherAvailabilityCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("tutoring.write"))
):
    """Create teacher availability"""
    from app.domain.entities.tutoring import TeacherAvailability
    
    new_availability = TeacherAvailability(
        teacher_id=availability.teacher_id,
        day_of_week=availability.day_of_week,
        start_time=availability.start_time,
        end_time=availability.end_time,
        is_available=True,
        max_students=availability.max_students
    )
    db.add(new_availability)
    await db.commit()
    await db.refresh(new_availability)
    
    return success_response({
        "id": str(new_availability.id),
        "day_of_week": new_availability.day_of_week,
        "start_time": new_availability.start_time.strftime("%H:%M"),
        "end_time": new_availability.end_time.strftime("%H:%M"),
        "created_at": new_availability.created_at.isoformat()
    })
