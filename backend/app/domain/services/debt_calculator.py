from datetime import date
from decimal import Decimal

from app.infrastructure.models.models import DebtStatus


class DebtCalculator:
    @staticmethod
    def calculate_status(amount: Decimal, paid_amount: Decimal, due_date: date) -> DebtStatus:
        remaining = amount - paid_amount
        if remaining <= 0:
            return DebtStatus.PAID
        if paid_amount > 0:
            if due_date < date.today():
                return DebtStatus.OVERDUE
            return DebtStatus.PARTIALLY_PAID
        if due_date < date.today():
            return DebtStatus.OVERDUE
        return DebtStatus.UNPAID

    @staticmethod
    def validate_payment(amount: Decimal, paid_amount: Decimal, payment_amount: Decimal) -> None:
        if payment_amount <= 0:
            raise ValueError("Ödeme tutarı 0'dan büyük olmalıdır")
        remaining = amount - paid_amount
        if payment_amount > remaining:
            raise ValueError("Ödeme tutarı kalan borçtan fazla olamaz")

    @staticmethod
    def apply_payment(amount: Decimal, paid_amount: Decimal, payment_amount: Decimal) -> Decimal:
        DebtCalculator.validate_payment(amount, paid_amount, payment_amount)
        return paid_amount + payment_amount

    @staticmethod
    def reverse_payment(paid_amount: Decimal, payment_amount: Decimal) -> Decimal:
        new_paid = paid_amount - payment_amount
        if new_paid < 0:
            raise ValueError("Ödeme iptali sonrası borç tutarı negatif olamaz")
        return new_paid
