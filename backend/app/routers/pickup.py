"""
Student Pickup/Dismissal Desk Module API
Handles pickup authorizations and pickup logs
"""
from __future__ import annotations
from app.core.dates import school_today, school_day_bounds
from datetime import datetime, date
from typing import Optional, List
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select, and_, func, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.responses import success_response
from app.core.permissions import PermissionChecker
from app.core.tenant import TenantContext
from app.domain.entities import Student, User
from app.core.exceptions import ConflictException, NotFoundException
from app.application.services.consent_service import utc_iso
from app.application.services import pickup_service as service

router = APIRouter(prefix="/api/dismissal", tags=["Dismissal"])


async def lock_student(db, student_id):
    changed = await db.execute(update(Student).where(Student.id == student_id, Student.deleted_at.is_(None))
        .values(updated_at=Student.updated_at).execution_options(synchronize_session=False))
    if changed.rowcount != 1:
        raise NotFoundException("Öğrenci bulunamadı")
    return (await db.execute(select(Student).where(Student.id == student_id).execution_options(populate_existing=True))).scalar_one()


# ==================== Schemas ====================

class PickupAuthorizationCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    student_id: UUID
    authorized_person_name: str = Field(min_length=1, max_length=255)
    authorized_person_id: str = Field(min_length=1, max_length=50)
    relationship: Optional[str] = Field(None, max_length=100)
    photo_url: Optional[str] = Field(default=None, max_length=500)
    phone: Optional[str] = Field(None, max_length=20)
    valid_from: date = Field(..., description="Valid from date")
    valid_until: Optional[date] = None
    notes: Optional[str] = Field(default=None, max_length=1000)
    request_id: UUID = Field(default_factory=uuid4, description="Aynı yetki oluşturma tekrarında aynı UUID")

    @model_validator(mode="after")
    def dates(self):
        if self.valid_until and self.valid_until < self.valid_from:
            raise ValueError("Geçerlilik bitişi başlangıçtan önce olamaz")
        return self

class PickupLogCreate(BaseModel):
    student_id: UUID
    authorization_id: Optional[UUID] = None
    pickup_person_name: str = Field(..., max_length=255)
    pickup_person_id: Optional[str] = Field(None, max_length=50)
    verified_by: UUID
    verification_method: str = Field(default="ID_CARD", description="ID_CARD, QR_CODE, FACE_RECOGNITION")
    notes: Optional[str] = None

class PickupVerificationRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    student_id: UUID
    pickup_person_id: str = Field(min_length=1, max_length=50)
    pickup_person_name: Optional[str] = Field(None, max_length=255, description="Uyumluluk alanı; kayıtlı yetkilinin adı kullanılır")
    request_id: UUID = Field(default_factory=uuid4, description="Retry the same delivery with the same request UUID")


# ==================== Pickup Authorizations Endpoints ====================

@router.get("/options")
async def options(student_id: Optional[UUID] = None, search: str = Query("", max_length=100), db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("dismissal.read"))):
    from app.application.services.student_choices import options as choices
    return success_response(await choices(db, student_id, search.strip()))


@router.get("/summary")
async def summary(student_id: Optional[UUID] = None, day: Optional[date] = Query(None, alias="date"), db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("dismissal.read"))):
    return success_response(await service.summary(db, day, student_id))

@router.get("/authorizations")
async def get_pickup_authorizations(
    student_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("dismissal.read"))
):
    """Get pickup authorizations with filtering"""
    from app.domain.entities.pickup import PickupAuthorization
    
    query = select(PickupAuthorization)
    
    conditions = []
    if student_id:
        conditions.append(PickupAuthorization.student_id == student_id)
    if status:
        conditions.append(PickupAuthorization.status == status.upper())
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(PickupAuthorization.valid_from.desc(), PickupAuthorization.id).limit(limit).offset(offset)
    
    result = await db.execute(query)
    authorizations = result.scalars().all()
    
    enriched_authorizations = []
    for auth in authorizations:
        # Get student name
        student_name = None
        student = None
        if auth.student_id:
            student_result = await db.execute(
                select(Student).where(Student.id == auth.student_id)
            )
            student = student_result.scalar_one_or_none()
            if student:
                student_name = f"{student.first_name} {student.last_name}"
        
        # Get created by name
        created_by_name = None
        if auth.created_by:
            user_result = await db.execute(
                select(User).where(User.id == auth.created_by)
            )
            user = user_result.scalar_one_or_none()
            if user:
                created_by_name = f"{user.first_name} {user.last_name}"
        
        enriched_authorizations.append({
            "id": str(auth.id),
            "student_id": str(auth.student_id),
            "student_name": student_name,
            "authorized_person_name": auth.authorized_person_name,
            "authorized_person_id": auth.authorized_person_id,
            "relationship": auth.relationship,
            "photo_url": auth.photo_url,
            "phone": auth.phone,
            "valid_from": auth.valid_from.isoformat(),
            "valid_until": auth.valid_until.isoformat() if auth.valid_until else None,
            "status": auth.status,
            "notes": auth.notes,
            "created_at": auth.created_at.isoformat(),
            "created_by": str(auth.created_by) if auth.created_by else None,
            "created_by_name": created_by_name,
            "effective_status": service.effective_status(auth, student)
        })
    
    return success_response(enriched_authorizations)


@router.post("/authorizations")
async def create_pickup_authorization(
    authorization: PickupAuthorizationCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("dismissal.write"))
):
    """Create a new pickup authorization"""
    from app.domain.entities.pickup import PickupAuthorization
    student = await lock_student(db, authorization.student_id)
    previous = await service.replay(db, tenant, authorization)
    if previous:
        return success_response(service.authorization_data(previous, student))
    if student.status != "ACTIVE":
        raise HTTPException(409, "Teslim yetkisi yalnız aktif öğrenci için oluşturulabilir")
    await service.check_overlap(db, authorization)
    
    new_authorization = PickupAuthorization(
        id=authorization.request_id,
        student_id=authorization.student_id,
        authorized_person_name=authorization.authorized_person_name,
        authorized_person_id=authorization.authorized_person_id,
        relationship=authorization.relationship,
        photo_url=authorization.photo_url,
        phone=authorization.phone,
        valid_from=authorization.valid_from,
        valid_until=authorization.valid_until,
        status="ACTIVE",
        notes=authorization.notes,
        created_by=tenant.user_id
    )
    db.add(new_authorization)
    service.audit(db, tenant, student, new_authorization, "PICKUP_AUTHORIZATION_CREATED", {"request_sha256": service.fingerprint(tenant, authorization)})
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        student = (await db.execute(select(Student).where(Student.id == authorization.student_id))).scalar_one()
        previous = await service.replay(db, tenant, authorization)
        if previous:
            return success_response(service.authorization_data(previous, student))
        raise
    await db.refresh(new_authorization)
    
    return success_response({
        "id": str(new_authorization.id),
        "authorized_person_name": new_authorization.authorized_person_name,
        "valid_from": new_authorization.valid_from.isoformat(),
        "status": new_authorization.status,
        "created_at": new_authorization.created_at.isoformat()
    })


@router.put("/authorizations/{authorization_id}")
async def update_pickup_authorization(
    authorization_id: UUID,
    authorization: PickupAuthorizationCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("dismissal.write"))
):
    """Update a pickup authorization"""
    from app.domain.entities.pickup import PickupAuthorization
    
    result = await db.execute(
        select(PickupAuthorization).where(PickupAuthorization.id == authorization_id)
    )
    existing_auth = result.scalar_one_or_none()
    
    if not existing_auth:
        raise HTTPException(status_code=404, detail="Authorization not found")
    if authorization.student_id != existing_auth.student_id:
        raise ConflictException("Teslim yetkisinin öğrencisi değiştirilemez")
    student = await lock_student(db, existing_auth.student_id)
    await db.refresh(existing_auth)
    if student.status != "ACTIVE" or existing_auth.status != "ACTIVE":
        raise HTTPException(409, "Yalnız aktif öğrenciye ait açık teslim yetkisi düzenlenebilir")
    await service.check_overlap(db, authorization, existing_auth.id)
    
    existing_auth.authorized_person_name = authorization.authorized_person_name
    existing_auth.authorized_person_id = authorization.authorized_person_id
    existing_auth.relationship = authorization.relationship
    existing_auth.photo_url = authorization.photo_url
    existing_auth.phone = authorization.phone
    existing_auth.valid_from = authorization.valid_from
    existing_auth.valid_until = authorization.valid_until
    existing_auth.notes = authorization.notes
    service.audit(db, tenant, student, existing_auth, "PICKUP_AUTHORIZATION_UPDATED", {"fields": sorted(authorization.model_fields_set - {"request_id", "student_id"})})
    
    await db.commit()
    await db.refresh(existing_auth)
    
    return success_response({
        "id": str(existing_auth.id),
        "updated_at": existing_auth.updated_at.isoformat()
    })


@router.delete("/authorizations/{authorization_id}")
async def revoke_pickup_authorization(
    authorization_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("dismissal.write"))
):
    """Revoke a pickup authorization"""
    from app.domain.entities.pickup import PickupAuthorization
    
    result = await db.execute(
        select(PickupAuthorization).where(PickupAuthorization.id == authorization_id)
    )
    auth = result.scalar_one_or_none()
    
    if not auth:
        raise HTTPException(status_code=404, detail="Authorization not found")
    student = await lock_student(db, auth.student_id)
    await db.refresh(auth)
    
    if auth.status != "REVOKED":
        auth.status = "REVOKED"
        service.audit(db, tenant, student, auth, "PICKUP_AUTHORIZATION_REVOKED", {"status": "REVOKED"})
    
    await db.commit()
    
    return success_response({
        "id": str(auth.id),
        "status": "REVOKED",
        "message": "Authorization revoked successfully"
    })


# ==================== Pickup Verification Endpoints ====================

@router.post("/verify-pickup")
async def verify_pickup(
    request: PickupVerificationRequest,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("dismissal.write"))
):
    """Check registered identity and persist the authenticated operator."""
    from app.domain.entities.pickup import PickupAuthorization, PickupLog
    await lock_student(db, request.student_id)
    student = (await db.execute(select(Student).where(Student.id == request.student_id))).scalar_one()

    def recorded(log, repeated=False):
        if log.student_id != request.student_id or log.pickup_person_id != request.pickup_person_id or log.verified_by != tenant.user_id:
            raise ConflictException("İstek kimliği farklı bir teslim için kullanılmış")
        return success_response({"authorized": True, "message": "Teslim kaydı doğrulandı", "student_id": str(log.student_id),
            "student_name": f"{student.first_name} {student.last_name}",
            "pickup_person_name": log.pickup_person_name, "authorization_id": str(log.authorization_id) if log.authorization_id else None,
            "pickup_log_id": str(log.id), "pickup_time": utc_iso(log.pickup_time), "repeated_request": repeated})

    previous = (await db.execute(select(PickupLog).where(PickupLog.id == request.request_id))).scalar_one_or_none()
    if previous:
        return recorded(previous, True)
    if student.status != "ACTIVE":
        raise HTTPException(409, "Teslim kaydı yalnız aktif öğrenci için tutulabilir")
    today = school_today()
    authorizations = (await db.execute(select(PickupAuthorization).where(PickupAuthorization.student_id == request.student_id,
        PickupAuthorization.authorized_person_id == request.pickup_person_id, PickupAuthorization.status == "ACTIVE",
        PickupAuthorization.valid_from <= today,
        (PickupAuthorization.valid_until.is_(None)) | (PickupAuthorization.valid_until >= today)))).scalars().all()
    if not authorizations:
        return success_response({"authorized": False, "message": "Geçerli teslim yetkisiyle kimlik bilgisi eşleşmedi",
            "student_id": str(request.student_id), "authorization_id": None, "pickup_log_id": None})
    if len(authorizations) > 1:
        raise ConflictException("Aynı kişi için birden fazla etkin yetki var; kayıtlar incelenmeli")
    authorization = authorizations[0]
    log = PickupLog(id=request.request_id, student_id=request.student_id, authorization_id=authorization.id,
        pickup_person_name=authorization.authorized_person_name, pickup_person_id=authorization.authorized_person_id,
        verified_by=tenant.user_id, verification_method="ID_CARD")
    db.add(log)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        previous = (await db.execute(select(PickupLog).where(PickupLog.id == request.request_id))).scalar_one_or_none()
        if previous:
            return recorded(previous, True)
        if (await db.execute(select(PickupLog.__table__.c.id).where(PickupLog.__table__.c.id == request.request_id))).first():
            raise ConflictException("İstek kimliği kullanılamıyor; yeni kimlik üretin")
        raise
    await db.refresh(log)
    return recorded(log)


# ==================== Pickup Logs Endpoints ====================

@router.get("/logs")
async def get_pickup_logs(
    student_id: Optional[UUID] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("dismissal.read"))
):
    """Get pickup logs with filtering"""
    from app.domain.entities.pickup import PickupLog
    
    query = select(PickupLog)
    if start_date and end_date and end_date < start_date:
        raise HTTPException(422, "Bitiş tarihi başlangıçtan önce olamaz")
    
    conditions = []
    if student_id:
        conditions.append(PickupLog.student_id == student_id)
    if start_date:
        conditions.append(PickupLog.pickup_time >= school_day_bounds(start_date)[0])
    if end_date:
        conditions.append(PickupLog.pickup_time < school_day_bounds(end_date)[1])
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(PickupLog.pickup_time.desc(), PickupLog.id).limit(limit).offset(offset)
    
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
        
        # Get verified by name
        verified_by_name = None
        if log.verified_by:
            user_result = await db.execute(
                select(User).where(User.id == log.verified_by)
            )
            user = user_result.scalar_one_or_none()
            if user:
                verified_by_name = f"{user.first_name} {user.last_name}"
        
        enriched_logs.append({
            "id": str(log.id),
            "student_id": str(log.student_id),
            "student_name": student_name,
            "authorization_id": str(log.authorization_id) if log.authorization_id else None,
            "pickup_person_name": log.pickup_person_name,
            "pickup_person_id": log.pickup_person_id,
            "verified_by": str(log.verified_by) if log.verified_by else None,
            "verified_by_name": verified_by_name,
            "pickup_time": utc_iso(log.pickup_time),
            "verification_method": log.verification_method,
            "notes": log.notes,
            "created_at": utc_iso(log.created_at)
        })
    
    return success_response(enriched_logs)


@router.get("/students/{student_id}/authorizations")
async def get_student_pickup_authorizations(
    student_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("dismissal.read"))
):
    """Get all active pickup authorizations for a student"""
    from app.domain.entities.pickup import PickupAuthorization
    
    today = school_today()
    result = await db.execute(
        select(PickupAuthorization).where(
            and_(
                PickupAuthorization.student_id == student_id,
                PickupAuthorization.status == "ACTIVE",
                PickupAuthorization.valid_from <= today,
                (PickupAuthorization.valid_until.is_(None)) | (PickupAuthorization.valid_until >= today)
            )
        )
    )
    authorizations = result.scalars().all()
    
    enriched_authorizations = []
    for auth in authorizations:
        enriched_authorizations.append({
            "id": str(auth.id),
            "authorized_person_name": auth.authorized_person_name,
            "authorized_person_id": auth.authorized_person_id,
            "relationship": auth.relationship,
            "photo_url": auth.photo_url,
            "phone": auth.phone,
            "valid_from": auth.valid_from.isoformat(),
            "valid_until": auth.valid_until.isoformat() if auth.valid_until else None
        })
    
    return success_response(enriched_authorizations)


@router.get("/today-pickups")
async def get_today_pickups(
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("dismissal.read"))
):
    """Get today's pickup summary"""
    from app.domain.entities.pickup import PickupLog
    
    today = school_today()
    start_of_day, end_of_day = school_day_bounds(today)
    
    # Get today's pickup logs
    result = await db.execute(
        select(PickupLog).where(
            and_(
                PickupLog.pickup_time >= start_of_day,
                PickupLog.pickup_time < end_of_day
            )
        )
    )
    logs = result.scalars().all()
    
    # Count pickups
    total_pickups = len(logs)
    
    # Get unique students picked up
    unique_students = set(log.student_id for log in logs)
    unique_student_count = len(unique_students)
    
    return success_response({
        "date": today.isoformat(),
        "total_pickups": total_pickups,
        "unique_students": unique_student_count,
        "pickup_time_range": {
            "first": utc_iso(min(log.pickup_time for log in logs)) if logs else None,
            "last": utc_iso(max(log.pickup_time for log in logs)) if logs else None
        }
    })
