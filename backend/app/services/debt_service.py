from typing import Optional
from uuid import UUID
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import DebtRepository
from app.domain.entities.debt import Debt
from app.core.exceptions import AppException


class DebtService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.debt_repo = DebtRepository()

    async def create_debt(
        self,
        organization_id: UUID,
        branch_id: UUID,
        student_id: UUID,
        debt_type: str,
        amount: Decimal,
        **kwargs
    ) -> Debt:
        debt_data = {
            "organization_id": organization_id,
            "branch_id": branch_id,
            "student_id": student_id,
            "debt_type": debt_type,
            "amount": amount,
            "paid_amount": Decimal("0"),
            "remaining_amount": amount,
            **kwargs
        }
        
        return await self.debt_repo.create(self.db, debt_data)

    async def update_debt(
        self,
        debt_id: UUID,
        **kwargs
    ) -> Debt:
        debt = await self.debt_repo.get(self.db, debt_id)
        if not debt:
            raise AppException("Borç bulunamadı", status_code=404)
        
        return await self.debt_repo.update(self.db, debt, kwargs)

    async def update_paid_amount(
        self,
        debt_id: UUID,
        payment_amount: Decimal
    ) -> Debt:
        debt = await self.debt_repo.get(self.db, debt_id)
        if not debt:
            raise AppException("Borç bulunamadı", status_code=404)
        
        debt.paid_amount += payment_amount
        debt.remaining_amount = debt.amount - debt.paid_amount
        
        if debt.remaining_amount <= 0:
            debt.status = "paid"
            debt.remaining_amount = Decimal("0")
        
        await self.db.flush()
        await self.db.refresh(debt)
        return debt

    async def get_student_total_debt(self, student_id: UUID) -> Decimal:
        return await self.debt_repo.get_total_debt(self.db, student_id)
