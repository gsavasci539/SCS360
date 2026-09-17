"""
Hardware Device API
Handles communication with RFID readers, turnstiles, and canteen terminals
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.responses import success_response
from app.core.security import PermissionChecker, TenantContext
from app.domain.entities.user import User
from app.infrastructure.models.models import Device, RfidCard

router = APIRouter(prefix="/api/hardware", tags=["Hardware"])


# ==================== Schemas ====================

class DeviceRegisterRequest(BaseModel):
    device_id: str = Field(..., description="Unique device identifier")
    device_type: str = Field(..., description="TURNSTILE, CARD_READER, DOOR_LOCK, ATTENDANCE_KIOSK, CANTEEN_TERMINAL")
    serial_number: str = Field(..., description="Device serial number")
    branch_id: str = Field(..., description="Branch UUID")
    ip_address: Optional[str] = None
    location: Optional[str] = None


class DeviceHeartbeatRequest(BaseModel):
    status: str = Field(default="ONLINE", description="ONLINE, OFFLINE, ERROR")
    ip_address: Optional[str] = None


class AccessCheckRequest(BaseModel):
    holder_id: str = Field(..., description="Card holder UUID")
    card_type: str = Field(..., description="STUDENT or STAFF")
    device_id: str = Field(..., description="Device identifier")


class AccessLogRequest(BaseModel):
    card_number: str = Field(..., description="RFID card number")
    holder_id: str = Field(..., description="Card holder UUID")
    device_id: str = Field(..., description="Device identifier")
    access_status: str = Field(..., description="GRANTED or DENIED")
    branch_id: str = Field(..., description="Branch UUID")


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
    request: DeviceRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register a new hardware device"""
    # Check if device already exists
    existing_device = await db.execute(
        select(Device).where(
            and_(
                Device.serial_number == request.serial_number,
                Device.organization_id == request.branch_id  # Using branch_id as org_id for now
            )
        )
    )
    device = existing_device.scalar_one_or_none()
    
    if device:
        # Update existing device
        device.device_type = request.device_type
        device.ip_address = request.ip_address
        device.location = request.location
        device.status = "ACTIVE"
        device.last_heartbeat = datetime.now()
    else:
        # Create new device
        device = Device(
            id=request.device_id,
            organization_id=request.branch_id,  # Using branch_id as org_id for now
            branch_id=request.branch_id,
            name=f"{request.device_type}_{request.serial_number}",
            device_type=request.device_type,
            serial_number=request.serial_number,
            ip_address=request.ip_address,
            location=request.location,
            status="ACTIVE",
            last_heartbeat=datetime.now()
        )
        db.add(device)
    
    await db.commit()
    return success_response({"device_id": device.id, "status": "registered"}, "Device registered successfully")


@router.post("/devices/{device_id}/heartbeat")
async def device_heartbeat(
    device_id: str,
    request: DeviceHeartbeatRequest,
    db: AsyncSession = Depends(get_db),
):
    """Receive heartbeat from hardware device"""
    device = await db.execute(
        select(Device).where(Device.id == device_id)
    )
    device = device.scalar_one_or_none()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    device.status = request.status
    device.ip_address = request.ip_address
    device.last_heartbeat = datetime.now()
    
    await db.commit()
    return success_response({"device_id": device_id, "status": "updated"}, "Heartbeat received")


@router.get("/devices")
async def list_devices(
    branch_id: Optional[str] = Query(None),
    device_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
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

@router.post("/access/check")
async def check_access_permission(
    request: AccessCheckRequest,
    db: AsyncSession = Depends(get_db),
):
    """Check if a card holder has access permission"""
    # For now, we'll implement basic access logic
    # You can extend this with time-based access, location-based access, etc.
    
    # Check if holder exists and is active
    from app.infrastructure.models.models import Student, User
    
    if request.card_type == "STUDENT":
        holder = await db.execute(
            select(Student).where(Student.id == request.holder_id)
        )
        holder = holder.scalar_one_or_none()
        
        if not holder:
            return success_response({
                "access_granted": False,
                "reason": "Student not found"
            })
        
        if holder.status != "ACTIVE":
            return success_response({
                "access_granted": False,
                "reason": "Student is not active"
            })
    
    elif request.card_type == "STAFF":
        holder = await db.execute(
            select(User).where(User.id == request.holder_id)
        )
        holder = holder.scalar_one_or_none()
        
        if not holder:
            return success_response({
                "access_granted": False,
                "reason": "Staff not found"
            })
        
        if holder.status != "ACTIVE":
            return success_response({
                "access_granted": False,
                "reason": "Staff is not active"
            })
    
    # Check device status
    device = await db.execute(
        select(Device).where(Device.id == request.device_id)
    )
    device = device.scalar_one_or_none()
    
    if not device or device.status != "ACTIVE":
        return success_response({
            "access_granted": False,
            "reason": "Device is not active"
        })
    
    # Access granted
    return success_response({
        "access_granted": True,
        "reason": "Access permitted"
    })


@router.post("/access/log")
async def log_access(
    request: AccessLogRequest,
    db: AsyncSession = Depends(get_db),
):
    """Log access attempt (granted or denied)"""
    # Create access log entry
    from app.infrastructure.models.models import AuditLog, AuditAction
    
    log_entry = AuditLog(
        organization_id=request.branch_id,  # Using branch_id as org_id for now
        branch_id=request.branch_id,
        user_id=None,  # Hardware device access
        action=AuditAction.OTHER,
        entity_type="ACCESS_LOG",
        entity_id=None,
        old_values=None,
        new_values={
            "card_number": request.card_number,
            "holder_id": request.holder_id,
            "device_id": request.device_id,
            "access_status": request.access_status,
            "timestamp": datetime.now().isoformat()
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
    request: CardPaymentRequest,
    db: AsyncSession = Depends(get_db),
):
    """Process payment using RFID card number"""
    # Get RFID card by card number
    card = await db.execute(
        select(RfidCard).where(RfidCard.card_number == request.card_number)
    )
    card = card.scalar_one_or_none()
    
    if not card:
        return success_response({
            "authorized": False,
            "message": "Card not found",
            "transaction_id": None,
            "amount": float(request.amount),
            "blocked_reason": "CARD_NOT_FOUND",
            "holder_name": None,
            "balance": None
        })
    
    if card.status != "ACTIVE":
        return success_response({
            "authorized": False,
            "message": "Card is not active",
            "transaction_id": None,
            "amount": float(request.amount),
            "blocked_reason": "CARD_INACTIVE",
            "holder_name": card.holder_name,
            "balance": None
        })
    
    # Get wallet info (simplified - would need proper wallet integration)
    # For now, we'll use the canteen wallet endpoint logic
    from app.domain.entities import CanteenWalletTransaction
    
    # Create wallet transaction
    transaction = CanteenWalletTransaction(
        student_id=card.holder_id,
        amount=request.amount,
        transaction_type="DEBIT",
        payment_method="CARD",
        reference_number=f"RFID_{request.card_number}",
        processed_by=None,  # Hardware device
        status="COMPLETED"
    )
    
    db.add(transaction)
    await db.commit()
    await db.refresh(transaction)
    
    return success_response({
        "authorized": True,
        "message": "Payment processed successfully",
        "transaction_id": str(transaction.id),
        "amount": float(request.amount),
        "blocked_reason": None,
        "holder_name": card.holder_name,
        "balance": None  # Would return actual balance
    }, "Payment processed successfully")


@router.post("/card/balance")
async def get_card_balance(
    request: CardBalanceCheckRequest,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("canteen.read"))
):
    """Get wallet balance for a card number"""
    # Get RFID card by card number
    card = await db.execute(
        select(RfidCard).where(RfidCard.card_number == request.card_number)
    )
    card = card.scalar_one_or_none()
    
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    # Determine holder type and get additional information
    holder_type = card.card_type  # STUDENT or STAFF
    holder_role = None
    class_name = None
    branch_name = None
    
    if holder_type == "STUDENT":
        from app.domain.entities import Student, Class, Branch, CanteenOrder
        from uuid import UUID
        
        # Convert holder_id to UUID if it's a string
        holder_id = UUID(card.holder_id) if isinstance(card.holder_id, str) else card.holder_id
        
        student = await db.execute(
            select(Student).where(Student.id == holder_id)
        )
        student = student.scalar_one_or_none()
        
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        
        # Get class name
        if student.class_id:
            class_result = await db.execute(
                select(Class).where(Class.id == student.class_id)
            )
            class_room = class_result.scalar_one_or_none()
            if class_room:
                class_name = class_room.name
        
        # Get branch name
        if student.branch_id:
            branch_result = await db.execute(
                select(Branch).where(Branch.id == student.branch_id)
            )
            branch = branch_result.scalar_one_or_none()
            if branch:
                branch_name = branch.name
        
        # Calculate today's spending
        today = date.today()
        today_orders = await db.execute(
            select(CanteenOrder).where(
                and_(
                    CanteenOrder.student_id == holder_id,
                    CanteenOrder.order_date == today,
                    CanteenOrder.status == "COMPLETED"
                )
            )
        )
        today_orders = today_orders.scalars().all()
        daily_spent = sum(order.total_price for order in today_orders)
        
    elif holder_type == "STAFF":
        from app.domain.entities import User, Branch
        from uuid import UUID
        
        # Convert holder_id to UUID if it's a string
        holder_id = UUID(card.holder_id) if isinstance(card.holder_id, str) else card.holder_id
        
        user = await db.execute(
            select(User).options(
                selectinload(User.roles),
                selectinload(User.branches)
            ).where(User.id == holder_id)
        )
        user = user.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="Staff not found")
        
        # Get role name
        if user.roles:
            holder_role = user.roles[0].name if user.roles else None
        
        # Get branch name (from first assigned branch)
        if user.branches:
            branch = user.branches[0] if user.branches else None
            if branch:
                branch_name = branch.name
        
        daily_spent = Decimal("0.00")  # Staff may not have daily spending limits
    
    else:
        daily_spent = Decimal("0.00")
    
    # Calculate actual balance from wallet transactions
    from app.domain.entities import CanteenWalletTransaction
    
    # Determine the holder ID for wallet transaction query
    wallet_holder_id = holder_id if holder_type == "STUDENT" else (UUID(card.holder_id) if isinstance(card.holder_id, str) else card.holder_id)
    
    wallet_transactions = await db.execute(
        select(CanteenWalletTransaction).where(
            CanteenWalletTransaction.student_id == wallet_holder_id,
            CanteenWalletTransaction.status == "COMPLETED"
        )
    )
    wallet_transactions = wallet_transactions.scalars().all()
    
    current_balance = Decimal("0.00")
    for tx in wallet_transactions:
        if tx.transaction_type == "CREDIT":
            current_balance += Decimal(str(tx.amount))
        elif tx.transaction_type == "DEBIT":
            current_balance -= Decimal(str(tx.amount))
    
    return success_response({
        "card_number": card.card_number,
        "holder_id": card.holder_id,
        "holder_name": card.holder_name,
        "holder_type": holder_type,
        "holder_role": holder_role,
        "class_name": class_name,
        "branch_name": branch_name,
        "balance": float(current_balance),
        "daily_limit": float(Decimal("50.00")),  # Would get from student settings
        "daily_spent": float(daily_spent),
        "card_status": card.status
    }, "Card balance retrieved")


@router.post("/card/topup")
async def topup_card_balance(
    card_number: str,
    amount: Decimal = Query(..., gt=0, decimal_places=2),
    payment_method: str = Query(..., description="CASH, CARD, BANK_TRANSFER"),
    reference_number: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("canteen.write"))
):
    """Top up card balance using card number"""
    try:
        # Get RFID card by card number
        card = await db.execute(
            select(RfidCard).where(RfidCard.card_number == card_number)
        )
        card = card.scalar_one_or_none()
        
        if not card:
            raise HTTPException(status_code=404, detail="Card not found")
        
        # Create wallet transaction
        from app.domain.entities import CanteenWalletTransaction
        from uuid import UUID
        
        # Convert holder_id to UUID if it's a string
        holder_id = UUID(card.holder_id) if isinstance(card.holder_id, str) else card.holder_id
        
        transaction = CanteenWalletTransaction(
            student_id=holder_id,
            amount=float(amount),
            transaction_type="CREDIT",
            payment_method=payment_method.upper(),
            reference_number=reference_number,
            processed_by=current_user.id,
            status="COMPLETED"
        )
        
        db.add(transaction)
        await db.commit()
        await db.refresh(transaction)
        
        # Calculate new balance by summing all wallet transactions
        from app.domain.entities import CanteenWalletTransaction
        
        all_transactions = await db.execute(
            select(CanteenWalletTransaction).where(
                CanteenWalletTransaction.student_id == holder_id,
                CanteenWalletTransaction.status == "COMPLETED"
            )
        )
        all_transactions = all_transactions.scalars().all()
        
        current_balance = Decimal("0.00")
        for tx in all_transactions:
            if tx.transaction_type == "CREDIT":
                current_balance += Decimal(str(tx.amount))
            elif tx.transaction_type == "DEBIT":
                current_balance -= Decimal(str(tx.amount))
        
        new_balance = current_balance
        
        return success_response({
            "card_number": card.card_number,
            "holder_id": card.holder_id,
            "holder_name": card.holder_name,
            "transaction_id": str(transaction.id),
            "amount": float(amount),
            "payment_method": payment_method.upper(),
            "reference_number": reference_number,
            "new_balance": float(current_balance),
            "transaction_date": transaction.created_at.isoformat()
        }, "Card balance topped up successfully")
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error processing topup: {str(e)}")


# ==================== WiFi RFID Device Endpoints ====================

@router.post("/wifi/card-read")
async def wifi_card_read(
    request: WifiCardReadRequest,
    db: AsyncSession = Depends(get_db),
):
    """Handle card read from WiFi RFID device"""
    # Get card info
    card = await db.execute(
        select(RfidCard).where(RfidCard.card_number == request.card_number)
    )
    card = card.scalar_one_or_none()
    
    if not card:
        return success_response({
            "success": False,
            "message": "Card not found",
            "card_number": request.card_number
        })
    
    # Get card balance info
    holder_id = UUID(card.holder_id) if isinstance(card.holder_id, str) else card.holder_id
    
    # Calculate actual balance from wallet transactions
    from app.domain.entities import CanteenWalletTransaction
    
    wallet_transactions = await db.execute(
        select(CanteenWalletTransaction).where(
            CanteenWalletTransaction.student_id == holder_id,
            CanteenWalletTransaction.status == "COMPLETED"
        )
    )
    wallet_transactions = wallet_transactions.scalars().all()
    
    current_balance = Decimal("0.00")
    for tx in wallet_transactions:
        if tx.transaction_type == "CREDIT":
            current_balance += Decimal(str(tx.amount))
        elif tx.transaction_type == "DEBIT":
            current_balance -= Decimal(str(tx.amount))
    
    return success_response({
        "success": True,
        "card_number": card.card_number,
        "holder_id": card.holder_id,
        "holder_name": card.holder_name,
        "holder_type": card.card_type,
        "balance": float(current_balance),
        "device_id": request.device_id,
        "timestamp": request.timestamp or datetime.now().isoformat()
    }, "Card read processed successfully")


@router.get("/wifi/card-reads")
async def get_wifi_card_reads(
    device_id: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get recent card reads from WiFi devices (for frontend polling)"""
    # This would typically read from a card_reads table or cache
    # For now, return empty as we'll implement real-time polling
    return success_response([], "No recent card reads")
