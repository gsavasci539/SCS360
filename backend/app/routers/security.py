"""Permission-scoped digital credentials and factual gate events."""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services import security_service as service
from app.core.database import get_db
from app.core.dates import school_day_bounds, school_today
from app.core.permissions import PermissionChecker
from app.core.responses import success_response
from app.core.tenant import TenantContext
from app.domain.entities.security import DigitalIdToken, GateLog
from app.infrastructure.models.models import Branch, Student
from app.infrastructure.repositories.base import BaseRepository

router = APIRouter(prefix="/api/security", tags=["Security"])


async def check_branch(db, tenant, branch_id):
    if branch_id is not None:
        await BaseRepository(db, tenant).get_by_id(branch_id, Branch)


def check_student_branch(student, branch_id):
    if branch_id is not None and student.branch_id != branch_id:
        raise HTTPException(404, "Öğrenci seçili şubede bulunamadı")


class GenerateTokenRequest(BaseModel):
    student_id: UUID
    expires_hours: int = Field(24, ge=1, le=8760)
    request_id: UUID = Field(default_factory=uuid4, description="Aynı kimlik oluşturma işleminin tekrarında aynı UUID")


class QRVerificationRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    token: str = Field(min_length=1, max_length=255)
    direction: Literal["IN", "OUT"] = "IN"
    gate_location: str | None = Field(None, max_length=100)
    verification_method: Literal["QR", "BARCODE", "MANUAL"] = "QR"
    notes: str | None = Field(None, max_length=1000)
    request_id: UUID = Field(default_factory=uuid4, description="Aynı geçişin tekrarında aynı UUID")


@router.get("/options")
async def options(student_id: UUID | None = None, branch_id: UUID | None = None, search: str = Query("", max_length=100),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("security.read"))):
    await check_branch(db, tenant, branch_id)
    return success_response(await service.options(db, student_id, search.strip(), branch_id=branch_id))


@router.get("/digital-ids")
async def list_digital_ids(student_id: UUID | None = None, branch_id: UUID | None = None, record_id: UUID | None = None,
    limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db, scope="function"), tenant: TenantContext = Depends(PermissionChecker("security.read"))):
    await check_branch(db, tenant, branch_id)
    query = select(DigitalIdToken, Student).join(Student, Student.id == DigitalIdToken.student_id).where(Student.deleted_at.is_(None))
    if student_id:
        query = query.where(DigitalIdToken.student_id == student_id)
    if branch_id:
        query = query.where(Student.branch_id == branch_id)
    if record_id:
        query = query.where(DigitalIdToken.id == record_id)
    rows = (await db.execute(query.order_by(DigitalIdToken.issued_at.desc(), DigitalIdToken.id).limit(limit).offset(offset))).all()
    return success_response([service.token_data(token, child) for token, child in rows])


@router.get("/digital-id/{student_id}")
async def get_digital_id(student_id: UUID, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("security.read"))):
    child = await service.student(db, student_id)
    return success_response(await service.token_details(db, await service.latest(db, child), child))


@router.post("/digital-id/generate")
async def generate_digital_id(body: GenerateTokenRequest, branch_id: UUID | None = None, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("security.write"))):
    await check_branch(db, tenant, branch_id)
    child = await service.student(db, body.student_id)
    child = await service.lock_student(db, child.id)
    check_student_branch(child, branch_id)
    previous = (await db.execute(select(DigitalIdToken).where(DigitalIdToken.id == body.request_id))).scalar_one_or_none()
    if previous:
        if not service.same_issue(previous, body):
            raise HTTPException(409, "İstek kimliği farklı bir kimlik oluşturma işlemi için kullanılmış")
        return success_response(service.token_data(previous, child))
    collision = (await db.execute(select(DigitalIdToken.__table__.c.id).where(DigitalIdToken.__table__.c.id == body.request_id))).first()
    if collision:
        raise HTTPException(409, "İstek kimliği kullanılamıyor; yeni işlem başlatın")
    if child.status != "ACTIVE":
        raise HTTPException(409, "Kimlik yalnız aktif öğrenci için oluşturulabilir")
    tokens = (await db.execute(select(DigitalIdToken).where(DigitalIdToken.student_id == child.id, DigitalIdToken.status == "ACTIVE"))).scalars().all()
    for token in tokens:
        token.status = "REVOKED"
    now = datetime.now(UTC)
    token = DigitalIdToken(id=body.request_id, student_id=child.id, token=str(uuid4()), barcode_number=generate_barcode_number(),
        status="ACTIVE", issued_at=now, expires_at=now + timedelta(hours=body.expires_hours))
    db.add(token)
    service.audit(db, tenant, child, token.id, "STUDENT_ID_ISSUED", {"expires_hours": body.expires_hours, "previous_active_ids": len(tokens)})
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        child = await service.student(db, body.student_id)
        previous = (await db.execute(select(DigitalIdToken).where(DigitalIdToken.id == body.request_id))).scalar_one_or_none()
        if previous and service.same_issue(previous, body):
            return success_response(service.token_data(previous, child))
        collision = (await db.execute(select(DigitalIdToken.__table__.c.id).where(DigitalIdToken.__table__.c.id == body.request_id))).first()
        if collision:
            raise HTTPException(409, "İstek kimliği farklı bir kimlik oluşturma işlemi için kullanılmış")
        raise
    await db.refresh(token)
    return success_response(service.token_data(token, child))


@router.post("/digital-ids/{token_id}/revoke")
async def revoke_digital_id(token_id: UUID, branch_id: UUID | None = None, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("security.write"))):
    await check_branch(db, tenant, branch_id)
    token = (await db.execute(select(DigitalIdToken).where(DigitalIdToken.id == token_id))).scalar_one_or_none()
    if token is None:
        raise HTTPException(404, "Kimlik bulunamadı veya erişim kapsamı dışında")
    child = await service.student(db, token.student_id)
    child = await service.lock_student(db, child.id)
    check_student_branch(child, branch_id)
    await db.refresh(token)
    if token.status != "REVOKED":
        token.status = "REVOKED"
        service.audit(db, tenant, child, token.id, "STUDENT_ID_REVOKED", {"status": "REVOKED"})
    await db.commit()
    return success_response(service.token_data(token, child))


@router.get("/digital-ids/{token_id}/qr-code")
async def qr_code(token_id: UUID, branch_id: UUID | None = None, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("security.read"))):
    await check_branch(db, tenant, branch_id)
    token = (await db.execute(select(DigitalIdToken).where(DigitalIdToken.id == token_id))).scalar_one_or_none()
    if token is None:
        raise HTTPException(404, "Kimlik bulunamadı veya erişim kapsamı dışında")
    child = await service.student(db, token.student_id)
    check_student_branch(child, branch_id)
    if not service.active(token) or child.status != "ACTIVE":
        raise HTTPException(409, "Etkin kimlik için QR indirilebilir")
    from reportlab.graphics import renderSVG
    from reportlab.graphics.barcode.qr import QrCodeWidget
    from reportlab.graphics.shapes import Drawing
    widget = QrCodeWidget(token.token)
    x0, y0, x1, y1 = widget.getBounds()
    drawing = Drawing(256, 256, transform=[256 / (x1 - x0), 0, 0, 256 / (y1 - y0), 0, 0])
    drawing.add(widget)
    return Response(renderSVG.drawToString(drawing), media_type="image/svg+xml", headers={"Cache-Control": "private, no-store",
        "Content-Disposition": f'attachment; filename="SCS360-kimlik-{token.student_id}.svg"', "X-Content-Type-Options": "nosniff"})


@router.post("/gate-logs/verify-qr")
async def verify_qr_code(body: QRVerificationRequest, branch_id: UUID | None = None, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("security.write"))):
    await check_branch(db, tenant, branch_id)
    column = DigitalIdToken.barcode_number if body.verification_method == "BARCODE" else DigitalIdToken.token
    token = (await db.execute(select(DigitalIdToken).where(column == body.token))).scalar_one_or_none()
    if token is None:
        return success_response(service.unauthorized())
    child = await service.student(db, token.student_id)
    child = await service.lock_student(db, child.id)
    if branch_id is not None and child.branch_id != branch_id:
        return success_response(service.unauthorized())
    await db.refresh(token)
    previous = await service.replay(db, tenant, child, token, body)
    if previous:
        return success_response(previous)
    if not service.active(token) or child.status != "ACTIVE":
        return success_response(service.unauthorized())
    now = datetime.now(UTC)
    token.last_used_at = now
    log = GateLog(id=body.request_id, student_id=child.id, branch_id=child.branch_id, verified_by=tenant.user_id,
        direction=body.direction, gate_location=body.gate_location, verification_method=body.verification_method, status="AUTHORIZED",
        parent_pickup_permission=False, service_permission=False, notes=body.notes, created_at=now)
    db.add(log)
    service.audit(db, tenant, child, log.id, "STUDENT_GATE_VERIFIED", {"token_id": str(token.id), "request_sha256": service.fingerprint(tenant, token, body)})
    child_identifier, token_identifier = child.id, token.id
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        # Rollback expires ORM instances, including primary keys. Reload before
        # constructing the retry acknowledgement or inspecting the collision.
        child = await service.student(db, child_identifier)
        token = (await db.execute(select(DigitalIdToken).where(DigitalIdToken.id == token_identifier))).scalar_one_or_none()
        if token is None:
            raise HTTPException(409, "Kimlik değişmiş; yeni işlem başlatın")
        previous = await service.replay(db, tenant, child, token, body)
        if previous:
            return success_response(previous)
        raise
    await db.refresh(log)
    return success_response(service.recorded(log, child))


@router.get("/gate-logs")
async def get_gate_logs(start_date: date | None = None, end_date: date | None = None, student_id: UUID | None = None,
    branch_id: UUID | None = None, record_id: UUID | None = None, direction: Literal["IN", "OUT"] | None = None,
    limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db, scope="function"), tenant: TenantContext = Depends(PermissionChecker("security.read"))):
    await check_branch(db, tenant, branch_id)
    if start_date and end_date and end_date < start_date:
        raise HTTPException(422, "Bitiş tarihi başlangıçtan önce olamaz")
    query = select(GateLog)
    for value, condition in ((student_id, GateLog.student_id == student_id), (branch_id, GateLog.branch_id == branch_id), (record_id, GateLog.id == record_id),
        (direction, GateLog.direction == direction), (start_date, GateLog.created_at >= school_day_bounds(start_date)[0] if start_date else True),
        (end_date, GateLog.created_at < school_day_bounds(end_date)[1] if end_date else True)):
        if value is not None:
            query = query.where(condition)
    logs = (await db.execute(query.order_by(GateLog.created_at.desc(), GateLog.id).limit(limit).offset(offset))).scalars().all()
    return success_response(await service.logs_data(db, logs))


@router.get("/gate-logs/stats")
async def get_gate_stats(day: date | None = Query(None, alias="date"), student_id: UUID | None = None, branch_id: UUID | None = None,
    db: AsyncSession = Depends(get_db, scope="function"), tenant: TenantContext = Depends(PermissionChecker("security.read"))):
    await check_branch(db, tenant, branch_id)
    return success_response(await service.stats(db, tenant, day or school_today(), student_id, branch_id=branch_id))


def generate_barcode_number():
    return "SCS360" + uuid4().hex.upper()
