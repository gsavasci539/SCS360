"""
Kulüpler & Sosyal Etkinlikler Module API
Handles school clubs, memberships, events, and certificates
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

router = APIRouter(prefix="/api/clubs", tags=["Clubs"])


# ==================== Schemas ====================

class SchoolClubCreate(BaseModel):
    branch_id: UUID
    club_name: str = Field(..., max_length=255)
    description: Optional[str] = None
    advisor_teacher_id: Optional[UUID] = None
    max_members: int = Field(default=30, ge=1)
    meeting_day: Optional[str] = None
    meeting_time: Optional[time] = None
    meeting_location: Optional[str] = None

class ClubMembershipCreate(BaseModel):
    club_id: UUID
    student_id: UUID
    role: str = Field(default="MEMBER")
    notes: Optional[str] = None

class ClubEventCreate(BaseModel):
    club_id: UUID
    event_name: str = Field(..., max_length=255)
    event_date: date = Field(..., description="Event date")
    event_time: Optional[time] = None
    location: Optional[str] = None
    description: Optional[str] = None
    max_participants: Optional[int] = None

class StudentCertificateCreate(BaseModel):
    student_id: UUID
    certificate_type: str = Field(..., max_length=50)
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    event_id: Optional[UUID] = None
    template_id: Optional[str] = None


# ==================== School Clubs Endpoints ====================

@router.get("/clubs")
async def get_school_clubs(
    branch_id: Optional[UUID] = Query(None),
    is_active: Optional[bool] = Query(True),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("clubs.read"))
):
    """Get school clubs with filtering"""
    from app.domain.entities.clubs import SchoolClub
    
    query = select(SchoolClub)
    
    conditions = []
    if branch_id:
        conditions.append(SchoolClub.branch_id == branch_id)
    if is_active is not None:
        conditions.append(SchoolClub.is_active == is_active)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(SchoolClub.club_name).limit(limit).offset(offset)
    
    result = await db.execute(query)
    clubs = result.scalars().all()
    
    enriched_clubs = []
    for club in clubs:
        # Get branch name
        branch_name = None
        if club.branch_id:
            branch_result = await db.execute(
                select(Branch).where(Branch.id == club.branch_id)
            )
            branch = branch_result.scalar_one_or_none()
            if branch:
                branch_name = branch.name
        
        # Get advisor teacher name
        advisor_name = None
        if club.advisor_teacher_id:
            teacher_result = await db.execute(
                select(User).where(User.id == club.advisor_teacher_id)
            )
            teacher = teacher_result.scalar_one_or_none()
            if teacher:
                advisor_name = f"{teacher.first_name} {teacher.last_name}"
        
        enriched_clubs.append({
            "id": str(club.id),
            "branch_id": str(club.branch_id),
            "branch_name": branch_name,
            "club_name": club.club_name,
            "description": club.description,
            "advisor_teacher_id": str(club.advisor_teacher_id) if club.advisor_teacher_id else None,
            "advisor_name": advisor_name,
            "max_members": club.max_members,
            "current_members": club.current_members,
            "meeting_day": club.meeting_day,
            "meeting_time": club.meeting_time.strftime("%H:%M") if club.meeting_time else None,
            "meeting_location": club.meeting_location,
            "is_active": club.is_active,
            "created_at": club.created_at.isoformat()
        })
    
    return success_response(enriched_clubs)


@router.post("/clubs")
async def create_school_club(
    club: SchoolClubCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("clubs.write"))
):
    """Create a new school club"""
    from app.domain.entities.clubs import SchoolClub
    
    new_club = SchoolClub(
        branch_id=club.branch_id,
        club_name=club.club_name,
        description=club.description,
        advisor_teacher_id=club.advisor_teacher_id,
        max_members=club.max_members,
        meeting_day=club.meeting_day,
        meeting_time=club.meeting_time,
        meeting_location=club.meeting_location,
        is_active=True,
        current_members=0
    )
    db.add(new_club)
    await db.commit()
    await db.refresh(new_club)
    
    return success_response({
        "id": str(new_club.id),
        "club_name": new_club.club_name,
        "max_members": new_club.max_members,
        "created_at": new_club.created_at.isoformat()
    })


@router.put("/clubs/{club_id}")
async def update_school_club(
    club_id: UUID,
    club: SchoolClubCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("clubs.write"))
):
    """Update a school club"""
    from app.domain.entities.clubs import SchoolClub
    
    result = await db.execute(
        select(SchoolClub).where(SchoolClub.id == club_id)
    )
    existing_club = result.scalar_one_or_none()
    
    if not existing_club:
        raise HTTPException(status_code=404, detail="Club not found")
    
    existing_club.branch_id = club.branch_id
    existing_club.club_name = club.club_name
    existing_club.description = club.description
    existing_club.advisor_teacher_id = club.advisor_teacher_id
    existing_club.max_members = club.max_members
    existing_club.meeting_day = club.meeting_day
    existing_club.meeting_time = club.meeting_time
    existing_club.meeting_location = club.meeting_location
    
    await db.commit()
    
    return success_response({
        "id": str(existing_club.id),
        "updated_at": existing_club.updated_at.isoformat()
    })


# ==================== Club Memberships Endpoints ====================

@router.get("/memberships")
async def get_club_memberships(
    club_id: Optional[UUID] = Query(None),
    student_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("clubs.read"))
):
    """Get club memberships with filtering"""
    from app.domain.entities.clubs import ClubMembership
    
    query = select(ClubMembership)
    
    conditions = []
    if club_id:
        conditions.append(ClubMembership.club_id == club_id)
    if student_id:
        conditions.append(ClubMembership.student_id == student_id)
    if status:
        conditions.append(ClubMembership.status == status.upper())
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(ClubMembership.joined_date.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    memberships = result.scalars().all()
    
    enriched_memberships = []
    for membership in memberships:
        # Get club name
        club_name = None
        if membership.club_id:
            from app.domain.entities.clubs import SchoolClub
            club_result = await db.execute(
                select(SchoolClub).where(SchoolClub.id == membership.club_id)
            )
            club = club_result.scalar_one_or_none()
            if club:
                club_name = club.club_name
        
        # Get student name
        student_name = None
        if membership.student_id:
            student_result = await db.execute(
                select(Student).where(Student.id == membership.student_id)
            )
            student = student_result.scalar_one_or_none()
            if student:
                student_name = f"{student.first_name} {student.last_name}"
        
        enriched_memberships.append({
            "id": str(membership.id),
            "club_id": str(membership.club_id),
            "club_name": club_name,
            "student_id": str(membership.student_id),
            "student_name": student_name,
            "joined_date": membership.joined_date.isoformat(),
            "role": membership.role,
            "status": membership.status,
            "notes": membership.notes,
            "created_at": membership.created_at.isoformat()
        })
    
    return success_response(enriched_memberships)


@router.post("/memberships")
async def create_club_membership(
    membership: ClubMembershipCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("clubs.write"))
):
    """Create a new club membership"""
    from app.domain.entities.clubs import ClubMembership, SchoolClub
    
    # Check if club has capacity
    club_result = await db.execute(
        select(SchoolClub).where(SchoolClub.id == membership.club_id)
    )
    club = club_result.scalar_one_or_none()
    
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")
    
    if club.current_members >= club.max_members:
        raise HTTPException(status_code=400, detail="Club has reached maximum capacity")
    
    # Check if student is already a member
    existing_result = await db.execute(
        select(ClubMembership).where(
            and_(
                ClubMembership.club_id == membership.club_id,
                ClubMembership.student_id == membership.student_id
            )
        )
    )
    existing = existing_result.scalar_one_or_none()
    
    if existing:
        existing.status = "ACTIVE"
        existing.role = membership.role
        existing.notes = membership.notes
    else:
        new_membership = ClubMembership(
            club_id=membership.club_id,
            student_id=membership.student_id,
            role=membership.role,
            notes=membership.notes,
            status="ACTIVE"
        )
        db.add(new_membership)
        
        # Update club member count
        club.current_members += 1
    
    await db.commit()
    
    return success_response({
        "message": "Club membership created successfully",
        "club_id": str(membership.club_id),
        "student_id": str(membership.student_id)
    })


# ==================== Club Events Endpoints ====================

@router.get("/events")
async def get_club_events(
    club_id: Optional[UUID] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("clubs.read"))
):
    """Get club events with filtering"""
    from app.domain.entities.clubs import ClubEvent
    
    query = select(ClubEvent)
    
    conditions = []
    if club_id:
        conditions.append(ClubEvent.club_id == club_id)
    if start_date:
        conditions.append(ClubEvent.event_date >= start_date)
    if end_date:
        conditions.append(ClubEvent.event_date <= end_date)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(ClubEvent.event_date.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    events = result.scalars().all()
    
    enriched_events = []
    for event in events:
        # Get club name
        club_name = None
        if event.club_id:
            from app.domain.entities.clubs import SchoolClub
            club_result = await db.execute(
                select(SchoolClub).where(SchoolClub.id == event.club_id)
            )
            club = club_result.scalar_one_or_none()
            if club:
                club_name = club.club_name
        
        enriched_events.append({
            "id": str(event.id),
            "club_id": str(event.club_id),
            "club_name": club_name,
            "event_name": event.event_name,
            "event_date": event.event_date.isoformat(),
            "event_time": event.event_time.strftime("%H:%M") if event.event_time else None,
            "location": event.location,
            "description": event.description,
            "max_participants": event.max_participants,
            "created_at": event.created_at.isoformat()
        })
    
    return success_response(enriched_events)


@router.post("/events")
async def create_club_event(
    event: ClubEventCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("clubs.write"))
):
    """Create a new club event"""
    from app.domain.entities.clubs import ClubEvent
    
    new_event = ClubEvent(
        club_id=event.club_id,
        event_name=event.event_name,
        event_date=event.event_date,
        event_time=event.event_time,
        location=event.location,
        description=event.description,
        max_participants=event.max_participants
    )
    db.add(new_event)
    await db.commit()
    await db.refresh(new_event)
    
    return success_response({
        "id": str(new_event.id),
        "event_name": new_event.event_name,
        "event_date": new_event.event_date.isoformat(),
        "created_at": new_event.created_at.isoformat()
    })


# ==================== Student Certificates Endpoints ====================

@router.get("/certificates")
async def get_student_certificates(
    student_id: Optional[UUID] = Query(None),
    certificate_type: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("clubs.read"))
):
    """Get student certificates with filtering"""
    from app.domain.entities.clubs import StudentCertificate
    
    query = select(StudentCertificate)
    
    conditions = []
    if student_id:
        conditions.append(StudentCertificate.student_id == student_id)
    if certificate_type:
        conditions.append(StudentCertificate.certificate_type == certificate_type)
    if start_date:
        conditions.append(StudentCertificate.issue_date >= start_date)
    if end_date:
        conditions.append(StudentCertificate.issue_date <= end_date)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(StudentCertificate.issue_date.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    certificates = result.scalars().all()
    
    enriched_certificates = []
    for cert in certificates:
        # Get student name
        student_name = None
        if cert.student_id:
            student_result = await db.execute(
                select(Student).where(Student.id == cert.student_id)
            )
            student = student_result.scalar_one_or_none()
            if student:
                student_name = f"{student.first_name} {student.last_name}"
        
        # Get issued by name
        issued_by_name = None
        if cert.issued_by:
            user_result = await db.execute(
                select(User).where(User.id == cert.issued_by)
            )
            user = user_result.scalar_one_or_none()
            if user:
                issued_by_name = f"{user.first_name} {user.last_name}"
        
        enriched_certificates.append({
            "id": str(cert.id),
            "student_id": str(cert.student_id),
            "student_name": student_name,
            "certificate_type": cert.certificate_type,
            "title": cert.title,
            "description": cert.description,
            "issue_date": cert.issue_date.isoformat(),
            "issued_by": str(cert.issued_by) if cert.issued_by else None,
            "issued_by_name": issued_by_name,
            "event_id": str(cert.event_id) if cert.event_id else None,
            "template_id": cert.template_id,
            "pdf_url": cert.pdf_url,
            "created_at": cert.created_at.isoformat()
        })
    
    return success_response(enriched_certificates)


@router.post("/certificates")
async def create_student_certificate(
    certificate: StudentCertificateCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("clubs.write"))
):
    """Create a new student certificate"""
    from app.domain.entities.clubs import StudentCertificate
    
    new_certificate = StudentCertificate(
        student_id=certificate.student_id,
        certificate_type=certificate.certificate_type,
        title=certificate.title,
        description=certificate.description,
        event_id=certificate.event_id,
        template_id=certificate.template_id,
        issued_by=None  # Will be set from current user context
    )
    db.add(new_certificate)
    await db.commit()
    await db.refresh(new_certificate)
    
    # TODO: Generate PDF using template
    
    return success_response({
        "id": str(new_certificate.id),
        "title": new_certificate.title,
        "certificate_type": new_certificate.certificate_type,
        "issue_date": new_certificate.issue_date.isoformat(),
        "created_at": new_certificate.created_at.isoformat()
    })
