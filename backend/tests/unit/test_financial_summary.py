from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace

from app.application.services.financial_summary import recorded_summary


def debt(amount, due, paid="0"):
    return SimpleNamespace(amount=Decimal(amount), paid_amount=Decimal(paid), due_date=due)


def test_contract_calendar_crosses_year_once_and_keeps_overdue_and_later_balances_separate():
    rows = [debt("10", date(2026, 12, 31)), debt("20", date(2027, 1, 1)),
        debt("30", date(2027, 2, 28)), debt("40", date(2027, 3, 1)), debt("5", date(2026, 12, 30))]
    result = recorded_summary(rows, [], 3, today=date(2026, 12, 31))
    assert [(row["month"], row["scheduled_amount"]) for row in result["monthly_forecast"]] == [
        ("2026-12", "10.00"), ("2027-01", "20.00"), ("2027-02", "30.00")]
    assert result["total_expected"] == "60.00"
    assert result["overdue_amount"] == "5.00"
    assert result["outstanding_debt"] == "105.00"
    assert result["period_end_exclusive"] == "2027-03-01"
    assert result["upcoming_payments_count"] == 3
    assert result["collection_rate"] == 0
    assert result["risk_assessment"] == "unknown"


def test_history_uses_school_month_for_utc_and_naive_database_timestamps(monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "BUSINESS_TIMEZONE", "Europe/Istanbul")
    payments = [SimpleNamespace(amount=Decimal(amount), payment_date=instant) for amount, instant in [
        ("1", datetime(2026, 12, 31, 20, 59, tzinfo=UTC)),
        ("2", datetime(2026, 12, 31, 21, tzinfo=UTC)),
        ("3", datetime(2027, 1, 1))]]
    result = recorded_summary([], payments, 1, today=date(2027, 1, 1))
    assert result["historical_monthly"] == [
        {"month": "2026-12", "collected_amount": "1.00", "payment_count": 1},
        {"month": "2027-01", "collected_amount": "5.00", "payment_count": 2}]
    assert result["collected_total"] == "6.00"
    assert result["collection_rate"] is None
    assert result["requires_review"] is False


def test_invalid_ledger_never_presents_a_partial_total_as_a_complete_balance():
    rows = [debt("100", date(2027, 1, 10), "25"), debt("50", date(2027, 1, 20), "NaN")]
    result = recorded_summary(rows, [], 2, today=date(2027, 1, 1))
    assert result["requires_review"] is True and result["invalid_debt_count"] == 1
    for key in ("total_debt", "total_paid", "total_expected", "overdue_amount", "outstanding_debt", "collection_rate"):
        assert result[key] is None, key
    assert all(row["scheduled_amount"] is None for row in result["monthly_forecast"])
    assert result["collected_total"] == "0.00"
