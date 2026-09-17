import pytest
from decimal import Decimal
from datetime import date

from app.domain.services.debt_calculator import DebtCalculator
from app.infrastructure.models.models import DebtStatus


class TestDebtCalculator:
    def test_validate_payment_positive(self):
        DebtCalculator.validate_payment(Decimal("100"), Decimal("0"), Decimal("50"))

    def test_validate_payment_zero_raises(self):
        with pytest.raises(ValueError):
            DebtCalculator.validate_payment(Decimal("100"), Decimal("0"), Decimal("0"))

    def test_validate_payment_exceeds_remaining(self):
        with pytest.raises(ValueError):
            DebtCalculator.validate_payment(Decimal("100"), Decimal("50"), Decimal("60"))

    def test_calculate_status_paid(self):
        status = DebtCalculator.calculate_status(Decimal("100"), Decimal("100"), date.today())
        assert status == DebtStatus.PAID

    def test_calculate_status_unpaid(self):
        status = DebtCalculator.calculate_status(Decimal("100"), Decimal("0"), date.today() + __import__("datetime").timedelta(days=10))
        assert status == DebtStatus.UNPAID

    def test_calculate_status_overdue(self):
        status = DebtCalculator.calculate_status(Decimal("100"), Decimal("0"), date.today() - __import__("datetime").timedelta(days=5))
        assert status == DebtStatus.OVERDUE

    def test_apply_payment(self):
        result = DebtCalculator.apply_payment(Decimal("100"), Decimal("30"), Decimal("20"))
        assert result == Decimal("50")

    def test_reverse_payment(self):
        result = DebtCalculator.reverse_payment(Decimal("50"), Decimal("20"))
        assert result == Decimal("30")
