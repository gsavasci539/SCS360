from __future__ import annotations
from app.core.dates import school_today
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.permissions import PermissionChecker
from app.core.responses import success_response
from app.domain.entities.user import User
from app.core.tenant import TenantContext
from app.repositories.rfid_card_repository import RfidCardRepository
from app.repositories.card_number_repository import CardNumberRepository
from app.infrastructure.models.models import RfidCard

router = APIRouter(prefix="/api/rfid-cards", tags=["RFID Cards"])


class RFIDCardCreate(BaseModel):
    card_number_id: str = Field(..., description="Kart numarası ID (card_numbers tablosundan seçilecek)")
    holder_id: str = Field(..., description="Kart sahibi ID (öğrenci veya personel ID)")
    holder_name: str = Field(..., description="Kart sahibi adı")
    card_type: Optional[str] = Field(None, description="Kart tipi: STUDENT veya STAFF (otomatik belirlenir)")


class RFIDCardUpdate(BaseModel):
    card_number: Optional[str] = None
    card_type: Optional[str] = None
    holder_id: Optional[str] = None
    holder_name: Optional[str] = None
    status: Optional[str] = None
    issue_date: Optional[str] = None
    expiry_date: Optional[str] = None


def card_to_dict(card: RfidCard) -> dict:
    return {
        "id": card.id,
        "card_number": card.card_number,
        "card_type": card.card_type,
        "holder_id": card.holder_id,
        "holder_name": card.holder_name,
        "status": card.status,
        "issue_date": card.issue_date.isoformat() if card.issue_date else None,
        "expiry_date": card.expiry_date.isoformat() if card.expiry_date else None,
        "created_at": card.created_at.isoformat() if card.created_at else None,
        "updated_at": card.updated_at.isoformat() if card.updated_at else None,
    }


@router.get("")
async def list_rfid_cards(
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("canteen.read"))
):
    """List all RFID cards"""
    repo = RfidCardRepository(db)
    
    # Get organization and branch IDs from tenant context
    org_id = str(tenant.organization_id) if tenant.organization_id else None
    branch_id = str(tenant.branch_ids[0]) if tenant.branch_ids else None
    
    # For canteen users, return all active cards without org/branch filtering
    if any(role.slug == "canteen" for role in current_user.roles):
        cards = await repo.list_all()
    else:
        cards = await repo.list_all(organization_id=org_id, branch_id=branch_id)
    
    return success_response([card_to_dict(card) for card in cards], "RFID kartları listelendi")


@router.get("/{card_id}")
async def get_rfid_card(
    card_id: str,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("settings.read"))
):
    """Get a specific RFID card by ID"""
    repo = RfidCardRepository(db)
    card = await repo.get_by_id(card_id)
    
    if not card:
        raise HTTPException(status_code=404, detail="RFID kartı bulunamadı")
    return success_response(card_to_dict(card), "RFID kartı bilgileri")


@router.get("/number/{card_number}")
async def get_rfid_card_by_number(
    card_number: str,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("settings.read"))
):
    """Get RFID card by card number (for mobile sync)"""
    repo = RfidCardRepository(db)
    org_id = str(tenant.organization_id) if tenant.organization_id else None
    card = await repo.get_by_card_number(card_number, organization_id=org_id)
    if not card:
        raise HTTPException(status_code=404, detail="RFID kartı bulunamadı")
    return success_response(card_to_dict(card), "RFID kartı bilgileri")


@router.post("")
async def create_rfid_card(
    card: RFIDCardCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("settings.write"))
):
    """Create a new RFID card using card number from database"""
    rfid_repo = RfidCardRepository(db)
    card_number_repo = CardNumberRepository(db)
    
    # Get organization and branch IDs from tenant context
    org_id = str(tenant.organization_id) if tenant.organization_id else None
    branch_id = str(tenant.branch_ids[0]) if tenant.branch_ids else None
    
    # Get card number from database
    card_number_obj = await card_number_repo.get_by_id(card.card_number_id)
    if not card_number_obj:
        raise HTTPException(status_code=404, detail="Kart numarası bulunamadı")
    
    # Check if card number is available
    if card_number_obj.status != "AVAILABLE":
        raise HTTPException(status_code=400, detail="Bu kart numarası zaten atanmış veya kullanılamaz durumda")
    
    # Check if RFID card with this number already exists
    if await rfid_repo.card_number_exists(card_number_obj.card_number, organization_id=org_id):
        raise HTTPException(status_code=400, detail="Bu kart numarası zaten kullanımda")
    
    # Determine card type
    card_type_str = "STUDENT"
    
    if card.card_type:
        card_type_str = card.card_type.upper()
        if card_type_str not in ["STUDENT", "STAFF"]:
            card_type_str = "STUDENT"
    
    # Create RFID card
    new_card = await rfid_repo.create(
        card_number=card_number_obj.card_number,
        card_type=card_type_str,
        holder_id=card.holder_id,
        holder_name=card.holder_name,
        organization_id=org_id,
        branch_id=branch_id,
        issue_date=school_today(),
        status="ACTIVE"
    )
    
    # Mark card number as ASSIGNED
    await card_number_repo.update_status(card.card_number_id, "ASSIGNED")
    
    await db.commit()
    return success_response(card_to_dict(new_card), "RFID kartı oluşturuldu")


@router.put("/{card_id}")
async def update_rfid_card(
    card_id: str,
    card: RFIDCardUpdate,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("settings.write"))
):
    """Update an existing RFID card"""
    repo = RfidCardRepository(db)
    
    # Check if card number is being changed and if it conflicts
    org_id = str(tenant.organization_id) if tenant.organization_id else None
    if card.card_number:
        if await repo.card_number_exists(card.card_number, organization_id=org_id, exclude_id=card_id):
            raise HTTPException(status_code=400, detail="Bu kart numarası zaten kullanımda")
    
    # Validate enum values if provided
    card_type_str = None
    if card.card_type:
        card_type_str = card.card_type.upper()
        if card_type_str not in ["STUDENT", "STAFF"]:
            card_type_str = None
    
    status_str = None
    if card.status:
        status_str = card.status.upper()
        if status_str not in ["ACTIVE", "INACTIVE", "BLOCKED"]:
            status_str = None
    
    # Update card
    updated_card = await repo.update(
        card_id=card_id,
        card_number=card.card_number,
        card_type=card_type_str,
        holder_id=card.holder_id,
        holder_name=card.holder_name,
        status=status_str,
        issue_date=datetime.strptime(card.issue_date, "%Y-%m-%d").date() if card.issue_date else None,
        expiry_date=datetime.strptime(card.expiry_date, "%Y-%m-%d").date() if card.expiry_date else None
    )
    
    if not updated_card:
        raise HTTPException(status_code=404, detail="RFID kartı bulunamadı")
    
    await db.commit()
    return success_response(card_to_dict(updated_card), "RFID kartı güncellendi")


@router.delete("/{card_id}")
async def delete_rfid_card(
    card_id: str,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("settings.write"))
):
    """Cancel an RFID card (change status to CANCELLED instead of deleting)"""
    rfid_repo = RfidCardRepository(db)
    
    # Get the card
    card = await rfid_repo.get_by_id(card_id)
    if not card:
        raise HTTPException(status_code=404, detail="RFID kartı bulunamadı")
    
    # Update card status to CANCELLED
    updated_card = await rfid_repo.update(card_id, status="CANCELLED")
    
    # Keep card number as ASSIGNED to prevent reuse
    
    await db.commit()
    return success_response(card_to_dict(updated_card), "RFID kartı iptal edildi")


@router.get("/holder/{holder_id}")
async def get_cards_by_holder(
    holder_id: str,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("settings.read"))
):
    """Get all RFID cards for a specific holder (student or staff)"""
    repo = RfidCardRepository(db)
    org_id = str(tenant.organization_id) if tenant.organization_id else None
    cards = await repo.get_by_holder(holder_id, organization_id=org_id)
    return success_response([card_to_dict(card) for card in cards], "Kart sahibine ait kartlar")


@router.post("/sync/mobile")
async def sync_mobile_cards(
    holder_id: str,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("settings.read"))
):
    """Sync RFID cards to mobile app for a specific holder"""
    repo = RfidCardRepository(db)
    org_id = str(tenant.organization_id) if tenant.organization_id else None
    cards = await repo.get_by_holder(holder_id, organization_id=org_id)
    
    # Filter only active cards
    active_cards = [card for card in cards if card.status == "ACTIVE"]
    
    # Format for mobile app
    mobile_cards = []
    for card in active_cards:
        mobile_cards.append({
            "card_id": card.id,
            "card_number": card.card_number,
            "card_type": card.card_type,
            "holder_name": card.holder_name,
            "status": card.status,
            "issue_date": card.issue_date.isoformat() if card.issue_date else None,
            "expiry_date": card.expiry_date.isoformat() if card.expiry_date else None,
            "qr_code": f"RFID:{card.card_number}",
            "last_sync": datetime.now().isoformat()
        })
    
    return success_response(mobile_cards, "Mobil uygulama için kartlar senkronize edildi")
