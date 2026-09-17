from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.permissions import PermissionChecker
from app.core.responses import success_response
from app.domain.entities.user import User
from app.core.tenant import TenantContext
from app.repositories.device_repository import DeviceRepository
from app.infrastructure.models.models import Device

router = APIRouter(prefix="/api/devices", tags=["Devices"])


class DeviceCreate(BaseModel):
    name: str = Field(..., description="Cihaz adı")
    device_type: str = Field(..., description="Cihaz tipi: TURNSTILE, CARD_READER, DOOR_LOCK, ATTENDANCE_KIOSK, CANTEEN_TERMINAL")
    serial_number: str = Field(..., description="Seri numarası")
    ip_address: Optional[str] = Field(None, description="IP adresi")
    location: Optional[str] = Field(None, description="Konum")
    notes: Optional[str] = Field(None, description="Notlar")


class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    device_type: Optional[str] = None
    serial_number: Optional[str] = None
    ip_address: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


def device_to_dict(device: Device) -> dict:
    """Convert device to dictionary"""
    return {
        "id": device.id,
        "organization_id": device.organization_id,
        "branch_id": device.branch_id,
        "name": device.name,
        "device_type": device.device_type,
        "serial_number": device.serial_number,
        "ip_address": device.ip_address,
        "location": device.location,
        "status": device.status,
        "last_heartbeat": device.last_heartbeat.isoformat() if device.last_heartbeat else None,
        "notes": device.notes,
        "created_at": device.created_at.isoformat() if device.created_at else None,
        "updated_at": device.updated_at.isoformat() if device.updated_at else None,
    }


@router.get("")
async def list_devices(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("settings.read"))
):
    """List all devices"""
    repo = DeviceRepository(db)
    
    # Get organization and branch IDs from tenant context
    org_id = str(tenant.organization_id) if tenant.organization_id else None
    branch_id = str(tenant.branch_ids[0]) if tenant.branch_ids else None
    
    devices = await repo.list_all(organization_id=org_id, branch_id=branch_id)
    return success_response([device_to_dict(device) for device in devices], "Cihazlar listelendi")


@router.get("/{device_id}")
async def get_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("settings.read"))
):
    """Get a specific device by ID"""
    repo = DeviceRepository(db)
    device = await repo.get_by_id(device_id)
    
    if not device:
        raise HTTPException(status_code=404, detail="Cihaz bulunamadı")
    return success_response(device_to_dict(device), "Cihaz bilgileri")


@router.post("")
async def create_device(
    device: DeviceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("settings.write"))
):
    """Create a new device"""
    repo = DeviceRepository(db)
    
    # Get organization and branch IDs from tenant context
    org_id = str(tenant.organization_id) if tenant.organization_id else None
    branch_id = str(tenant.branch_ids[0]) if tenant.branch_ids else None
    
    # Check if serial number already exists
    if await repo.serial_number_exists(device.serial_number, organization_id=org_id):
        raise HTTPException(status_code=400, detail="Bu seri numarası zaten kullanımda")
    
    # Validate device type
    valid_types = ["TURNSTILE", "CARD_READER", "DOOR_LOCK", "ATTENDANCE_KIOSK", "CANTEEN_TERMINAL"]
    if device.device_type.upper() not in valid_types:
        raise HTTPException(status_code=400, detail=f"Geçersiz cihaz tipi. Geçerli tipler: {', '.join(valid_types)}")
    
    # Create device
    new_device = await repo.create(
        name=device.name,
        device_type=device.device_type.upper(),
        serial_number=device.serial_number,
        organization_id=org_id,
        branch_id=branch_id,
        ip_address=device.ip_address,
        location=device.location,
        status="ACTIVE",
        notes=device.notes
    )
    
    await db.commit()
    return success_response(device_to_dict(new_device), "Cihaz oluşturuldu")


@router.put("/{device_id}")
async def update_device(
    device_id: str,
    device: DeviceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("settings.write"))
):
    """Update a device"""
    repo = DeviceRepository(db)
    
    # Check if device exists
    existing_device = await repo.get_by_id(device_id)
    if not existing_device:
        raise HTTPException(status_code=404, detail="Cihaz bulunamadı")
    
    # Check if serial number already exists (if being updated)
    if device.serial_number and device.serial_number != existing_device.serial_number:
        org_id = str(existing_device.organization_id) if existing_device.organization_id else None
        if await repo.serial_number_exists(device.serial_number, organization_id=org_id, exclude_id=device_id):
            raise HTTPException(status_code=400, detail="Bu seri numarası zaten kullanımda")
    
    # Validate device type (if being updated)
    if device.device_type:
        valid_types = ["TURNSTILE", "CARD_READER", "DOOR_LOCK", "ATTENDANCE_KIOSK", "CANTEEN_TERMINAL"]
        if device.device_type.upper() not in valid_types:
            raise HTTPException(status_code=400, detail=f"Geçersiz cihaz tipi. Geçerli tipler: {', '.join(valid_types)}")
    
    # Update device
    updated_device = await repo.update(
        device_id,
        name=device.name,
        device_type=device.device_type.upper() if device.device_type else None,
        serial_number=device.serial_number,
        ip_address=device.ip_address,
        location=device.location,
        status=device.status,
        notes=device.notes
    )
    
    if not updated_device:
        raise HTTPException(status_code=404, detail="Cihaz bulunamadı")
    
    await db.commit()
    return success_response(device_to_dict(updated_device), "Cihaz güncellendi")


@router.delete("/{device_id}")
async def delete_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("settings.write"))
):
    """Delete a device"""
    repo = DeviceRepository(db)
    
    deleted = await repo.delete(device_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Cihaz bulunamadı")
    
    await db.commit()
    return success_response(message="Cihaz silindi")


@router.patch("/{device_id}/status")
async def update_device_status(
    device_id: str,
    status: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("settings.write"))
):
    """Update device status"""
    repo = DeviceRepository(db)
    
    # Validate status
    valid_statuses = ["ACTIVE", "INACTIVE", "MAINTENANCE", "BROKEN"]
    if status.upper() not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Geçersiz durum. Geçerli durumlar: {', '.join(valid_statuses)}")
    
    updated_device = await repo.update_status(device_id, status.upper())
    if not updated_device:
        raise HTTPException(status_code=404, detail="Cihaz bulunamadı")
    
    await db.commit()
    return success_response(device_to_dict(updated_device), "Cihaz durumu güncellendi")


@router.patch("/{device_id}/heartbeat")
async def update_device_heartbeat(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("settings.write"))
):
    """Update device last heartbeat (for device communication)"""
    repo = DeviceRepository(db)
    
    updated_device = await repo.update_heartbeat(device_id, datetime.now())
    if not updated_device:
        raise HTTPException(status_code=404, detail="Cihaz bulunamadı")
    
    await db.commit()
    return success_response(device_to_dict(updated_device), "Cihaz kalp atışı güncellendi")
