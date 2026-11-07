from datetime import date
from decimal import Decimal

import pytest

from app.domain.services import debt_calculator as calculator
from app.infrastructure.models.models import DebtStatus


@pytest.mark.parametrize("paid,expected", [("0", DebtStatus.OVERDUE), ("25", DebtStatus.OVERDUE)])
def test_debt_status_uses_school_calendar_even_while_server_is_on_previous_day(monkeypatch, paid, expected):
    class ServerDate(date):
        @classmethod
        def today(cls): return cls(2026, 11, 4)
    monkeypatch.setattr(calculator, "date", ServerDate)
    monkeypatch.setattr(calculator, "school_today", lambda: date(2026, 11, 5), raising=False)
    assert calculator.DebtCalculator.calculate_status(Decimal("100"), Decimal(paid), date(2026, 11, 4)) == expected


def test_due_today_is_not_overdue_and_fully_paid_wins_over_old_due_date(monkeypatch):
    monkeypatch.setattr(calculator, "school_today", lambda: date(2026, 11, 5), raising=False)
    assert calculator.DebtCalculator.calculate_status(Decimal("100"), Decimal("25"), date(2026, 11, 5)) == DebtStatus.PARTIALLY_PAID
    assert calculator.DebtCalculator.calculate_status(Decimal("100"), Decimal("100"), date(2020, 1, 1)) == DebtStatus.PAID
