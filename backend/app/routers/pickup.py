"""
Student Pickup/Dismissal Desk Module API
Handles pickup authorizations and pickup logs
"""
from datetime import datetime, date
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

router = APIRouter(prefix="/api/dismissal", tags=["Dismissal"])


# ==================== Schemas ====================

class PickupAuthorizationCreate(BaseModel):
    student_id: UUID
    authorized_person_name: str = Field(..., max_length=255)
    authorized_person_id: Optional[str] = Field(None, max_length=50)
    relationship: Optional[str] = Field(None, max_length=100)
    photo_url: Optional[str] = None
    phone: Optional[str] = Field(None, max_length=20)
    valid_from: date = Field(..., description="Valid from date")
    valid_until: Optional[date] = None
    notes: Optional[str] = None

class PickupLogCreate(BaseModel):
    student_id: UUID
    authorization_id: Optional[UUID] = None
    pickup_person_name: str = Field(..., max_length=255)
    pickup_person_id: Optional[str] = Field(None, max_length=50)
    verified_by: UUID
    verification_method: str = Field(default="ID_CARD", description="ID_CARD, QR_CODE, FACE_RECOGNITION")
    notes: Optional[str] = None

class PickupVerificationRequest(BaseModel):
    student_id: UUID
    pickup_person_id: Optional[str] = Field(None, max_length=50)
    pickup_person_name: str = Field(..., max_length=255)


# ==================== Pickup Authorizations Endpoints ====================

@router.get("/authorizations")
async def get_pickup_authorizations(
    student_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
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
    
    query = query.order_by(PickupAuthorization.valid_from.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    authorizations = result.scalars().all()
    
    enriched_authorizations = []
    for auth in authorizations:
        # Get student name
        student_name = None
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
            "created_by_name": created_by_name
        })
    
    return success_response(enriched_authorizations)


@router.post("/authorizations")
async def create_pickup_authorization(
    authorization: PickupAuthorizationCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("dismissal.write"))
):
    """Create a new pickup authorization"""
    from app.domain.entities.pickup import PickupAuthorization
    
    new_authorization = PickupAuthorization(
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
        created_by=None  # Will be set from current user context
    )
    db.add(new_authorization)
    await db.commit()
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
    db: AsyncSession = Depends(get_db),
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
    
    existing_auth.authorized_person_name = authorization.authorized_person_name
    existing_auth.authorized_person_id = authorization.authorized_person_id
    existing_auth.relationship = authorization.relationship
    existing_auth.photo_url = authorization.photo_url
    existing_auth.phone = authorization.phone
    existing_auth.valid_from = authorization.valid_from
    existing_auth.valid_until = authorization.valid_until
    existing_auth.notes = authorization.notes
    
    await db.commit()
    
    return success_response({
        "id": str(existing_auth.id),
        "updated_at": existing_auth.updated_at.isoformat()
    })


@router.delete("/authorizations/{authorization_id}")
async def revoke_pickup_authorization(
    authorization_id: UUID,
    db: AsyncSession = Depends(get_db),
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
    
    auth.status = "REVOKED"
    
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
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("dismissal.write"))
):
    """Verify pickup authorization and create pickup log"""
    from app.domain.entities.pickup import PickupAuthorization, PickupLog
    
    # Get active authorizations for the student
    today = date.today()
    result = await db.execute(
        select(PickupAuthorization).where(
            and_(
                PickupAuthorization.student_id == request.student_id,
                PickupAuthorization.status == "ACTIVE",
                PickupAuthorization.valid_from <= today,
                (PickupAuthorization.valid_until.is_(None)) | (PickupAuthorization.valid_until >= today)
            )
        )
    )
    authorizations = result.scalars().all()
    
    # Check if the pickup person is authorized
    authorized = False
    matched_authorization = None
    
    for auth in authorizations:
        if request.pickup_person_id and auth.authorized_person_id == request.pickup_person_id:
            authorized = True
            matched_authorization = auth
            break
        # Also check by name (less secure but fallback)
        if auth.authorized_person_name.lower() == request.pickup_person_name.lower():
            authorized = True
            matched_authorization = auth
            break
    
    if not authorized:
        return success_response({
            "authorized": False,
            "message": "Pickup person is not authorized",
            "student_id": str(request.student_id),
            "pickup_person_name": request.pickup_person_name,
            "authorization_id": None,
            "pickup_log_id": None
        })
    
    # Create pickup log
    new_log = PickupLog(
        student_id=request.student_id,
        authorization_id=matched_authorization.id if matched_authorization else None,
        pickup_person_name=request.pickup_person_name,
        pickup_person_id=request.pickup_person_id,
        verified_by=None,  # Will be set from current user context
        verification_method="ID_CARD",
        notes=None
    )
    db.add(new_log)
    await db.commit()
    await db.refresh(new_log)
    
    # Get student name
    student_result = await db.execute(
        select(Student).where(Student.id == request.student_id)
    )
    student = student_result.scalar_one_or_none()
    student_name = f"{student.first_name} {student.last_name}" if student else None
    
    return success_response({
        "authorized": True,
        "message": "Pickup verified successfully",
        "student_id": str(request.student_id),
        "student_name": student_name,
        "pickup_person_name": request.pickup_person_name,
        "authorization_id": str(matched_authorization.id) if matched_authorization else None,
        "pickup_log_id": str(new_log.id),
        "pickup_time": new_log.pickup_time.isoformat()
    })


# ==================== Pickup Logs Endpoints ====================

@router.get("/logs")
async def get_pickup_logs(
    student_id: Optional[UUID] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("dismissal.read"))
):
    """Get pickup logs with filtering"""
    from app.domain.entities.pickup import PickupLog
    
    query = select(PickupLog)
    
    conditions = []
    if student_id:
        conditions.append(PickupLog.student_id == student_id)
    if start_date:
        conditions.append(PickupLog.pickup_time >= start_date)
    if end_date:
        conditions.append(PickupLog.pickup_time <= end_date.replace(hour=23, minute=59, second=59))
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(PickupLog.pickup_time.desc()).limit(limit).offset(offset)
    
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
            "pickup_time": log.pickup_time.isoformat(),
            "verification_method": log.verification_method,
            "notes": log.notes,
            "created_at": log.created_at.isoformat()
        })
    
    return success_response(enriched_logs)


@router.get("/students/{student_id}/authorizations")
async def get_student_pickup_authorizations(
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("dismissal.read"))
):
    """Get all active pickup authorizations for a student"""
    from app.domain.entities.pickup import PickupAuthorization
    
    today = date.today()
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
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("dismissal.read"))
):
    """Get today's pickup summary"""
    from app.domain.entities.pickup import PickupLog
    
    today = date.today()
    start_of_day = datetime.combine(today, datetime.min.time())
    end_of_day = datetime.combine(today, datetime.max.time())
    
    # Get today's pickup logs
    result = await db.execute(
        select(PickupLog).where(
            and_(
                PickupLog.pickup_time >= start_of_day,
                PickupLog.pickup_time <= end_of_day
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
            "first": min(log.pickup_time for log in logs).isoformat() if logs else None,
            "last": max(log.pickup_time for log in logs).isoformat() if logs else None
        }
    })
