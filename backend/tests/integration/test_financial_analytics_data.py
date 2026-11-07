from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from app.core.dates import school_today
from app.infrastructure.models.models import Debt, DebtStatus, DebtType, Payment, PaymentMethod, Permission, Role
from test_finance_compatibility import finance_client, auth  # noqa: F401
from test_material_files import materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401


@pytest.fixture
async def financial_analytics_client(finance_client):
    client, sessions, data = finance_client
    async with sessions() as db:
        role = (await db.execute(select(Role).options(selectinload(Role.permissions))
            .where(Role.slug == "accountant"))).scalar_one()
        role.permissions.append(Permission(code="parents.read", name="Parents", module="parents"))
        await db.commit()
    return client, sessions, data


async def test_empty_financial_analytics_does_not_invent_monthly_income_or_model_scores(financial_analytics_client):
    client, _, data = financial_analytics_client
    reply = await client.get("/api/ai/ai-financial-predictions", headers=auth(data["accountant"]))
    assert reply.status_code == 200, reply.text
    result = reply.json()["data"]
    assert result["analysis_type"] == "recorded_finance" and result["ai_model"] is None, result
    assert result["forecast_available"] is False and result["predictions"] == []
    assert result["risk_parents"] == [] and result["risk_assessment"]["level"] == "unknown"
    assert result["collection_rate"] is None and result["historical_monthly"] == []
    assert all(row["scheduled_amount"] == "0.00" and row["predicted_amount"] is None for row in result["monthly_forecast"])
    for months in (0, -1, 25):
        assert (await client.get("/api/ai/ai-financial-predictions", headers=auth(data["accountant"]), params={"months": months})).status_code == 422


async def test_financial_analytics_uses_scoped_real_payment_history_and_contract_dues(financial_analytics_client):
    client, sessions, data = financial_analytics_client
    now = datetime.now(UTC)
    async with sessions() as db:
        def debt(amount, paid="0", **values):
            return Debt(organization_id=data["org"].id, branch_id=data["branch"].id,
                student_id=data["children"][0].id, debt_type=DebtType.EDUCATION,
                amount=Decimal(amount), paid_amount=Decimal(paid), due_date=school_today() + timedelta(days=1), **values)
        selected = debt("100", "25")
        db.add_all([selected, debt("500", status=DebtStatus.CANCELLED), debt("777", deleted_at=now)])
        await db.flush()
        def payment(amount, **values):
            return Payment(organization_id=data["org"].id, branch_id=data["branch"].id,
                student_id=data["children"][0].id, debt_id=selected.id, amount=Decimal(amount),
                payment_date=now, payment_method=PaymentMethod.CASH, received_by=data["accountant"].id, **values)
        db.add_all([payment("25", status="completed"), payment("80", status="pending"),
            payment("90", status="cancelled"), payment("100", status="completed", cancelled_at=now)])
        db.add(Debt(organization_id=data["stranger"].organization_id, branch_id=data["other_branch"].id,
            student_id=data["stranger"].id, debt_type=DebtType.EDUCATION, amount=9000, paid_amount=0, due_date=school_today()))
        await db.commit()
    reply = await client.get("/api/ai/ai-financial-predictions", headers=auth(data["accountant"]), params={"months": 3})
    assert reply.status_code == 200, reply.text
    result = reply.json()["data"]
    assert Decimal(result["outstanding_debt"]) == 75 and Decimal(result["collected_total"]) == 25
    assert result["collection_rate"] == 25 and result["months"] == 3
    assert Decimal(result["total_expected"]) == 75
    assert sum(Decimal(row["scheduled_amount"]) for row in result["monthly_forecast"]) == 75
    assert sum(Decimal(row["collected_amount"]) for row in result["historical_monthly"]) == 25
    assert result["predictions"] == [] and result["risk_assessment"]["level"] == "unknown"


async def test_financial_analytics_keeps_bad_legacy_balances_unknown_and_unchanged(financial_analytics_client):
    client, sessions, data = financial_analytics_client
    async with sessions() as db:
        row = Debt(organization_id=data["org"].id, branch_id=data["branch"].id, student_id=data["children"][0].id,
            debt_type=DebtType.EDUCATION, amount=100,
            paid_amount=Decimal("NaN") if db.bind.dialect.name == "postgresql" else Decimal("Infinity"), due_date=school_today())
        db.add(row); await db.commit()
    reply = await client.get("/api/ai/ai-financial-predictions", headers=auth(data["accountant"]))
    assert reply.status_code == 200, reply.text
    result = reply.json()["data"]
    assert result["requires_review"] is True and result["outstanding_debt"] is None
    assert result["risk_assessment"]["collection_rate"] is None
    async with sessions() as db:
        assert not (await db.get(Debt, row.id)).paid_amount.is_finite()


async def test_financial_analytics_query_failure_is_503_without_database_details(financial_analytics_client, monkeypatch):
    from app.application.services import financial_summary
    client, _, data = financial_analytics_client
    async def unavailable(*args, **kwargs):
        raise SQLAlchemyError("secret financial SELECT and connection credentials")
    monkeypatch.setattr(financial_summary, "summary", unavailable)
    reply = await client.get("/api/ai/ai-financial-predictions", headers=auth(data["accountant"]))
    assert reply.status_code == 503 and reply.json()["success"] is False, reply.text
    assert "SELECT" not in reply.text and "secret" not in reply.text and "credentials" not in reply.text


async def test_financial_analytics_keeps_both_finance_and_parent_domain_permissions_required(finance_client):
    client, sessions, data = finance_client
    endpoint = "/api/ai/ai-financial-predictions"
    assert (await client.get(endpoint, headers=auth(data["accountant"]))).status_code == 403
    async with sessions() as db:
        role = (await db.execute(select(Role).options(selectinload(Role.permissions)).where(Role.slug == "accountant"))).scalar_one()
        role.permissions = [Permission(code="parents.read", name="Parents", module="parents")]
        await db.commit()
    assert (await client.get(endpoint, headers=auth(data["accountant"]))).status_code == 403
