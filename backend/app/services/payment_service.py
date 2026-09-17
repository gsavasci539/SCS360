from typing import Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import PaymentRepository, DebtRepository, ReceiptRepository
from app.domain.entities.payment import Payment
from app.domain.entities.receipt import Receipt
from app.core.exceptions import AppException


class PaymentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.payment_repo = PaymentRepository()
        self.debt_repo = DebtRepository()
        self.receipt_repo = ReceiptRepository()

    async def create_payment(
        self,
        organization_id: UUID,
        branch_id: UUID,
        student_id: UUID,
        debt_id: UUID,
        amount: Decimal,
        payment_method: str,
        payment_date: datetime,
        **kwargs
    ) -> dict:
        # Get debt
        from app.services.debt_service import DebtService
        debt_service = DebtService(self.db)
        debt = await self.debt_repo.get(self.db, debt_id)
        
        if not debt:
            raise AppException("Borç bulunamadı", status_code=404)
        
        if amount > debt.remaining_amount:
            raise AppException("Ödeme tutarı kalan borçtan büyük olamaz", status_code=400)
        
        # Create payment
        payment_data = {
            "organization_id": organization_id,
            "branch_id": branch_id,
            "student_id": student_id,
            "debt_id": debt_id,
            "amount": amount,
            "payment_method": payment_method,
            "payment_date": payment_date,
            **kwargs
        }
        
        payment = await self.payment_repo.create(self.db, payment_data)
        
        # Update debt
        await debt_service.update_paid_amount(debt_id, amount)
        
        # Create receipt
        receipt_number = await self._generate_receipt_number(organization_id, branch_id)
        receipt_data = {
            "organization_id": organization_id,
            "branch_id": branch_id,
            "payment_id": payment.id,
            "receipt_number": receipt_number,
            "student_name": f"{debt.student_id}",  # TODO: Get actual student name
            "amount": amount,
            "payment_method": payment_method,
            "payment_date": payment_date
        }
        
        receipt = await self.receipt_repo.create(self.db, receipt_data)
        
        return {
            "payment": payment,
            "receipt": receipt
        }

    async def _generate_receipt_number(self, organization_id: UUID, branch_id: UUID) -> str:
        # TODO: Implement receipt number generation logic
        import time
        return f"RCP-{int(time.time())}"

    async def cancel_payment(self, payment_id: UUID) -> Payment:
        payment = await self.payment_repo.get(self.db, payment_id)
        if not payment:
            raise AppException("Ödeme bulunamadı", status_code=404)
        
        if payment.status == "cancelled":
            raise AppException("Ödeme zaten iptal edilmiş", status_code=400)
        
        # Reverse debt payment
        from app.services.debt_service import DebtService
        debt_service = DebtService(self.db)
        debt = await self.debt_repo.get(self.db, payment.debt_id)
        
        debt.paid_amount -= payment.amount
        debt.remaining_amount += payment.amount
        debt.status = "pending"
        
        await self.db.flush()
        
        # Cancel payment
        payment.status = "cancelled"
        await self.db.flush()
        await self.db.refresh(payment)
        
        return payment
