"""
Security Module - Digital ID & Gate Validator API
Handles QR code verification, gate logs, and digital ID management
"""
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.responses import success_response
from app.core.security import PermissionChecker, TenantContext
from app.domain.entities import (
    Student, User, Branch
)

router = APIRouter(prefix="/api/security", tags=["Security"])


# ==================== Schemas ====================

class DigitalIdResponse(BaseModel):
    id: UUID
    student_id: UUID
    token: str
    qr_code_url: Optional[str]
    barcode_number: Optional[str]
    status: str
    expires_at: Optional[datetime]
    issued_at: datetime
    last_used_at: Optional[datetime]
    student_name: str
    student_number: Optional[str]
    class_name: Optional[str]
    branch_name: Optional[str]

class QRVerificationRequest(BaseModel):
    token: str = Field(..., description="QR code token to verify")
    direction: str = Field(default="IN", description="IN or OUT")
    gate_location: Optional[str] = Field(None, description="Gate/door location")
    verification_method: str = Field(default="QR", description="QR, BARCODE, or MANUAL")

class QRVerificationResponse(BaseModel):
    authorized: bool
    status: str
    message: str
    student_id: Optional[UUID]
    student_name: Optional[str]
    student_photo: Optional[str]
    parent_pickup_permission: bool
    service_permission: bool
    gate_log_id: Optional[UUID]
    timestamp: datetime

class GateLogResponse(BaseModel):
    id: UUID
    student_id: Optional[UUID]
    student_name: Optional[str]
    user_id: Optional[UUID]
    user_name: Optional[str]
    branch_id: Optional[UUID]
    branch_name: Optional[str]
    direction: str
    status: str
    gate_location: Optional[str]
    verified_by: Optional[UUID]
    verified_by_name: Optional[str]
    verification_method: str
    parent_pickup_permission: bool
    service_permission: bool
    notes: Optional[str]
    created_at: datetime

class GateStatsResponse(BaseModel):
    total_entries: int
    total_exits: int
    currently_in_school: int
    date: str
    by_status: dict

class GenerateTokenRequest(BaseModel):
    student_id: UUID
    expires_hours: Optional[int] = Field(default=24, description="Token validity in hours")


# ==================== Digital ID Endpoints ====================

@router.get("/digital-id/{student_id}")
async def get_digital_id(
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("student.read"))
):
    """Get or generate digital ID token for a student"""
    # Check if student exists
    student_result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = student_result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Try to get existing active token
    token_result = await db.execute(
        select(DigitalIdToken).where(
            and_(
                DigitalIdToken.student_id == student_id,
                DigitalIdToken.status == "ACTIVE",
                or_(
                    DigitalIdToken.expires_at.is_(None),
                    DigitalIdToken.expires_at > datetime.utcnow()
                )
            )
        ).order_by(DigitalIdToken.issued_at.desc())
    )
    token = token_result.scalar_one_or_none()
    
    # Generate new token if none exists
    if not token:
        token = DigitalIdToken(
            student_id=student_id,
            token=str(uuid4()),
            barcode_number=generate_barcode_number(),
            status="ACTIVE",
            expires_at=datetime.utcnow() + timedelta(hours=24),
            issued_at=datetime.utcnow()
        )
        db.add(token)
        await db.commit()
        await db.refresh(token)
    
    # Get student details
    class_name = None
    branch_name = None
    if student.class_id:
        # Get class name (simplified - in real app would join with classes table)
        class_name = str(student.class_id) if student.class_id else None
    
    return success_response({
        "id": str(token.id),
        "student_id": str(token.student_id),
        "token": token.token,
        "qr_code_url": f"/api/security/qr-code/{token.token}",
        "barcode_number": token.barcode_number,
        "status": token.status,
        "expires_at": token.expires_at.isoformat() if token.expires_at else None,
        "issued_at": token.issued_at.isoformat(),
        "last_used_at": token.last_used_at.isoformat() if token.last_used_at else None,
        "student_name": f"{student.first_name} {student.last_name}",
        "student_number": student.student_number,
        "class_name": class_name,
        "branch_name": branch_name
    })


@router.post("/digital-id/generate")
async def generate_digital_id(
    request: GenerateTokenRequest,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("student.write"))
):
    """Generate new digital ID token for a student"""
    # Check if student exists
    student_result = await db.execute(
        select(Student).where(Student.id == request.student_id)
    )
    student = student_result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Revoke existing tokens
    await db.execute(
        select(DigitalIdToken).where(
            and_(
                DigitalIdToken.student_id == request.student_id,
                DigitalIdToken.status == "ACTIVE"
            )
        )
    )
    existing_tokens = await db.execute(
        select(DigitalIdToken).where(
            and_(
                DigitalIdToken.student_id == request.student_id,
                DigitalIdToken.status == "ACTIVE"
            )
        )
    )
    for existing_token in existing_tokens.scalars():
        existing_token.status = "REVOKED"
    
    # Generate new token
    new_token = DigitalIdToken(
        student_id=request.student_id,
        token=str(uuid4()),
        barcode_number=generate_barcode_number(),
        status="ACTIVE",
        expires_at=datetime.utcnow() + timedelta(hours=request.expires_hours),
        issued_at=datetime.utcnow()
    )
    db.add(new_token)
    await db.commit()
    await db.refresh(new_token)
    
    return success_response({
        "id": str(new_token.id),
        "token": new_token.token,
        "qr_code_url": f"/api/security/qr-code/{new_token.token}",
        "barcode_number": new_token.barcode_number,
        "expires_at": new_token.expires_at.isoformat() if new_token.expires_at else None
    })


# ==================== Gate Verification Endpoints ====================

@router.post("/gate-logs/verify-qr")
async def verify_qr_code(
    request: QRVerificationRequest,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("security.write"))
):
    """Verify QR code and create gate log"""
    # Find token
    token_result = await db.execute(
        select(DigitalIdToken).where(
            and_(
                DigitalIdToken.token == request.token,
                DigitalIdToken.status == "ACTIVE",
                or_(
                    DigitalIdToken.expires_at.is_(None),
                    DigitalIdToken.expires_at > datetime.utcnow()
                )
            )
        )
    )
    token = token_result.scalar_one_or_none()
    
    if not token:
        return success_response({
            "authorized": False,
            "status": "UNAUTHORIZED",
            "message": "Invalid or expired QR code",
            "student_id": None,
            "student_name": None,
            "student_photo": None,
            "parent_pickup_permission": False,
            "service_permission": False,
            "gate_log_id": None,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    # Get student details
    student_result = await db.execute(
        select(Student).where(Student.id == token.student_id)
    )
    student = student_result.scalar_one_or_none()
    
    if not student or student.status != "ACTIVE":
        return success_response({
            "authorized": False,
            "status": "BLOCKED",
            "message": "Student not found or inactive",
            "student_id": None,
            "student_name": None,
            "student_photo": None,
            "parent_pickup_permission": False,
            "service_permission": False,
            "gate_log_id": None,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    # Update token last used
    token.last_used_at = datetime.utcnow()
    
    # Create gate log
    gate_log = GateLog(
        student_id=token.student_id,
        direction=request.direction,
        status="AUTHORIZED",
        gate_location=request.gate_location,
        verification_method=request.verification_method,
        parent_pickup_permission=True,  # Would check from parent settings
        service_permission=True  # Would check from service settings
    )
    db.add(gate_log)
    await db.commit()
    await db.refresh(gate_log)
    
    return success_response({
        "authorized": True,
        "status": "AUTHORIZED",
        "message": f"Gate {request.direction} authorized",
        "student_id": str(student.id),
        "student_name": f"{student.first_name} {student.last_name}",
        "student_photo": student.photo_url if hasattr(student, 'photo_url') else None,
        "parent_pickup_permission": gate_log.parent_pickup_permission,
        "service_permission": gate_log.service_permission,
        "gate_log_id": str(gate_log.id),
        "timestamp": datetime.utcnow().isoformat()
    })


@router.get("/gate-logs")
async def get_gate_logs(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    student_id: Optional[UUID] = Query(None, description="Filter by student"),
    branch_id: Optional[UUID] = Query(None, description="Filter by branch"),
    direction: Optional[str] = Query(None, description="Filter by direction (IN/OUT)"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("security.read"))
):
    """Get gate logs with filtering"""
    query = select(GateLog)
    
    # Apply filters
    conditions = []
    if start_date:
        conditions.append(GateLog.created_at >= datetime.strptime(start_date, "%Y-%m-%d"))
    if end_date:
        conditions.append(GateLog.created_at <= datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59))
    if student_id:
        conditions.append(GateLog.student_id == student_id)
    if branch_id:
        conditions.append(GateLog.branch_id == branch_id)
    if direction:
        conditions.append(GateLog.direction == direction)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(GateLog.created_at.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    # Enrich with student/user names
    enriched_logs = []
    for log in logs:
        log_data = {
            "id": str(log.id),
            "student_id": str(log.student_id) if log.student_id else None,
            "student_name": None,
            "user_id": str(log.user_id) if log.user_id else None,
            "user_name": None,
            "branch_id": str(log.branch_id) if log.branch_id else None,
            "branch_name": None,
            "direction": log.direction,
            "status": log.status,
            "gate_location": log.gate_location,
            "verified_by": str(log.verified_by) if log.verified_by else None,
            "verified_by_name": None,
            "verification_method": log.verification_method,
            "parent_pickup_permission": log.parent_pickup_permission,
            "service_permission": log.service_permission,
            "notes": log.notes,
            "created_at": log.created_at.isoformat()
        }
        
        # Get student name
        if log.student_id:
            student_result = await db.execute(
                select(Student).where(Student.id == log.student_id)
            )
            student = student_result.scalar_one_or_none()
            if student:
                log_data["student_name"] = f"{student.first_name} {student.last_name}"
        
        # Get user name
        if log.user_id:
            user_result = await db.execute(
                select(User).where(User.id == log.user_id)
            )
            user = user_result.scalar_one_or_none()
            if user:
                log_data["user_name"] = f"{user.first_name} {user.last_name}"
        
        enriched_logs.append(log_data)
    
    return success_response(enriched_logs)


@router.get("/gate-logs/stats")
async def get_gate_stats(
    date: Optional[str] = Query(None, description="Date (YYYY-MM-DD), defaults to today"),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("security.read"))
):
    """Get gate statistics for a specific date"""
    if not date:
        date = datetime.utcnow().strftime("%Y-%m-%d")
    
    start_datetime = datetime.strptime(date, "%Y-%m-%d")
    end_datetime = start_datetime.replace(hour=23, minute=59, second=59)
    
    # Get logs for the date
    result = await db.execute(
        select(GateLog).where(
            and_(
                GateLog.created_at >= start_datetime,
                GateLog.created_at <= end_datetime,
                GateLog.status == "AUTHORIZED"
            )
        )
    )
    logs = result.scalars().all()
    
    # Calculate stats
    entries = sum(1 for log in logs if log.direction == "IN")
    exits = sum(1 for log in logs if log.direction == "OUT")
    
    # Calculate currently in school (entries - exits)
    currently_in_school = max(0, entries - exits)
    
    # Count by status
    status_counts = {}
    for log in logs:
        status_counts[log.status] = status_counts.get(log.status, 0) + 1
    
    return success_response({
        "total_entries": entries,
        "total_exits": exits,
        "currently_in_school": currently_in_school,
        "date": date,
        "by_status": status_counts
    })


# ==================== Helper Functions ====================

def generate_barcode_number() -> str:
    """Generate a unique barcode number"""
    import random
    return f"OK{random.randint(100000, 999999)}"
