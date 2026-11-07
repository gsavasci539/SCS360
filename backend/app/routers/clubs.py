"""
Kulüpler & Sosyal Etkinlikler Module API
Handles school clubs, memberships, events, and certificates
"""
from __future__ import annotations
from datetime import date, time
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.responses import success_response
from app.core.permissions import PermissionChecker
from app.core.tenant import TenantContext
from app.domain.entities import Student, User, Branch
from app.application.services import club_service
from app.core.dates import school_today
from app.infrastructure.repositories.base import BaseRepository
from fastapi.responses import Response

router = APIRouter(prefix="/api/clubs", tags=["Clubs"])


async def named_rows(db, model, identifiers, name_column=None):
    if not identifiers:
        return {}
    rows = (await db.execute(select(model).where(model.id.in_(identifiers)))).scalars()
    return {row.id: getattr(row, name_column) if name_column else f"{row.first_name} {row.last_name}" for row in rows if row is not None}


# ==================== Schemas ====================

class SchoolClubCreate(BaseModel):
    branch_id: UUID
    club_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    advisor_teacher_id: Optional[UUID] = None
    max_members: int = Field(default=30, ge=1, le=10000)
    meeting_day: Optional[str] = Field(None, max_length=20)
    meeting_time: Optional[time] = None
    meeting_location: Optional[str] = Field(None, max_length=255)

class ClubMembershipCreate(BaseModel):
    club_id: UUID
    student_id: UUID
    role: str = Field(default="MEMBER", min_length=1, max_length=50)
    notes: Optional[str] = None

class ClubEventCreate(BaseModel):
    club_id: UUID
    event_name: str = Field(..., min_length=1, max_length=255)
    event_date: date = Field(..., description="Event date")
    event_time: Optional[time] = None
    location: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    max_participants: Optional[int] = Field(None, ge=1)

class StudentCertificateCreate(BaseModel):
    student_id: UUID
    certificate_type: str = Field(..., min_length=1, max_length=50)
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1200)
    event_id: Optional[UUID] = None
    template_id: Optional[str] = "scs360"


# ==================== School Clubs Endpoints ====================

@router.get("/options")
async def club_options(branch_id: Optional[UUID] = None, search: str = Query("", max_length=100),
    limit: int = Query(100, ge=1, le=200), db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("clubs.write"))):
    from sqlalchemy import or_
    from app.infrastructure.models.models import Role, UserRole
    branches = (await db.execute(select(Branch.id, Branch.name).where(Branch.deleted_at.is_(None)).order_by(Branch.name))).all()
    if branch_id is None:
        return success_response({"branches": [{"id": str(row.id), "name": row.name} for row in branches], "students": [], "teachers": [], "student_count": 0})
    branch = await BaseRepository(db, tenant).get_by_id(branch_id, Branch)
    query = select(Student).where(Student.branch_id == branch.id, Student.deleted_at.is_(None), Student.status == "ACTIVE")
    if search.strip():
        value = "%" + search.strip() + "%"
        query = query.where(or_(Student.first_name.ilike(value), Student.last_name.ilike(value), Student.student_number.ilike(value)))
    count = (await db.execute(query.with_only_columns(func.count()).select_from(Student))).scalar_one()
    students = (await db.execute(query.order_by(Student.last_name, Student.first_name).limit(limit))).scalars()
    teachers = (await db.execute(select(User.id, User.first_name, User.last_name).join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id).where(User.organization_id == branch.organization_id,
            User.deleted_at.is_(None), User.status == "ACTIVE", Role.slug == "teacher", Role.deleted_at.is_(None),
            or_(Role.organization_id.is_(None), Role.organization_id == branch.organization_id)).distinct())).all()
    return success_response({"branches": [{"id": str(row.id), "name": row.name} for row in branches],
        "students": [{"id": str(row.id), "name": f"{row.first_name} {row.last_name}", "student_number": row.student_number} for row in students],
        "teachers": [{"id": str(row.id), "name": f"{row.first_name} {row.last_name}"} for row in teachers], "student_count": count})


@router.get("")
@router.get("/clubs")
async def get_school_clubs(
    branch_id: Optional[UUID] = Query(None),
    is_active: Optional[bool] = Query(True),
    search: str = Query("", max_length=100),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db, scope="function"),
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
    if search.strip():
        conditions.append(SchoolClub.club_name.ilike("%" + search.strip() + "%"))
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(SchoolClub.club_name, SchoolClub.id).limit(limit).offset(offset)
    
    result = await db.execute(query)
    clubs = result.scalars().all()
    from app.domain.entities.clubs import ClubMembership
    table = ClubMembership.__table__
    students, club_table, branches = Student.__table__, SchoolClub.__table__, Branch.__table__
    counts = dict((await db.execute(select(table.c.club_id, func.count(func.distinct(table.c.student_id)))
        .select_from(table.join(students, students.c.id == table.c.student_id).join(club_table, club_table.c.id == table.c.club_id)
            .join(branches, branches.c.id == club_table.c.branch_id))
        .where(table.c.club_id.in_([club.id for club in clubs]), table.c.status == "ACTIVE", students.c.deleted_at.is_(None),
            students.c.status == "ACTIVE", students.c.branch_id == club_table.c.branch_id,
            students.c.organization_id == branches.c.organization_id).group_by(table.c.club_id))).all()) if clubs else {}
    
    branches = await named_rows(db, Branch, {club.branch_id for club in clubs}, "name")
    advisors = await named_rows(db, User, {club.advisor_teacher_id for club in clubs if club.advisor_teacher_id})
    enriched_clubs = []
    for club in clubs:
        enriched_clubs.append({
            "id": str(club.id),
            "branch_id": str(club.branch_id),
            "branch_name": branches.get(club.branch_id),
            "club_name": club.club_name,
            "description": club.description,
            "advisor_teacher_id": str(club.advisor_teacher_id) if club.advisor_teacher_id else None,
            "advisor_name": advisors.get(club.advisor_teacher_id),
            "max_members": club.max_members,
            "current_members": counts.get(club.id, 0),
            "meeting_day": club.meeting_day,
            "meeting_time": club.meeting_time.strftime("%H:%M") if club.meeting_time else None,
            "meeting_location": club.meeting_location,
            "is_active": club.is_active,
            "created_at": club.created_at.isoformat()
        })
    
    return success_response(enriched_clubs)


@router.post("/clubs")
async def create_school_club(club: SchoolClubCreate, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("clubs.write"))):
    return success_response(await club_service.save_club(db, tenant, club), "Kulüp kaydedildi")


@router.put("/clubs/{club_id}")
async def update_school_club(club_id: UUID, club: SchoolClubCreate, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("clubs.write"))):
    return success_response(await club_service.save_club(db, tenant, club, club_id), "Kulüp güncellendi")

@router.get("/memberships")
async def get_club_memberships(
    club_id: Optional[UUID] = Query(None),
    student_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db, scope="function"),
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
    
    query = query.order_by(ClubMembership.joined_date.desc(), ClubMembership.id).limit(limit).offset(offset)
    
    result = await db.execute(query)
    memberships = result.scalars().all()
    
    from app.domain.entities.clubs import SchoolClub
    clubs = await named_rows(db, SchoolClub, {row.club_id for row in memberships}, "club_name")
    students = await named_rows(db, Student, {row.student_id for row in memberships})
    enriched_memberships = []
    for membership in memberships:
        enriched_memberships.append({
            "id": str(membership.id),
            "club_id": str(membership.club_id),
            "club_name": clubs.get(membership.club_id),
            "student_id": str(membership.student_id),
            "student_name": students.get(membership.student_id),
            "joined_date": membership.joined_date.isoformat(),
            "role": membership.role,
            "status": membership.status,
            "notes": membership.notes,
            "created_at": membership.created_at.isoformat()
        })
    
    return success_response(enriched_memberships)


@router.post("/memberships")
async def create_club_membership(membership: ClubMembershipCreate, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("clubs.write"))):
    return success_response(await club_service.enroll(db, tenant, membership), "Kulüp üyeliği kaydedildi")


@router.delete("/memberships/{membership_id}")
async def leave_club(membership_id: UUID, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("clubs.write"))):
    return success_response(await club_service.leave(db, tenant, membership_id), "Kulüp üyeliği sonlandırıldı")

@router.get("/events")
async def get_club_events(
    club_id: Optional[UUID] = Query(None),
    search: str = Query("", max_length=100),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("clubs.read"))
):
    """Get club events with filtering"""
    from app.domain.entities.clubs import ClubEvent
    
    query = select(ClubEvent)
    
    conditions = []
    if club_id:
        conditions.append(ClubEvent.club_id == club_id)
    if search.strip():
        conditions.append(ClubEvent.event_name.ilike("%" + search.strip() + "%"))
    if start_date:
        conditions.append(ClubEvent.event_date >= start_date)
    if end_date:
        conditions.append(ClubEvent.event_date <= end_date)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(ClubEvent.event_date.desc(), ClubEvent.id).limit(limit).offset(offset)
    
    result = await db.execute(query)
    events = result.scalars().all()
    
    from app.domain.entities.clubs import SchoolClub
    clubs = await named_rows(db, SchoolClub, {row.club_id for row in events}, "club_name")
    enriched_events = []
    for event in events:
        enriched_events.append({
            "id": str(event.id),
            "club_id": str(event.club_id),
            "club_name": clubs.get(event.club_id),
            "event_name": event.event_name,
            "event_date": event.event_date.isoformat(),
            "status": "SCHEDULED" if event.event_date >= school_today() else "PAST",
            "event_time": event.event_time.strftime("%H:%M") if event.event_time else None,
            "location": event.location,
            "description": event.description,
            "max_participants": event.max_participants,
            "created_at": event.created_at.isoformat()
        })
    
    return success_response(enriched_events)


@router.post("/events")
async def create_club_event(event: ClubEventCreate, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("clubs.write"))):
    return success_response(await club_service.save_event(db, tenant, event), "Etkinlik kaydedildi")

@router.get("/certificates")
async def get_student_certificates(
    student_id: Optional[UUID] = Query(None),
    certificate_type: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db, scope="function"),
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
    
    query = query.order_by(StudentCertificate.issue_date.desc(), StudentCertificate.created_at.desc(), StudentCertificate.id).limit(limit).offset(offset)
    
    result = await db.execute(query)
    certificates = result.scalars().all()
    
    students = await named_rows(db, Student, {row.student_id for row in certificates})
    issuers = await named_rows(db, User, {row.issued_by for row in certificates if row.issued_by})
    enriched_certificates = []
    for cert in certificates:
        enriched_certificates.append({
            "id": str(cert.id),
            "student_id": str(cert.student_id),
            "student_name": students.get(cert.student_id),
            "certificate_type": cert.certificate_type,
            "title": cert.title,
            "description": cert.description,
            "issue_date": cert.issue_date.isoformat(),
            "issued_by": str(cert.issued_by) if cert.issued_by else None,
            "issued_by_name": issuers.get(cert.issued_by),
            "event_id": str(cert.event_id) if cert.event_id else None,
            "template_id": cert.template_id,
            "pdf_url": f"/api/clubs/certificates/{cert.id}/pdf",
            "created_at": cert.created_at.isoformat()
        })
    
    return success_response(enriched_certificates)


@router.post("/certificates")
async def create_student_certificate(certificate: StudentCertificateCreate, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("clubs.write"))):
    return success_response(await club_service.certificate(db, tenant, certificate), "Öğrenci belgesi oluşturuldu")


@router.get("/certificates/{certificate_id}/pdf")
async def download_certificate(certificate_id: UUID, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("clubs.read"))):
    from app.infrastructure.pdf.certificate_pdf import generate_certificate_pdf
    context = await club_service.certificate_context(db, tenant, certificate_id)
    return Response(content=generate_certificate_pdf(context), media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="scs360-certificate-{certificate_id}.pdf"',
            "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})
