from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import date
from uuid import UUID

from app.infrastructure.models.models import RfidCard


class RfidCardRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        card_number: str,
        card_type: str,
        holder_id: str,
        holder_name: str,
        organization_id: Optional[str] = None,
        branch_id: Optional[str] = None,
        issue_date: Optional[date] = None,
        expiry_date: Optional[date] = None,
        status: str = "ACTIVE"
    ) -> RfidCard:
        """Create a new RFID card"""
        card = RfidCard(
            card_number=card_number,
            card_type=card_type,
            holder_id=holder_id,
            holder_name=holder_name,
            organization_id=organization_id,
            branch_id=branch_id,
            issue_date=issue_date,
            expiry_date=expiry_date,
            status=status
        )
        self.db.add(card)
        await self.db.flush()
        return card

    async def get_by_id(self, card_id: str) -> Optional[RfidCard]:
        """Get RFID card by ID"""
        result = await self.db.execute(select(RfidCard).where(RfidCard.id == card_id))
        return result.scalar_one_or_none()

    async def get_by_card_number(self, card_number: str, organization_id: Optional[str] = None) -> Optional[RfidCard]:
        """Get RFID card by card number"""
        query = select(RfidCard).where(RfidCard.card_number == card_number)
        if organization_id:
            query = query.where(RfidCard.organization_id == organization_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_holder(self, holder_id: str, organization_id: Optional[str] = None) -> List[RfidCard]:
        """Get all RFID cards for a specific holder"""
        query = select(RfidCard).where(RfidCard.holder_id == holder_id)
        if organization_id:
            query = query.where(RfidCard.organization_id == organization_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def list_all(self, organization_id: Optional[str] = None, branch_id: Optional[str] = None) -> List[RfidCard]:
        """List all RFID cards with optional filters"""
        query = select(RfidCard)
        conditions = []
        
        if organization_id:
            conditions.append(RfidCard.organization_id == organization_id)
        if branch_id:
            conditions.append(RfidCard.branch_id == branch_id)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update(
        self,
        card_id: str,
        card_number: Optional[str] = None,
        card_type: Optional[str] = None,
        holder_id: Optional[str] = None,
        holder_name: Optional[str] = None,
        status: Optional[str] = None,
        issue_date: Optional[date] = None,
        expiry_date: Optional[date] = None
    ) -> Optional[RfidCard]:
        """Update RFID card"""
        card = await self.get_by_id(card_id)
        if not card:
            return None
        
        if card_number is not None:
            card.card_number = card_number
        if card_type is not None:
            card.card_type = card_type
        if holder_id is not None:
            card.holder_id = holder_id
        if holder_name is not None:
            card.holder_name = holder_name
        if status is not None:
            card.status = status
        if issue_date is not None:
            card.issue_date = issue_date
        if expiry_date is not None:
            card.expiry_date = expiry_date
        
        await self.db.flush()
        return card

    async def delete(self, card_id: str) -> bool:
        """Delete RFID card"""
        card = await self.get_by_id(card_id)
        if not card:
            return False
        
        await self.db.delete(card)
        await self.db.flush()
        return True

    async def card_number_exists(self, card_number: str, organization_id: Optional[str] = None, exclude_id: Optional[str] = None) -> bool:
        """Check if card number already exists"""
        query = select(RfidCard).where(RfidCard.card_number == card_number)
        if organization_id:
            query = query.where(RfidCard.organization_id == organization_id)
        if exclude_id:
            query = query.where(RfidCard.id != exclude_id)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None
