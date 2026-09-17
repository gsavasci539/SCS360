from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime
from uuid import UUID

from app.infrastructure.models.models import Device


class DeviceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        name: str,
        device_type: str,
        serial_number: str,
        organization_id: Optional[str] = None,
        branch_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        location: Optional[str] = None,
        status: str = "ACTIVE",
        notes: Optional[str] = None
    ) -> Device:
        """Create a new device"""
        device = Device(
            name=name,
            device_type=device_type,
            serial_number=serial_number,
            organization_id=organization_id,
            branch_id=branch_id,
            ip_address=ip_address,
            location=location,
            status=status,
            notes=notes,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        self.db.add(device)
        await self.db.flush()
        return device

    async def get_by_id(self, device_id: str) -> Optional[Device]:
        """Get device by ID"""
        result = await self.db.execute(select(Device).where(Device.id == device_id))
        return result.scalar_one_or_none()

    async def get_by_serial_number(self, serial_number: str, organization_id: Optional[str] = None) -> Optional[Device]:
        """Get device by serial number"""
        query = select(Device).where(Device.serial_number == serial_number)
        if organization_id:
            query = query.where(Device.organization_id == organization_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_all(self, organization_id: Optional[str] = None, branch_id: Optional[str] = None) -> List[Device]:
        """List all devices with optional filters"""
        query = select(Device)
        conditions = []
        
        if organization_id:
            conditions.append(Device.organization_id == organization_id)
        if branch_id:
            conditions.append(Device.branch_id == branch_id)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update(
        self,
        device_id: str,
        name: Optional[str] = None,
        device_type: Optional[str] = None,
        serial_number: Optional[str] = None,
        ip_address: Optional[str] = None,
        location: Optional[str] = None,
        status: Optional[str] = None,
        last_heartbeat: Optional[datetime] = None,
        notes: Optional[str] = None
    ) -> Optional[Device]:
        """Update device"""
        device = await self.get_by_id(device_id)
        if not device:
            return None
        
        if name is not None:
            device.name = name
        if device_type is not None:
            device.device_type = device_type
        if serial_number is not None:
            device.serial_number = serial_number
        if ip_address is not None:
            device.ip_address = ip_address
        if location is not None:
            device.location = location
        if status is not None:
            device.status = status
        if last_heartbeat is not None:
            device.last_heartbeat = last_heartbeat
        if notes is not None:
            device.notes = notes
        
        await self.db.flush()
        return device

    async def delete(self, device_id: str) -> bool:
        """Delete device"""
        device = await self.get_by_id(device_id)
        if not device:
            return False
        
        await self.db.delete(device)
        await self.db.flush()
        return True

    async def serial_number_exists(self, serial_number: str, organization_id: Optional[str] = None, exclude_id: Optional[str] = None) -> bool:
        """Check if serial number already exists"""
        query = select(Device).where(Device.serial_number == serial_number)
        if organization_id:
            query = query.where(Device.organization_id == organization_id)
        if exclude_id:
            query = query.where(Device.id != exclude_id)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None

    async def update_status(self, device_id: str, status: str) -> Optional[Device]:
        """Update device status"""
        return await self.update(device_id, status=status)

    async def update_heartbeat(self, device_id: str, heartbeat: datetime) -> Optional[Device]:
        """Update device last heartbeat"""
        return await self.update(device_id, last_heartbeat=heartbeat)
