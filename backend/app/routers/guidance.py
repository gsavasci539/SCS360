"""
Guidance & Counseling (PDR) Module API
Handles guidance sessions, behavioral incidents, and confidential notes
"""
from __future__ import annotations
from app.core.dates import school_today
from datetime import datetime, date, time
from typing import Annotated, Optional, List, Literal
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select, and_, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.responses import success_response
from app.core.permissions import PermissionChecker
from app.core.tenant import TenantContext
from app.domain.entities import Student, User
from app.infrastructure.models.models import Role, RolePermission, Permission, UserRole, UserStatus
from app.core.exceptions import ForbiddenException, NotFoundException, ValidationException

router = APIRouter(prefix="/api/guidance", tags=["Guidance"])


async def validate_counselor(db, tenant, student_id, counselor_id):
    if counselor_id != tenant.user_id and not tenant.has_permission("guidance.read_confidential"):
        raise ForbiddenException("Başka bir danışman adına kayıt yazamazsınız")
    student = (await db.execute(select(Student).where(Student.id == student_id, Student.deleted_at.is_(None)))).scalar_one_or_none()
    if student is None:
        raise NotFoundException("Öğrenci bulunamadı")
    counselor = (await db.execute(select(User)
        .where(User.id == counselor_id, User.organization_id == student.organization_id, User.status == UserStatus.ACTIVE,
            User.deleted_at.is_(None)))).scalar_one_or_none()
    if counselor is None:
        raise ValidationException("Öğrenciyle aynı kurumda aktif danışman seçilmelidir")
    roles, assignments, permissions, links = Role.__table__, UserRole.__table__, Permission.__table__, RolePermission.__table__
    allowed = select(permissions.c.id).join(links, links.c.permission_id == permissions.c.id).join(roles, roles.c.id == links.c.role_id)
    allowed = allowed.join(assignments, assignments.c.role_id == roles.c.id).where(assignments.c.user_id == counselor.id,
        roles.c.deleted_at.is_(None), (roles.c.organization_id == student.organization_id) | roles.c.organization_id.is_(None),
        permissions.c.code == "guidance.write")
    if not counselor.is_super_admin and (await db.execute(allowed.limit(1))).first() is None:
        raise ValidationException("Seçilen danışmanın rehberlik kayıt yetkisi yok")
    return counselor.id


# ==================== Schemas ====================

class GuidanceSessionCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    student_id: UUID
    counselor_id: Optional[UUID] = None
    session_type: Literal["INDIVIDUAL", "GROUP", "FAMILY", "CRISIS"] = "INDIVIDUAL"
    session_date: date = Field(..., description="Session date")
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    summary: Optional[str] = Field(default=None, max_length=2000)
    action_plan: Optional[str] = Field(default=None, max_length=2000)
    confidentiality_level: Literal["STANDARD", "RESTRICTED", "CONFIDENTIAL"] = "STANDARD"
    follow_up_date: Optional[date] = None

    @field_validator("session_type", "confidentiality_level", mode="before")
    @classmethod
    def enum_values(cls, value):
        return value.strip().upper() if isinstance(value, str) else value

    @model_validator(mode="after")
    def dates(self):
        if any(value and value.tzinfo is not None for value in (self.start_time, self.end_time)):
            raise ValueError("Görüşme saatleri okulun yerel saatiyle ve saat dilimi eki olmadan girilmelidir")
        if self.start_time and self.end_time and self.end_time < self.start_time:
            raise ValueError("Görüşme bitiş saati başlangıçtan önce olamaz")
        if self.follow_up_date and self.follow_up_date < self.session_date:
            raise ValueError("Takip tarihi görüşmeden önce olamaz")
        return self

class BehavioralIncidentCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    student_id: UUID
    reported_by: Optional[UUID] = None
    incident_date: date = Field(..., description="Incident date")
    incident_time: Optional[time] = None
    location: Optional[str] = Field(default=None, max_length=255)
    description: str = Field(min_length=1, max_length=2000)
    severity: Literal["MINOR", "MODERATE", "SEVERE", "CRITICAL"] = "MINOR"
    witnesses: Optional[str] = Field(default=None, max_length=1000)
    action_taken: Optional[str] = Field(default=None, max_length=2000)
    parent_notified: bool = Field(default=False)
    resolved: bool = Field(default=False)
    resolution_date: Optional[date] = None
    resolution_notes: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("severity", mode="before")
    @classmethod
    def severity_value(cls, value):
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("incident_time")
    @classmethod
    def local_time(cls, value):
        if value and value.tzinfo is not None:
            raise ValueError("Olay saati okulun yerel saatiyle girilmelidir")
        return value

class GuidanceNoteCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    student_id: UUID
    counselor_id: Optional[UUID] = None
    note_type: Literal["OBSERVATION", "ASSESSMENT", "INTERVENTION"] = "OBSERVATION"
    content: str = Field(min_length=1, max_length=5000)
    confidentiality_level: Literal["STANDARD", "RESTRICTED", "CONFIDENTIAL"] = "STANDARD"
    tags: Optional[List[Annotated[str, Field(min_length=1, max_length=50)]]] = Field(default=None, max_length=20)

    @field_validator("note_type", "confidentiality_level", mode="before")
    @classmethod
    def enum_values(cls, value):
        return value.strip().upper() if isinstance(value, str) else value


class IncidentResolution(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    resolution_notes: Optional[str] = Field(default=None, max_length=2000)


@router.get("/options")
async def guidance_options(student_id: Optional[UUID] = None, search: str = Query("", max_length=100), counselor_search: str = Query("", max_length=100),
                            db: AsyncSession = Depends(get_db, scope="function"), tenant: TenantContext = Depends(PermissionChecker("guidance.read", "guidance.write"))):
    from app.application.services.guidance_service import options
    return success_response(await options(db, tenant, student_id, search, counselor_search))


@router.get("/summary")
async def guidance_summary(student_id: Optional[UUID] = None, db: AsyncSession = Depends(get_db, scope="function"),
                            tenant: TenantContext = Depends(PermissionChecker("guidance.read"))):
    from app.application.services.guidance_service import summary
    return success_response(await summary(db, student_id))


# ==================== Guidance Sessions Endpoints ====================

@router.get("/sessions")
async def get_guidance_sessions(
    student_id: Optional[UUID] = Query(None),
    counselor_id: Optional[UUID] = Query(None),
    session_type: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    confidentiality_level: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("guidance.read"))
):
    """Get guidance sessions with filtering"""
    from app.domain.entities.guidance import GuidanceSession
    
    query = select(GuidanceSession)
    
    conditions = []
    if student_id:
        conditions.append(GuidanceSession.student_id == student_id)
    if counselor_id:
        conditions.append(GuidanceSession.counselor_id == counselor_id)
    if session_type:
        conditions.append(GuidanceSession.session_type == session_type.upper())
    if start_date:
        conditions.append(GuidanceSession.session_date >= start_date)
    if end_date:
        conditions.append(GuidanceSession.session_date <= end_date)
    
    # Confidentiality filter - only show restricted/confidential to authorized users
    if confidentiality_level:
        conditions.append(GuidanceSession.confidentiality_level == confidentiality_level.upper())
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(GuidanceSession.session_date.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    sessions = result.scalars().all()
    
    enriched_sessions = []
    for session in sessions:
        # Get student name
        student_name = None
        if session.student_id:
            student_result = await db.execute(
                select(Student).where(Student.id == session.student_id)
            )
            student = student_result.scalar_one_or_none()
            if student:
                student_name = f"{student.first_name} {student.last_name}"
        
        # Get counselor name
        counselor_name = None
        if session.counselor_id:
            counselor_result = await db.execute(
                select(User).where(User.id == session.counselor_id)
            )
            counselor = counselor_result.scalar_one_or_none()
            if counselor:
                counselor_name = f"{counselor.first_name} {counselor.last_name}"
        
        enriched_sessions.append({
            "id": str(session.id),
            "student_id": str(session.student_id),
            "student_name": student_name,
            "counselor_id": str(session.counselor_id),
            "counselor_name": counselor_name,
            "session_type": session.session_type,
            "session_date": session.session_date.isoformat(),
            "start_time": session.start_time.strftime("%H:%M") if session.start_time else None,
            "end_time": session.end_time.strftime("%H:%M") if session.end_time else None,
            "summary": session.summary,
            "action_plan": session.action_plan,
            "confidentiality_level": session.confidentiality_level,
            "follow_up_date": session.follow_up_date.isoformat() if session.follow_up_date else None,
            "created_at": session.created_at.isoformat()
        })
    
    return success_response(enriched_sessions)


@router.post("/sessions")
async def create_guidance_session(
    session: GuidanceSessionCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("guidance.write"))
):
    """Create a new guidance session"""
    from app.domain.entities.guidance import GuidanceSession
    counselor_id = await validate_counselor(db, tenant, session.student_id, session.counselor_id or tenant.user_id)
    
    new_session = GuidanceSession(
        student_id=session.student_id,
        counselor_id=counselor_id,
        session_type=session.session_type.upper(),
        session_date=session.session_date,
        start_time=session.start_time,
        end_time=session.end_time,
        summary=session.summary,
        action_plan=session.action_plan,
        confidentiality_level=session.confidentiality_level.upper(),
        follow_up_date=session.follow_up_date
    )
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)
    
    return success_response({
        "id": str(new_session.id),
        "session_type": new_session.session_type,
        "session_date": new_session.session_date.isoformat(),
        "created_at": new_session.created_at.isoformat()
    })


@router.put("/sessions/{session_id}")
async def update_guidance_session(
    session_id: UUID,
    session: GuidanceSessionCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("guidance.write"))
):
    """Update a guidance session"""
    from app.domain.entities.guidance import GuidanceSession
    
    result = await db.execute(
        select(GuidanceSession).where(GuidanceSession.id == session_id)
    )
    existing_session = result.scalar_one_or_none()
    
    if not existing_session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.student_id != existing_session.student_id:
        raise ValidationException("Görüşmenin öğrencisi değiştirilemez")
    existing_session.counselor_id = await validate_counselor(db, tenant, session.student_id, session.counselor_id or existing_session.counselor_id)
    
    existing_session.session_type = session.session_type.upper()
    existing_session.session_date = session.session_date
    existing_session.start_time = session.start_time
    existing_session.end_time = session.end_time
    existing_session.summary = session.summary
    existing_session.action_plan = session.action_plan
    existing_session.confidentiality_level = session.confidentiality_level.upper()
    existing_session.follow_up_date = session.follow_up_date
    
    await db.commit()
    
    return success_response({
        "id": str(existing_session.id),
        "updated_at": existing_session.updated_at.isoformat()
    })


@router.get("/students/{student_id}/timeline")
async def get_student_guidance_timeline(
    student_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("guidance.read"))
):
    """Get student's guidance timeline including sessions, incidents, and notes"""
    from app.domain.entities.guidance import GuidanceSession, BehavioralIncident, GuidanceNote
    
    # Get sessions
    sessions_result = await db.execute(
        select(GuidanceSession).where(GuidanceSession.student_id == student_id)
    )
    sessions = sessions_result.scalars().all()
    
    # Get incidents
    incidents_result = await db.execute(
        select(BehavioralIncident).where(BehavioralIncident.student_id == student_id)
    )
    incidents = incidents_result.scalars().all()
    
    # Get notes
    notes_result = await db.execute(
        select(GuidanceNote).where(GuidanceNote.student_id == student_id)
    )
    notes = notes_result.scalars().all()
    
    # Build timeline
    timeline = []
    
    for session in sessions:
        counselor_result = await db.execute(
            select(User).where(User.id == session.counselor_id)
        )
        counselor = counselor_result.scalar_one_or_none()
        counselor_name = f"{counselor.first_name} {counselor.last_name}" if counselor else None
        
        timeline.append({
            "type": "SESSION",
            "date": session.session_date.isoformat(),
            "title": f"{session.session_type} Session",
            "description": session.summary,
            "counselor": counselor_name,
            "confidentiality_level": session.confidentiality_level
        })
    
    for incident in incidents:
        reporter_result = await db.execute(
            select(User).where(User.id == incident.reported_by)
        )
        reporter = reporter_result.scalar_one_or_none()
        reporter_name = f"{reporter.first_name} {reporter.last_name}" if reporter else None
        
        timeline.append({
            "type": "INCIDENT",
            "date": incident.incident_date.isoformat(),
            "title": f"Behavioral Incident - {incident.severity}",
            "description": incident.description,
            "reported_by": reporter_name,
            "resolved": incident.resolved
        })
    
    for note in notes:
        counselor_result = await db.execute(
            select(User).where(User.id == note.counselor_id)
        )
        counselor = counselor_result.scalar_one_or_none()
        counselor_name = f"{counselor.first_name} {counselor.last_name}" if counselor else None
        
        timeline.append({
            "type": "NOTE",
            "date": note.created_at.isoformat(),
            "title": f"{note.note_type} Note",
            "description": note.content,
            "counselor": counselor_name,
            "confidentiality_level": note.confidentiality_level,
            "tags": note.tags
        })
    
    # Sort by date
    timeline.sort(key=lambda x: x["date"], reverse=True)
    
    return success_response(timeline)


# ==================== Behavioral Incidents Endpoints ====================

@router.get("/incidents")
async def get_behavioral_incidents(
    student_id: Optional[UUID] = Query(None),
    severity: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    resolved: Optional[bool] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("guidance.read"))
):
    """Get behavioral incidents with filtering"""
    from app.domain.entities.guidance import BehavioralIncident
    
    query = select(BehavioralIncident)
    
    conditions = []
    if student_id:
        conditions.append(BehavioralIncident.student_id == student_id)
    if severity:
        conditions.append(BehavioralIncident.severity == severity.upper())
    if start_date:
        conditions.append(BehavioralIncident.incident_date >= start_date)
    if end_date:
        conditions.append(BehavioralIncident.incident_date <= end_date)
    if resolved is not None:
        conditions.append(BehavioralIncident.resolved == resolved)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(BehavioralIncident.incident_date.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    incidents = result.scalars().all()
    
    enriched_incidents = []
    for incident in incidents:
        # Get student name
        student_name = None
        if incident.student_id:
            student_result = await db.execute(
                select(Student).where(Student.id == incident.student_id)
            )
            student = student_result.scalar_one_or_none()
            if student:
                student_name = f"{student.first_name} {student.last_name}"
        
        # Get reported by name
        reported_by_name = None
        if incident.reported_by:
            reporter_result = await db.execute(
                select(User).where(User.id == incident.reported_by)
            )
            reporter = reporter_result.scalar_one_or_none()
            if reporter:
                reported_by_name = f"{reporter.first_name} {reporter.last_name}"
        
        enriched_incidents.append({
            "id": str(incident.id),
            "student_id": str(incident.student_id),
            "student_name": student_name,
            "reported_by": str(incident.reported_by),
            "reported_by_name": reported_by_name,
            "incident_date": incident.incident_date.isoformat(),
            "incident_time": incident.incident_time.strftime("%H:%M") if incident.incident_time else None,
            "location": incident.location,
            "description": incident.description,
            "severity": incident.severity,
            "witnesses": incident.witnesses,
            "action_taken": incident.action_taken,
            "parent_notified": incident.parent_notified,
            "resolved": incident.resolved,
            "resolution_date": incident.resolution_date.isoformat() if incident.resolution_date else None,
            "resolution_notes": incident.resolution_notes,
            "created_at": incident.created_at.isoformat()
        })
    
    return success_response(enriched_incidents)


@router.post("/incidents")
async def create_behavioral_incident(
    incident: BehavioralIncidentCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("guidance.write"))
):
    """Create a new behavioral incident"""
    from app.domain.entities.guidance import BehavioralIncident
    if incident.reported_by and incident.reported_by != tenant.user_id:
        raise ForbiddenException("Bildirici oturum açan kullanıcı olmalıdır")
    
    new_incident = BehavioralIncident(
        student_id=incident.student_id,
        reported_by=tenant.user_id,
        incident_date=incident.incident_date,
        incident_time=incident.incident_time,
        location=incident.location,
        description=incident.description,
        severity=incident.severity.upper(),
        witnesses=incident.witnesses,
        action_taken=incident.action_taken,
        parent_notified=incident.parent_notified,
        resolved=incident.resolved,
        resolution_date=incident.resolution_date,
        resolution_notes=incident.resolution_notes
    )
    db.add(new_incident)
    await db.commit()
    await db.refresh(new_incident)
    
    return success_response({
        "id": str(new_incident.id),
        "severity": new_incident.severity,
        "incident_date": new_incident.incident_date.isoformat(),
        "created_at": new_incident.created_at.isoformat()
    })


@router.put("/incidents/{incident_id}/resolve")
async def resolve_behavioral_incident(
    incident_id: UUID,
    resolution_notes: Optional[str] = Query(None, max_length=2000, deprecated=True),
    resolution: Optional[IncidentResolution] = Body(None),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("guidance.write"))
):
    """Resolve a behavioral incident"""
    from app.domain.entities.guidance import BehavioralIncident
    notes = resolution.resolution_notes if resolution is not None else resolution_notes
    changed = await db.execute(update(BehavioralIncident).where(BehavioralIncident.id == incident_id)
        .values(resolved=BehavioralIncident.resolved).execution_options(synchronize_session=False))
    if changed.rowcount != 1:
        raise NotFoundException("Olay kaydı bulunamadı")
    
    result = await db.execute(
        select(BehavioralIncident).where(BehavioralIncident.id == incident_id)
    )
    incident = result.scalar_one_or_none()
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    if not incident.resolved:
        incident.resolved = True
        incident.resolution_date = school_today()
        incident.resolution_notes = notes
    
    await db.commit()
    
    return success_response({
        "id": str(incident.id),
        "resolved": True,
        "resolution_date": incident.resolution_date.isoformat() if incident.resolution_date else None
    })


# ==================== Guidance Notes Endpoints ====================

@router.get("/notes")
async def get_guidance_notes(
    student_id: Optional[UUID] = Query(None),
    counselor_id: Optional[UUID] = Query(None),
    note_type: Optional[str] = Query(None),
    confidentiality_level: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("guidance.read"))
):
    """Get guidance notes with filtering"""
    from app.domain.entities.guidance import GuidanceNote
    
    query = select(GuidanceNote)
    
    conditions = []
    if student_id:
        conditions.append(GuidanceNote.student_id == student_id)
    if counselor_id:
        conditions.append(GuidanceNote.counselor_id == counselor_id)
    if note_type:
        conditions.append(GuidanceNote.note_type == note_type.upper())
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(GuidanceNote.created_at.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    notes = result.scalars().all()
    
    enriched_notes = []
    for note in notes:
        # Get student name
        student_name = None
        if note.student_id:
            student_result = await db.execute(
                select(Student).where(Student.id == note.student_id)
            )
            student = student_result.scalar_one_or_none()
            if student:
                student_name = f"{student.first_name} {student.last_name}"
        
        # Get counselor name
        counselor_name = None
        if note.counselor_id:
            counselor_result = await db.execute(
                select(User).where(User.id == note.counselor_id)
            )
            counselor = counselor_result.scalar_one_or_none()
            if counselor:
                counselor_name = f"{counselor.first_name} {counselor.last_name}"
        
        # Filter content based on confidentiality
        content = note.content
        
        enriched_notes.append({
            "id": str(note.id),
            "student_id": str(note.student_id),
            "student_name": student_name,
            "counselor_id": str(note.counselor_id),
            "counselor_name": counselor_name,
            "note_type": note.note_type,
            "content": content,
            "confidentiality_level": note.confidentiality_level,
            "tags": note.tags,
            "created_at": note.created_at.isoformat()
        })
    
    return success_response(enriched_notes)


@router.post("/notes")
async def create_guidance_note(
    note: GuidanceNoteCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("guidance.write"))
):
    """Create a new guidance note"""
    from app.domain.entities.guidance import GuidanceNote
    counselor_id = await validate_counselor(db, tenant, note.student_id, note.counselor_id or tenant.user_id)
    
    new_note = GuidanceNote(
        student_id=note.student_id,
        counselor_id=counselor_id,
        note_type=note.note_type.upper(),
        content=note.content,
        confidentiality_level=note.confidentiality_level.upper(),
        tags=note.tags
    )
    db.add(new_note)
    await db.commit()
    await db.refresh(new_note)
    
    return success_response({
        "id": str(new_note.id),
        "note_type": new_note.note_type,
        "confidentiality_level": new_note.confidentiality_level,
        "created_at": new_note.created_at.isoformat()
    })
