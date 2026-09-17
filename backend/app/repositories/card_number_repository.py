from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import date

from app.infrastructure.models.models import CardNumber


class CardNumberRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        card_number: str,
        organization_id: Optional[str] = None,
        branch_id: Optional[str] = None,
        status: str = "AVAILABLE",
        notes: Optional[str] = None,
        purchased_date: Optional[date] = None,
        supplier: Optional[str] = None
    ) -> CardNumber:
        """Create a new card number"""
        card = CardNumber(
            card_number=card_number,
            organization_id=organization_id,
            branch_id=branch_id,
            status=status,
            notes=notes,
            purchased_date=purchased_date,
            supplier=supplier
        )
        self.db.add(card)
        await self.db.flush()
        return card

    async def get_by_id(self, card_id: str) -> Optional[CardNumber]:
        """Get card number by ID"""
        result = await self.db.execute(select(CardNumber).where(CardNumber.id == card_id))
        return result.scalar_one_or_none()

    async def get_by_card_number(self, card_number: str, organization_id: Optional[str] = None) -> Optional[CardNumber]:
        """Get card number by card number"""
        query = select(CardNumber).where(CardNumber.card_number == card_number)
        if organization_id:
            query = query.where(CardNumber.organization_id == organization_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_all(
        self,
        organization_id: Optional[str] = None,
        branch_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[CardNumber]:
        """List all card numbers with optional filters"""
        query = select(CardNumber)
        conditions = []
        
        if organization_id:
            conditions.append(CardNumber.organization_id == organization_id)
        if branch_id:
            conditions.append(CardNumber.branch_id == branch_id)
        if status:
            conditions.append(CardNumber.status == status)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def list_available(
        self,
        organization_id: Optional[str] = None,
        branch_id: Optional[str] = None
    ) -> List[CardNumber]:
        """List only available card numbers"""
        return await self.list_all(organization_id=organization_id, branch_id=branch_id, status="AVAILABLE")

    async def update(
        self,
        card_id: str,
        status: Optional[str] = None,
        notes: Optional[str] = None,
        purchased_date: Optional[date] = None,
        supplier: Optional[str] = None
    ) -> Optional[CardNumber]:
        """Update card number"""
        card = await self.get_by_id(card_id)
        if not card:
            return None
        
        if status is not None:
            card.status = status
        if notes is not None:
            card.notes = notes
        if purchased_date is not None:
            card.purchased_date = purchased_date
        if supplier is not None:
            card.supplier = supplier
        
        await self.db.flush()
        return card

    async def update_status(self, card_id: str, status: str) -> Optional[CardNumber]:
        """Update card number status"""
        return await self.update(card_id, status=status)

    async def delete(self, card_id: str) -> bool:
        """Delete card number"""
        card = await self.get_by_id(card_id)
        if not card:
            return False
        
        await self.db.delete(card)
        await self.db.flush()
        return True

    async def card_number_exists(self, card_number: str, organization_id: Optional[str] = None, exclude_id: Optional[str] = None) -> bool:
        """Check if card number already exists"""
        query = select(CardNumber).where(CardNumber.card_number == card_number)
        if organization_id:
            query = query.where(CardNumber.organization_id == organization_id)
        if exclude_id:
            query = query.where(CardNumber.id != exclude_id)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None
