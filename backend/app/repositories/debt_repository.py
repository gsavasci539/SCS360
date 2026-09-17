from datetime import datetime
from decimal import Decimal
from typing import List
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.debt import Debt
from app.repositories.base_repository import BaseRepository


class DebtRepository(BaseRepository[Debt]):
    def __init__(self):
        super().__init__(Debt)
    async def get_by_student(
        self, db: AsyncSession, student_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Debt]:
        result = await db.execute(
            select(Debt)
            .where(Debt.student_id == student_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_organization(
        self, db: AsyncSession, organization_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Debt]:
        result = await db.execute(
            select(Debt)
            .where(Debt.organization_id == organization_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_overdue_debts(
        self, db: AsyncSession, organization_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Debt]:
        result = await db.execute(
            select(Debt)
            .where(
                and_(
                    Debt.organization_id == organization_id,
                    Debt.due_date < datetime.utcnow(),
                    Debt.remaining_amount > 0
                )
            )
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_pending_debts(
        self, db: AsyncSession, organization_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Debt]:
        result = await db.execute(
            select(Debt)
            .where(
                and_(
                    Debt.organization_id == organization_id,
                    Debt.status == "pending",
                    Debt.remaining_amount > 0
                )
            )
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_total_debt(
        self, db: AsyncSession, student_id: UUID
    ) -> Decimal:
        result = await db.execute(
            select(func.sum(Debt.remaining_amount)).where(
                and_(
                    Debt.student_id == student_id,
                    Debt.remaining_amount > 0
                )
            )
        )
        return result.scalar() or Decimal("0.00")

    async def get_by_type(
        self, db: AsyncSession, debt_type: str, organization_id: UUID
    ) -> List[Debt]:
        result = await db.execute(
            select(Debt).where(
                and_(
                    Debt.organization_id == organization_id,
                    Debt.debt_type == debt_type
                )
            )
        )
        return result.scalars().all()
