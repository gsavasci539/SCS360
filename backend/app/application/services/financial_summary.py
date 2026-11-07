"""Recorded ledger and contractual due dates; this service does not predict income."""
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from sqlalchemy import func, select

from app.core.dates import school_datetime, school_today
from app.core.exceptions import ForbiddenException
from app.infrastructure.models.models import Debt, DebtStatus, Payment
from app.infrastructure.repositories.base import BaseRepository


MAX_MONEY = Decimal("9999999999.99")
ZERO = Decimal("0")


def month_start(day: date, offset: int = 0) -> date:
    year, month = divmod(day.year * 12 + day.month - 1 + offset, 12)
    return date(year, month + 1, 1)


def money(value):
    try:
        amount = Decimal(str(value))
        return amount if amount.is_finite() and ZERO <= amount <= MAX_MONEY else None
    except (InvalidOperation, TypeError, ValueError):
        return None


def currency(value):
    return format(value.quantize(Decimal("0.01")), ".2f") if value is not None else None


def recorded_summary(debts, payments, months: int, *, today: date):
    """Calculate known amounts without silently replacing invalid ledger rows by zero."""
    end = month_start(today, months)
    buckets = {month_start(today, offset).strftime("%Y-%m"): {"amount": ZERO, "count": 0}
        for offset in range(months)}
    principal, paid, outstanding, overdue = ZERO, ZERO, ZERO, ZERO
    overdue_count, upcoming_count, invalid_debts, invalid_payments = 0, 0, 0, 0
    for debt in debts:
        amount, received = money(debt.amount), money(debt.paid_amount)
        if amount is None or received is None or received > amount or not isinstance(debt.due_date, date):
            invalid_debts += 1
            continue
        remaining = amount - received
        principal += amount
        paid += received
        outstanding += remaining
        if remaining <= 0:
            continue
        if debt.due_date < today:
            overdue += remaining
            overdue_count += 1
        elif debt.due_date < end:
            bucket = buckets[debt.due_date.strftime("%Y-%m")]
            bucket["amount"] += remaining
            bucket["count"] += 1
            upcoming_count += 1

    historical = defaultdict(lambda: {"amount": ZERO, "count": 0})
    collected = ZERO
    for payment in payments:
        amount = money(payment.amount)
        try:
            local_day = school_datetime(payment.payment_date).date()
        except (AttributeError, OverflowError, TypeError, ValueError):
            local_day = None
        if amount is None or amount <= 0 or local_day is None or local_day > today:
            invalid_payments += 1
            continue
        collected += amount
        entry = historical[local_day.strftime("%Y-%m")]
        entry["amount"] += amount
        entry["count"] += 1

    requires_review = bool(invalid_debts or invalid_payments)
    rate = (float((paid / principal * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
        if not invalid_debts and principal > 0 else None)
    scheduled = sum((bucket["amount"] for bucket in buckets.values()), ZERO)
    recommendations = []
    if requires_review:
        recommendations.append("Eski tutar veya tarih bilgileri incelenmeli; eksik toplamlar gösterilmez.")
    if overdue_count and not invalid_debts:
        recommendations.append(f"Vadesi geçmiş {overdue_count} açık borç kaydı bulunuyor.")
    if not payments:
        recommendations.append("Henüz tamamlanmış tahsilat kaydı yok.")
    return {
        "analysis_type": "recorded_finance",
        "data_source": ["debts", "payments"],
        "as_of": today.isoformat(),
        "period_start": today.isoformat(),
        "period_end_exclusive": end.isoformat(),
        "months": months,
        "forecast_available": False,
        "total_debt": currency(principal) if not invalid_debts else None,
        "total_paid": currency(paid) if not invalid_debts else None,
        "outstanding_debt": currency(outstanding) if not invalid_debts else None,
        "total_expected": currency(scheduled) if not invalid_debts else None,
        "overdue_amount": currency(overdue) if not invalid_debts else None,
        "overdue_debts_count": overdue_count if not invalid_debts else None,
        "upcoming_payments_count": upcoming_count if not invalid_debts else None,
        "collection_rate": rate,
        "collected_total": currency(collected) if not invalid_payments else None,
        "payment_count": len(payments),
        "debt_count": len(debts),
        "historical_monthly": [{"month": month,
            "collected_amount": currency(entry["amount"]) if not invalid_payments else None,
            "payment_count": entry["count"]} for month, entry in sorted(historical.items())],
        # The route name is retained for old clients. These are contractual due
        # amounts, with predictive fields explicitly unavailable.
        "monthly_forecast": [{"month": month,
            "scheduled_amount": currency(entry["amount"]) if not invalid_debts else None,
            "debt_count": entry["count"] if not invalid_debts else None,
            "predicted_amount": None, "confidence": None} for month, entry in buckets.items()],
        "trend": "insufficient_data",
        "risk_assessment": "unknown",
        "requires_review": requires_review,
        "invalid_debt_count": invalid_debts,
        "invalid_payment_count": invalid_payments,
        "recommendations": recommendations,
    }


async def summary(db, tenant, months: int):
    if not tenant.organization_id:
        raise ForbiddenException("Önce kurum çalışma alanını seçin")
    repository = BaseRepository(db, tenant)
    # Project only monetary/date columns. Old SQLite keys and unrelated enum
    # values must not take down an aggregate or be rewritten to load an entity.
    # ORM column annotations retain the global tenant/student criteria.
    debt_query = repository._branch_filter(select(Debt.amount, Debt.paid_amount, Debt.due_date).where(
        Debt.organization_id == tenant.organization_id,
        Debt.deleted_at.is_(None), Debt.status != DebtStatus.CANCELLED), Debt)
    payment_query = repository._branch_filter(select(Payment.amount, Payment.payment_date).where(
        Payment.organization_id == tenant.organization_id,
        Payment.cancelled_at.is_(None), func.lower(Payment.status) == "completed"), Payment)
    debts = (await db.execute(debt_query)).all()
    payments = (await db.execute(payment_query)).all()
    return recorded_summary(debts, payments, months, today=school_today())
