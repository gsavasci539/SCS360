"""
Hardware Device API
Handles communication with RFID readers, turnstiles, and canteen terminals
"""
from __future__ import annotations
from datetime import UTC, datetime, date
from decimal import Decimal
from typing import Optional, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.responses import success_response
from app.core.permissions import PermissionChecker
from app.core.tenant import TenantContext
from app.domain.entities.user import User
from app.infrastructure.models.models import Device, RfidCard

router = APIRouter(prefix="/api/hardware", tags=["Hardware"], dependencies=[Depends(get_current_user)])


# ==================== Schemas ====================

class DeviceRegisterRequest(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=36)
    device_type: Literal["TURNSTILE", "CARD_READER", "DOOR_LOCK", "ATTENDANCE_KIOSK", "CANTEEN_TERMINAL"]
    serial_number: str = Field(..., min_length=1, max_length=100)
    branch_id: UUID
    ip_address: Optional[str] = Field(None, max_length=50)
    location: Optional[str] = Field(None, max_length=255)


class DeviceHeartbeatRequest(BaseModel):
    status: Literal["ONLINE", "OFFLINE", "ERROR"] = "ONLINE"
    ip_address: Optional[str] = Field(None, max_length=50)


class AccessCheckRequest(BaseModel):
    holder_id: UUID
    card_type: Literal["STUDENT", "STAFF"]
    device_id: str = Field(..., min_length=1, max_length=36)


class AccessLogRequest(BaseModel):
    card_number: str = Field(..., min_length=1, max_length=50)
    holder_id: Optional[UUID] = None
    device_id: str = Field(..., min_length=1, max_length=36)
    access_status: Literal["GRANTED", "DENIED"]
    branch_id: UUID


class CardPaymentRequest(BaseModel):
    card_number: str = Field(..., description="RFID card number")
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    branch_id: str = Field(..., description="Branch UUID")
    notes: Optional[str] = None


class CardBalanceCheckRequest(BaseModel):
    card_number: str = Field(..., description="RFID card number")


class WifiCardReadRequest(BaseModel):
    device_id: str = Field(..., description="WiFi RFID device identifier")
    card_number: str = Field(..., description="RFID card number")
    timestamp: Optional[str] = None


# ==================== Device Management Endpoints ====================

@router.post("/devices/register")
async def register_device(
    request: DeviceRegisterRequest, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("settings.write")),
):
    from app.infrastructure.models.models import Branch
    from app.infrastructure.repositories.base import BaseRepository
    from app.application.services.operations_service import identifier
    from app.core.exceptions import ConflictException
    from sqlalchemy.exc import IntegrityError
    branch = await BaseRepository(db, tenant).get_by_id(identifier(request.branch_id), Branch)
    device = (await db.execute(select(Device).where(Device.serial_number == request.serial_number,
        Device.organization_id == str(branch.organization_id)))).scalar_one_or_none()
    if device is not None and device.branch_id != str(branch.id):
        raise ConflictException("Cihaz farklı şubede kayıtlı; şubesini cihaz yönetiminden değiştirin")
    try:
        async with db.begin_nested():
            if device is None:
                device = Device(id=request.device_id, organization_id=str(branch.organization_id),
                    branch_id=str(branch.id), name=f"{request.device_type}_{request.serial_number}",
                    device_type=request.device_type, serial_number=request.serial_number)
                db.add(device)
            device.ip_address, device.location = request.ip_address, request.location
            device.status, device.last_heartbeat = "ACTIVE", datetime.now(UTC).replace(tzinfo=None)
            await db.flush()
    except IntegrityError as exc:
        raise ConflictException("Cihaz kimliği veya seri numarası zaten kullanılıyor") from exc
    return success_response({"device_id": device.id, "status": "registered"})


@router.post("/devices/{device_id}/heartbeat")
async def device_heartbeat(
    device_id: str, request: DeviceHeartbeatRequest, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("settings.write")),
):
    device = (await db.execute(select(Device).where(Device.id == device_id))).scalar_one_or_none()
    if device is None:
        raise HTTPException(status_code=404, detail="Cihaz bulunamadı")
    device.status = {"ONLINE": "ACTIVE", "OFFLINE": "INACTIVE", "ERROR": "BROKEN"}[request.status]
    device.ip_address = request.ip_address
    device.last_heartbeat = datetime.now(UTC).replace(tzinfo=None)
    await db.flush()
    return success_response({"device_id": device_id, "status": device.status})


@router.get("/devices")
async def list_devices(
    branch_id: Optional[str] = Query(None),
    device_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("settings.read"))
):
    """List all hardware devices"""
    query = select(Device)
    
    conditions = []
    if branch_id:
        conditions.append(Device.branch_id == branch_id)
    if device_type:
        conditions.append(Device.device_type == device_type)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    result = await db.execute(query)
    devices = result.scalars().all()
    
    device_list = []
    for device in devices:
        device_list.append({
            "id": device.id,
            "name": device.name,
            "device_type": device.device_type,
            "serial_number": device.serial_number,
            "ip_address": device.ip_address,
            "location": device.location,
            "status": device.status,
            "last_heartbeat": device.last_heartbeat.isoformat() if device.last_heartbeat else None,
            "branch_id": device.branch_id
        })
    
    return success_response(device_list, "Devices listed successfully")


# ==================== Access Control Endpoints ====================

@router.post("/access/check", dependencies=[Depends(PermissionChecker("security.read"))])
async def check_access_permission(
    request: AccessCheckRequest,
    db: AsyncSession = Depends(get_db, scope="function"),
):
    from app.application.services import hardware_access_service
    return success_response(await hardware_access_service.check(db, request.holder_id, request.card_type, request.device_id))


@router.post("/access/log", dependencies=[Depends(PermissionChecker("security.write"))])
async def log_access(
    request: AccessLogRequest,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("security.write")),
):
    """Log access attempt (granted or denied)"""
    # Create access log entry
    from app.infrastructure.models.models import AuditLog, AuditAction
    from app.application.services import hardware_access_service
    device, card = await hardware_access_service.validate_log(db, request)
    
    log_entry = AuditLog(
        organization_id=UUID(device.organization_id),
        branch_id=UUID(device.branch_id),
        user_id=tenant.user_id,
        action=AuditAction.OTHER,
        entity_type="ACCESS_LOG",
        entity_id=UUID(card.holder_id) if card else None,
        old_values=None,
        new_values={
            "card_number": request.card_number,
            "holder_id": str(request.holder_id) if card and request.holder_id else None,
            "device_id": request.device_id,
            "access_status": request.access_status,
            "timestamp": datetime.now(UTC).isoformat()
        },
        ip_address=None,
        user_agent=f"Hardware Device: {request.device_id}"
    )
    
    db.add(log_entry)
    await db.commit()
    
    return success_response({"logged": True}, "Access logged successfully")


# ==================== Card-based Payment Endpoints ====================

@router.post("/payment/process")
async def process_card_payment(
    request: CardPaymentRequest, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("canteen.write")),
):
    from app.application.services import hardware_wallet_service as hardware, canteen_wallet_service as wallets
    from app.application.services.operations_service import identifier
    from app.core.exceptions import ValidationException
    card = await hardware.card(db, tenant, request.card_number)
    if identifier(card.branch_id) != identifier(request.branch_id):
        raise ValidationException("Kart ve işlem şubesi eşleşmiyor")
    result = await wallets.purchase(db, tenant, card.holder_id, price=request.amount, name=request.notes or "RFID kantin satışı")
    return success_response(dict(result, holder_name=card.holder_name))


@router.post("/card/balance")
async def get_card_balance(
    request: CardBalanceCheckRequest, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("canteen.read")),
):
    from app.application.services import hardware_wallet_service as hardware
    return success_response(await hardware.balance(db, tenant, request.card_number))


@router.post("/card/topup")
async def topup_card_balance(
    card_number: str, amount: Decimal = Query(..., gt=0, decimal_places=2),
    payment_method: Literal["CASH", "CARD", "BANK_TRANSFER", "EFT"] = Query(...), reference_number: Optional[str] = None,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("canteen.write")),
):
    from app.application.services import hardware_wallet_service as hardware, canteen_wallet_service as wallets
    card = await hardware.card(db, tenant, card_number)
    result = await wallets.topup(db, tenant, card.holder_id, amount, payment_method, reference_number)
    return success_response(dict(result, card_number=card.card_number, holder_id=card.holder_id, holder_name=card.holder_name))

@router.post("/wifi/card-read")
async def wifi_card_read(
    request: WifiCardReadRequest, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("canteen.read")),
):
    from app.application.services import hardware_wallet_service as hardware
    from app.infrastructure.models.models import OperationalRecord, Student
    from app.core.exceptions import ValidationException
    device = (await db.execute(select(Device).where(Device.id == request.device_id, Device.status == "ACTIVE"))).scalar_one_or_none()
    if device is None:
        raise ValidationException("Aktif ve erişilebilir bir cihaz gerekli")
    result = await hardware.balance(db, tenant, request.card_number)
    card = await hardware.card(db, tenant, request.card_number)
    if device.branch_id != card.branch_id:
        raise ValidationException("Cihaz ve kart aynı şubede olmalı")
    data = dict(result, device_id=device.id, timestamp=datetime.now(UTC).isoformat(), success=True)
    student = (await db.execute(select(Student).where(Student.id == UUID(card.holder_id)))).scalar_one()
    db.add(OperationalRecord(organization_id=tenant.organization_id, branch_id=UUID(card.branch_id),
        class_id=student.class_id, created_by=tenant.user_id, kind="WIFI_CARD_READ", data=data))
    await db.flush()
    return success_response(data)


@router.get("/wifi/card-reads")
async def get_wifi_card_reads(
    device_id: Optional[str] = Query(None), limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("canteen.read")),
):
    from app.infrastructure.models.models import OperationalRecord
    query = select(OperationalRecord).where(OperationalRecord.kind == "WIFI_CARD_READ")
    if device_id:
        query = query.where(OperationalRecord.data["device_id"].as_string() == device_id)
    rows = (await db.execute(query.order_by(OperationalRecord.created_at.desc()).limit(limit))).scalars()
    return success_response([dict(row.data, id=str(row.id)) for row in rows])
