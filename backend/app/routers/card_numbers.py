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
from app.repositories.card_number_repository import CardNumberRepository
from app.infrastructure.models.models import CardNumber

router = APIRouter(prefix="/api/card-numbers", tags=["Card Numbers"])


class CardNumberCreate(BaseModel):
    card_number: str = Field(..., description="Kart numarası")
    notes: Optional[str] = Field(None, description="Notlar")
    purchased_date: Optional[str] = Field(None, description="Satın alma tarihi (YYYY-MM-DD)")
    supplier: Optional[str] = Field(None, description="Tedarikçi")


class CardNumberUpdate(BaseModel):
    status: Optional[str] = Field(None, description="Durum: AVAILABLE, ASSIGNED, DAMAGED, LOST")
    notes: Optional[str] = Field(None, description="Notlar")
    purchased_date: Optional[str] = Field(None, description="Satın alma tarihi (YYYY-MM-DD)")
    supplier: Optional[str] = Field(None, description="Tedarikçi")


def card_number_to_dict(card: CardNumber) -> dict:
    return {
        "id": card.id,
        "card_number": card.card_number,
        "status": card.status,
        "notes": card.notes,
        "purchased_date": card.purchased_date.isoformat() if card.purchased_date else None,
        "supplier": card.supplier,
        "organization_id": card.organization_id,
        "branch_id": card.branch_id,
        "created_at": card.created_at.isoformat() if card.created_at else None,
        "updated_at": card.updated_at.isoformat() if card.updated_at else None,
    }


@router.get("")
async def list_card_numbers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("settings.read")),
    status: Optional[str] = None
):
    """List all card numbers with optional status filter"""
    repo = CardNumberRepository(db)
    
    # Get organization and branch IDs from tenant context
    org_id = str(tenant.organization_id) if tenant.organization_id else None
    branch_id = str(tenant.branch_ids[0]) if tenant.branch_ids else None
    
    cards = await repo.list_all(organization_id=org_id, branch_id=branch_id, status=status)
    return success_response([card_number_to_dict(card) for card in cards], "Kart numaraları listelendi")


@router.get("/available")
async def list_available_card_numbers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("settings.read"))
):
    """List only available card numbers for selection"""
    repo = CardNumberRepository(db)
    
    # Get organization and branch IDs from tenant context
    org_id = str(tenant.organization_id) if tenant.organization_id else None
    branch_id = str(tenant.branch_ids[0]) if tenant.branch_ids else None
    
    cards = await repo.list_available(organization_id=org_id, branch_id=branch_id)
    return success_response([card_number_to_dict(card) for card in cards], "Mevcut kart numaraları")


@router.get("/{card_id}")
async def get_card_number(
    card_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("settings.read"))
):
    """Get a specific card number by ID"""
    repo = CardNumberRepository(db)
    card = await repo.get_by_id(card_id)
    
    if not card:
        raise HTTPException(status_code=404, detail="Kart numarası bulunamadı")
    return success_response(card_number_to_dict(card), "Kart numarası bilgileri")


@router.post("")
async def create_card_number(
    card: CardNumberCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("settings.write"))
):
    """Create a new card number"""
    repo = CardNumberRepository(db)
    
    # Get organization and branch IDs from tenant context
    org_id = str(tenant.organization_id) if tenant.organization_id else None
    branch_id = str(tenant.branch_ids[0]) if tenant.branch_ids else None
    
    # Check if card number already exists
    if await repo.card_number_exists(card.card_number, organization_id=org_id):
        raise HTTPException(status_code=400, detail="Bu kart numarası zaten kullanımda")
    
    # Parse purchased date if provided
    purchased_date = None
    if card.purchased_date:
        purchased_date = datetime.strptime(card.purchased_date, "%Y-%m-%d").date()
    
    # Create card number
    new_card = await repo.create(
        card_number=card.card_number,
        organization_id=org_id,
        branch_id=branch_id,
        status="AVAILABLE",
        notes=card.notes,
        purchased_date=purchased_date,
        supplier=card.supplier
    )
    
    await db.commit()
    return success_response(card_number_to_dict(new_card), "Kart numarası oluşturuldu")


@router.put("/{card_id}")
async def update_card_number(
    card_id: str,
    card: CardNumberUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("settings.write"))
):
    """Update an existing card number"""
    repo = CardNumberRepository(db)
    
    # Validate status if provided
    status_str = None
    if card.status:
        status_str = card.status.upper()
        if status_str not in ["AVAILABLE", "ASSIGNED", "DAMAGED", "LOST"]:
            raise HTTPException(status_code=400, detail="Geçersiz durum. AVAILABLE, ASSIGNED, DAMAGED veya LOST olmalıdır")
    
    # Parse purchased date if provided
    purchased_date = None
    if card.purchased_date:
        purchased_date = datetime.strptime(card.purchased_date, "%Y-%m-%d").date()
    
    # Update card number
    updated_card = await repo.update(
        card_id=card_id,
        status=status_str,
        notes=card.notes,
        purchased_date=purchased_date,
        supplier=card.supplier
    )
    
    if not updated_card:
        raise HTTPException(status_code=404, detail="Kart numarası bulunamadı")
    
    await db.commit()
    return success_response(card_number_to_dict(updated_card), "Kart numarası güncellendi")


@router.delete("/{card_id}")
async def delete_card_number(
    card_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("settings.write"))
):
    """Delete a card number"""
    repo = CardNumberRepository(db)
    
    deleted = await repo.delete(card_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Kart numarası bulunamadı")
    
    await db.commit()
    return success_response(message="Kart numarası silindi")
