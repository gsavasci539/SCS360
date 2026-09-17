from datetime import datetime
from decimal import Decimal
from typing import List
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.payment import Payment
from app.repositories.base_repository import BaseRepository


class PaymentRepository(BaseRepository[Payment]):
    def __init__(self):
        super().__init__(Payment)
    async def get_by_student(
        self, db: AsyncSession, student_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Payment]:
        result = await db.execute(
            select(Payment)
            .where(Payment.student_id == student_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_debt(
        self, db: AsyncSession, debt_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Payment]:
        result = await db.execute(
            select(Payment)
            .where(Payment.debt_id == debt_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_organization(
        self, db: AsyncSession, organization_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Payment]:
        result = await db.execute(
            select(Payment)
            .where(Payment.organization_id == organization_id)
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
    ) -> List[Payment]:
        result = await db.execute(
            select(Payment).where(
                and_(
                    Payment.organization_id == organization_id,
                    Payment.payment_date >= start_date,
                    Payment.payment_date <= end_date
                )
            )
        )
        return result.scalars().all()

    async def get_total_payments(
        self, db: AsyncSession, student_id: UUID
    ) -> Decimal:
        result = await db.execute(
            select(func.sum(Payment.amount)).where(
                and_(
                    Payment.student_id == student_id,
                    Payment.status == "completed"
                )
            )
        )
        return result.scalar() or Decimal("0.00")

    async def get_by_method(
        self, db: AsyncSession, payment_method: str, organization_id: UUID
    ) -> List[Payment]:
        result = await db.execute(
            select(Payment).where(
                and_(
                    Payment.organization_id == organization_id,
                    Payment.payment_method == payment_method
                )
            )
        )
        return result.scalars().all()
