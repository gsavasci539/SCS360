"""Acceptance contracts for recorded finance summaries, never invented forecasts."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from app.core.dates import school_datetime, school_today
from app.infrastructure.models.models import Branch, Debt, DebtStatus, DebtType, Payment, PaymentMethod, Student, User
from test_finance_compatibility import finance_client, auth  # noqa: F401
from test_material_files import materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401


async def test_finance_summary_uses_real_completed_history_and_scoped_open_debts(finance_client):
    client, sessions, data = finance_client
    now = datetime.now(UTC)
    async with sessions() as db:
        def debt(amount, paid, **values):
            return Debt(organization_id=data["org"].id, branch_id=data["branch"].id,
                student_id=data["children"][0].id, debt_type=DebtType.EDUCATION,
                amount=Decimal(amount), paid_amount=Decimal(paid), due_date=school_today() + timedelta(days=1), **values)
        active = debt("100", "25")
        db.add_all([active, debt("777", "222", status=DebtStatus.CANCELLED),
            debt("300", "100", deleted_at=now)])
        await db.flush()
        def payment(amount, **values):
            return Payment(organization_id=data["org"].id, branch_id=data["branch"].id,
                student_id=data["children"][0].id, debt_id=active.id, amount=Decimal(amount),
                payment_method=PaymentMethod.CASH, payment_date=now, received_by=data["accountant"].id, **values)
        db.add_all([payment("25", status="completed"), payment("900", status="pending"),
            payment("800", status="cancelled"), payment("100", status="completed", cancelled_at=now)])
        foreign = Debt(organization_id=data["stranger"].organization_id, branch_id=data["other_branch"].id,
            student_id=data["stranger"].id, debt_type=DebtType.EDUCATION, amount=1000, paid_amount=100,
            due_date=school_today())
        db.add(foreign)
        await db.commit()
    reply = await client.get("/api/ai/payment-forecast", headers=auth(data["accountant"]), params={"months": 3})
    assert reply.status_code == 200, reply.text
    result = reply.json()["data"]
    assert result["analysis_type"] == "recorded_finance", result
    assert Decimal(str(result["outstanding_debt"])) == 75
    assert Decimal(str(result["collected_total"])) == 25
    assert result["collection_rate"] == 25
    current = next(row for row in result["historical_monthly"] if row["month"] == school_datetime(now).strftime("%Y-%m"))
    assert Decimal(str(current["collected_amount"])) == 25
    assert all(row.get("confidence") is None for row in result["monthly_forecast"])
    assert all(row.get("predicted_amount") is None for row in result["monthly_forecast"])
    assert (await client.get("/api/ai/payment-forecast", headers=auth(data["user"]))).status_code == 403


async def test_empty_finance_summary_is_unknown_and_months_are_validated(finance_client):
    client, _, data = finance_client
    reply = await client.get("/api/ai/payment-forecast", headers=auth(data["accountant"]))
    assert reply.status_code == 200, reply.text
    result = reply.json()["data"]
    assert result["collection_rate"] is None and result["risk_assessment"] == "unknown", result
    assert result["historical_monthly"] == []
    assert Decimal(str(result["outstanding_debt"])) == 0
    for months in (0, -1, 25):
        invalid = await client.get("/api/ai/payment-forecast", headers=auth(data["accountant"]), params={"months": months})
        assert invalid.status_code == 422, invalid.text


async def test_nonfinite_legacy_ledger_is_explicitly_unknown_and_preserved(finance_client):
    client, sessions, data = finance_client
    async with sessions() as db:
        row = Debt(organization_id=data["org"].id, branch_id=data["branch"].id,
            student_id=data["children"][0].id, debt_type=DebtType.EDUCATION, amount=100,
            paid_amount=Decimal("NaN") if db.bind.dialect.name == "postgresql" else Decimal("Infinity"),
            due_date=school_today())
        db.add(row); await db.commit()
    reply = await client.get("/api/ai/payment-forecast", headers=auth(data["accountant"]))
    assert reply.status_code == 200, reply.text
    result = reply.json()["data"]
    assert result["requires_review"] is True
    assert result["outstanding_debt"] is None and result["collection_rate"] is None
    assert result["risk_assessment"] == "unknown"
    async with sessions() as db:
        saved = (await db.execute(select(Debt).where(Debt.id == row.id))).scalar_one()
        assert not saved.paid_amount.is_finite()


async def test_finance_summary_respects_staff_branch_boundary(finance_client):
    client, sessions, data = finance_client
    async with sessions() as db:
        branch = Branch(organization_id=data["org"].id, name="Other branch")
        db.add(branch); await db.flush()
        student = Student(organization_id=data["org"].id, branch_id=branch.id, first_name="Other", last_name="Branch")
        db.add(student); await db.flush()
        for person, amount in ((data["children"][0], "100"), (student, "1000")):
            row = Debt(organization_id=data["org"].id, branch_id=person.branch_id, student_id=person.id,
                debt_type=DebtType.EDUCATION, amount=Decimal(amount), paid_amount=Decimal(amount) / 4,
                due_date=school_today() + timedelta(days=1))
            db.add(row); await db.flush()
            db.add(Payment(organization_id=data["org"].id, branch_id=person.branch_id, student_id=person.id,
                debt_id=row.id, amount=Decimal(amount) / 4, payment_method=PaymentMethod.CASH,
                payment_date=datetime.now(UTC), status="completed", received_by=data["accountant"].id))
        staff = (await db.execute(select(User).options(selectinload(User.branches))
            .where(User.id == data["accountant"].id))).scalar_one()
        staff.branches = [data["branch"]]
        await db.commit()
    reply = await client.get("/api/ai/payment-forecast", headers=auth(data["accountant"]))
    assert reply.status_code == 200, reply.text
    result = reply.json()["data"]
    assert Decimal(result["outstanding_debt"]) == 75
    assert Decimal(result["collected_total"]) == 25
    assert result["debt_count"] == result["payment_count"] == 1


async def test_finance_query_failure_is_a_sanitized_retryable_error(finance_client, monkeypatch):
    client, _, data = finance_client
    from app.application.services import financial_summary
    async def unavailable(*args, **kwargs):
        raise SQLAlchemyError("private ledger SELECT and secret database connection details")
    monkeypatch.setattr(financial_summary, "summary", unavailable)
    reply = await client.get("/api/ai/payment-forecast", headers=auth(data["accountant"]))
    assert reply.status_code == 503, reply.text
    assert "private ledger" not in reply.text and "SELECT" not in reply.text and "secret" not in reply.text
    assert reply.json()["success"] is False


@pytest.mark.parametrize("legacy_case", ["invalid_amount", "future_date"])
async def test_invalid_completed_payment_history_is_unknown_without_hiding_valid_debt_balance(finance_client, legacy_case):
    client, sessions, data = finance_client
    now = datetime.now(UTC)
    async with sessions() as db:
        debt = Debt(organization_id=data["org"].id, branch_id=data["branch"].id,
            student_id=data["children"][0].id, debt_type=DebtType.EDUCATION,
            amount=100, paid_amount=25, due_date=school_today())
        db.add(debt); await db.flush()
        invalid_amount = Decimal("NaN") if db.bind.dialect.name == "postgresql" else Decimal("Infinity")
        invalid = Payment(organization_id=data["org"].id, branch_id=data["branch"].id,
            student_id=data["children"][0].id, debt_id=debt.id,
            amount=invalid_amount if legacy_case == "invalid_amount" else Decimal("50"),
            payment_date=now if legacy_case == "invalid_amount" else now + timedelta(days=2),
            payment_method=PaymentMethod.CASH, status="completed", received_by=data["accountant"].id)
        valid = Payment(organization_id=data["org"].id, branch_id=data["branch"].id,
            student_id=data["children"][0].id, debt_id=debt.id, amount=25,
            payment_date=now, payment_method=PaymentMethod.CASH, status="completed", received_by=data["accountant"].id)
        db.add_all([valid, invalid]); await db.commit()
    reply = await client.get("/api/ai/payment-forecast", headers=auth(data["accountant"]))
    assert reply.status_code == 200, reply.text
    result = reply.json()["data"]
    assert result["requires_review"] is True and result["invalid_payment_count"] == 1
    assert result["collected_total"] is None
    assert all(row["collected_amount"] is None for row in result["historical_monthly"])
    assert Decimal(result["outstanding_debt"]) == 75 and result["collection_rate"] == 25
    async with sessions() as db:
        saved = await db.get(Payment, invalid.id)
        assert saved.cancelled_at is None and saved.status == "completed"
        if legacy_case == "invalid_amount":
            assert not saved.amount.is_finite()
        else:
            assert saved.payment_date.date() == (now + timedelta(days=2)).date()


@pytest.mark.parametrize("portal_db", ["sqlite"], indirect=True)
async def test_summary_reads_money_from_legacy_sqlite_keys_without_rewriting_them(finance_client):
    client, sessions, data = finance_client
    async with sessions() as db:
        assert db.bind.dialect.name == "sqlite"
        legacy_debt = Debt(id="legacy-debt-key", organization_id=data["org"].id, branch_id=data["branch"].id,
            student_id=data["children"][0].id, debt_type=DebtType.EDUCATION, amount=100,
            paid_amount=25, due_date=school_today())
        db.add(legacy_debt); await db.flush()
        db.add(Payment(id="legacy-payment-key", organization_id=data["org"].id, branch_id=data["branch"].id,
            student_id=data["children"][0].id, debt_id="legacy-debt-key", amount=25,
            payment_date=datetime.now(UTC), payment_method=PaymentMethod.CASH,
            status="completed", received_by=data["accountant"].id))
        await db.commit()
        await db.execute(text("UPDATE debts SET debt_type = :value WHERE id = :key"),
            {"value": "LEGACY_IMPORTED_CATEGORY", "key": "legacy-debt-key"})
        await db.execute(text("UPDATE payments SET payment_method = :value WHERE id = :key"),
            {"value": "LEGACY_IMPORTED_METHOD", "key": "legacy-payment-key"})
        await db.commit()
    reply = await client.get("/api/ai/payment-forecast", headers=auth(data["accountant"]))
    assert reply.status_code == 200, reply.text
    result = reply.json()["data"]
    assert Decimal(result["outstanding_debt"]) == 75 and Decimal(result["collected_total"]) == 25
    assert result["requires_review"] is False
    async with sessions() as db:
        assert (await db.execute(text("SELECT id FROM debts WHERE id = :key"), {"key": "legacy-debt-key"})).scalar_one() == "legacy-debt-key"
        assert (await db.execute(text("SELECT id FROM payments WHERE id = :key"), {"key": "legacy-payment-key"})).scalar_one() == "legacy-payment-key"
        assert (await db.execute(text("SELECT payment_method FROM payments WHERE id = :key"), {"key": "legacy-payment-key"})).scalar_one() == "LEGACY_IMPORTED_METHOD"
