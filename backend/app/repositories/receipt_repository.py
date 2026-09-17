from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.receipt import Receipt
from app.repositories.base_repository import BaseRepository


class ReceiptRepository(BaseRepository[Receipt]):
    async def get_by_receipt_number(
        self, db: AsyncSession, receipt_number: str
    ) -> Optional[Receipt]:
        result = await db.execute(
            select(Receipt).where(Receipt.receipt_number == receipt_number)
        )
        return result.scalar_one_or_none()

    async def get_by_payment(
        self, db: AsyncSession, payment_id: UUID
    ) -> Optional[Receipt]:
        result = await db.execute(
            select(Receipt).where(Receipt.payment_id == payment_id)
        )
        return result.scalar_one_or_none()

    async def get_by_student(
        self, db: AsyncSession, student_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Receipt]:
        result = await db.execute(
            select(Receipt)
            .where(Receipt.student_id == student_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_organization(
        self, db: AsyncSession, organization_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Receipt]:
        result = await db.execute(
            select(Receipt)
            .where(Receipt.organization_id == organization_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_date_range(
        self,
        db: AsyncSession,
        organization_id: UUID,
        start_date: datetime,
        end_date: datetime
    ) -> List[Receipt]:
        result = await db.execute(
            select(Receipt).where(
                and_(
                    Receipt.organization_id == organization_id,
                    Receipt.issued_at >= start_date,
                    Receipt.issued_at <= end_date
                )
            )
        )
        return result.scalars().all()

    async def generate_receipt_number(
        self, db: AsyncSession, organization_id: UUID
    ) -> str:
        """Generate unique receipt number for organization"""
        from datetime import datetime
        date_prefix = datetime.now().strftime("%Y%m")
        
        # Count receipts for this month
        result = await db.execute(
            select(Receipt).where(
                and_(
                    Receipt.organization_id == organization_id,
                    Receipt.receipt_number.like(f"{date_prefix}%")
                )
            )
        )
        count = len(result.scalars().all())
        
        # Generate receipt number: YYYYMM + 4 digit sequence
        return f"{date_prefix}{(count + 1):04d}"

    async def create_for_payment(
        self, db: AsyncSession, payment_id: UUID, user_id: UUID
    ) -> Receipt:
        """Create receipt for a payment"""
        from app.infrastructure.models.models import Payment, Debt
        
        # Get payment
        payment_result = await db.execute(
            select(Payment).where(Payment.id == payment_id)
        )
        payment = payment_result.scalar_one_or_none()
        if not payment:
            raise ValueError("Payment not found")
        
        # Check if receipt already exists
        existing = await self.get_by_payment(db, payment_id)
        if existing:
            return existing
        
        # Get debt for remaining debt calculation
        debt_result = await db.execute(
            select(Debt).where(Debt.id == payment.debt_id)
        )
        debt = debt_result.scalar_one_or_none()
        
        # Calculate remaining debt
        remaining_debt = debt.remaining_amount if debt else 0
        
        # Generate receipt number
        receipt_number = await self.generate_receipt_number(db, payment.organization_id)
        
        # Create receipt
        receipt = Receipt(
            organization_id=payment.organization_id,
            branch_id=payment.branch_id,
            student_id=payment.student_id,
            payment_id=payment.id,
            receipt_number=receipt_number,
            issued_by=user_id,
            remaining_debt=remaining_debt
        )
        
        db.add(receipt)
        await db.flush()
        await db.refresh(receipt)
        
        return receipt
