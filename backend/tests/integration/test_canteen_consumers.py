"""Actual HTTP consumers use the ledger, native scopes and school calendar."""
from datetime import date, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload
from test_chatbot_finance_data import grant_finance
from test_material_files import headers, materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from test_recorded_canteen import movement, order
from test_saas_platform import platform_client  # noqa: F401

from app.application.services.chatbot.intent_schemas import ChatbotIntent
from app.core.dates import school_day_bounds, school_today
from app.domain.entities.canteen import CanteenProduct
from app.infrastructure.models.models import (
    Branch,
    Parent,
    Permission,
    Role,
    Student,
    StudentParent,
    User,
)
from app.routers.ai_analytics import router as analytics_router


@pytest.fixture
async def consumer(platform_client):  # noqa: F811
    client, sessions, data = platform_client
    async with sessions() as db:
        product = CanteenProduct(branch_id=data["branch"].id, name="Acceptance", price=10)
        db.add(product)
        await db.commit()
    return client, sessions, {**data, "product": product}


def controlled_canteen(monkeypatch, *, period="today", operation="summary"):
    from app.routers import chatbot
    async def intent(query, context):
        return ChatbotIntent(intent="CANTEEN", operation=operation, period=period, confidence=1)
    monkeypatch.setattr(chatbot.intent_service, "detect_intent_with_fallback", intent)
    monkeypatch.setattr(chatbot.date_resolver, "reference_date", date(2001, 1, 1))


async def test_actual_analysis_one_route_sources_future_exclusion_and_explicit_root_workspace(consumer):
    client, sessions, data = consumer
    today = school_today()
    tomorrow = school_day_bounds(today + timedelta(days=1))[0]
    async with sessions() as db:
        child = data["children"][0]
        db.add_all([movement(child, "15"), movement(child, "20", "SALE"), movement(child, "100", "CREDIT"),
            movement(child, "999", created_at=tomorrow), movement(data["stranger"], "800"),
            order(data, "15"), order(data, "7"), order(data, "900", order_date=today + timedelta(days=1))])
        await db.commit()
    assert len([r for r in analytics_router.routes if getattr(r, "path", None) == "/api/ai/canteen-analysis"]) == 1
    result = await client.get("/api/ai/canteen-analysis?days=1", headers=headers(data["teacher"]))
    assert result.status_code == 200, result.text
    facts = result.json()["data"]
    assert facts["total_sales"] == "35.00" and facts["topup_amount"] == "100.00"
    assert facts["catalog_orders"]["amount"] == "22.00" and facts["catalog_orders"]["included_in_sales_total"] is False
    assert facts["sale_record_count"] == 2 and facts["observed_day_count"] == 1
    assert (await client.get("/api/ai/canteen-analysis", headers=headers(data["root"]))).status_code == 403
    root = {**headers(data["root"]), "X-SCS360-Organization-Id": str(data["org"].id)}
    selected = await client.get("/api/ai/canteen-analysis?days=1", headers=root)
    assert selected.status_code == 200 and selected.json()["data"]["total_sales"] == "35.00", selected.text
    for days in (0, 366, "nope"):
        assert (await client.get(f"/api/ai/canteen-analysis?days={days}", headers=headers(data["teacher"])) ).status_code == 422


async def test_native_analysis_branch_and_finance_only_permissions(consumer):
    client, sessions, data = consumer
    async with sessions() as db:
        other_branch = Branch(organization_id=data["org"].id, name="Other branch")
        db.add(other_branch)
        await db.flush()
        other = Student(organization_id=data["org"].id, branch_id=other_branch.id, first_name="Other", last_name="Branch")
        teacher = await db.get(User, data["teacher"].id, options=[selectinload(User.branches)])
        teacher.branches = [await db.get(Branch, data["branch"].id)]
        db.add(other)
        await db.flush()
        db.add_all([movement(data["children"][0], "10"), movement(other, "900")])
        await db.commit()
    response = await client.get("/api/ai/canteen-analysis", headers=headers(teacher))
    assert response.status_code == 200 and response.json()["data"]["total_sales"] == "10.00", response.text
    async with sessions() as db:
        role = (await db.execute(select(Role).where(Role.slug == "teacher").options(selectinload(Role.permissions)))).scalar_one()
        role.permissions = [Permission(code="finance.read", name="Finance", module="finance")]
        await db.commit()
    assert (await client.get("/api/ai/canteen-analysis", headers=headers(teacher))).status_code == 403


@pytest.mark.parametrize("period", ["today", None])
async def test_parent_chatbot_selected_child_fresh_date_and_working_action(consumer, monkeypatch, period):
    controlled_canteen(monkeypatch, period=period)
    client, sessions, data = consumer
    await grant_finance(sessions)
    lower, upper = school_day_bounds(school_today())
    async with sessions() as db:
        child = data["children"][0]
        db.add_all([movement(child, "15", created_at=lower), movement(child, "20", "SALE"),
            movement(child, "100", "CREDIT"), movement(child, "900", created_at=upper),
            movement(child, "800", created_at=lower - timedelta(microseconds=1)),
            movement(data["children"][1], "70"), movement(data["stranger"], "999"), order(data, "22")])
        await db.commit()
    body = {"query": "Kantin özeti", "role": "SUPER_ADMIN", "student_id": str(child.id)}
    response = await client.post("/api/parent/chatbot", headers=headers(data["user"]), json=body)
    assert response.status_code == 200, response.text
    answer = response.json()["data"]
    assert "Kayıtlı satış: 35.00 TL (2 kayıt)" in answer["response_markdown"]
    assert "Bakiye yükleme: 100.00 TL" in answer["response_markdown"]
    assert "Eski katalog siparişleri: 22.00 TL" in answer["response_markdown"]
    assert "36" not in answer["response_markdown"] and "Tahmini Net" not in answer["response_markdown"]
    assert [a["action_tag"] for a in answer["suggested_actions"]] == ["VIEW_PAYMENTS"]


async def test_parent_purpose_mixed_staff_role_and_revoked_parent_rights(consumer, monkeypatch):
    controlled_canteen(monkeypatch, operation="details")
    client, sessions, data = consumer
    await grant_finance(sessions)
    async with sessions() as db:
        teacher = await db.get(User, data["teacher"].id, options=[selectinload(User.roles)])
        teacher.roles.append((await db.execute(select(Role).where(Role.slug == "parent"))).scalar_one())
        parent = Parent(organization_id=data["org"].id, user_id=teacher.id, first_name="Staff", last_name="Parent")
        db.add(parent)
        await db.flush()
        db.add(StudentParent(parent_id=parent.id, student_id=data["children"][0].id))
        db.add_all([movement(data["children"][0], "5"), movement(data["children"][1], "900")])
        await db.commit()
    body = {"query": "Kantin detayları", "role": "SUPER_ADMIN", "student_id": str(data["children"][0].id)}
    parent_response = await client.post("/api/parent/chatbot", headers=headers(teacher), json=body)
    assert parent_response.status_code == 200 and "Kayıtlı satış: 5.00 TL" in parent_response.json()["data"]["response_markdown"], parent_response.text
    async with sessions() as db:
        role = (await db.execute(select(Role).where(Role.slug == "parent").options(selectinload(Role.permissions)))).scalar_one()
        role.permissions = [p for p in role.permissions if p.code != "parent.view_finances"]
        await db.commit()
    denied = await client.post("/api/parent/chatbot", headers=headers(teacher), json=body)
    assert denied.status_code == 200 and "yetkiniz" in denied.json()["data"]["response_markdown"], denied.text
    assert denied.json()["data"]["suggested_actions"] == []


async def test_query_failure_is_safe_503_for_actual_analysis_and_chatbot(consumer, monkeypatch):
    from app.application.services import recorded_canteen
    controlled_canteen(monkeypatch)
    client, sessions, data = consumer
    await grant_finance(sessions)
    async def failure(*args, **kwargs):
        raise SQLAlchemyError("PRIVATE SQL CONNECTION DETAILS")
    monkeypatch.setattr(recorded_canteen, "_read_summary", failure)
    responses = [await client.get("/api/ai/canteen-analysis", headers=headers(data["teacher"])),
        await client.post("/api/parent/chatbot", headers=headers(data["user"]), json={"query": "Kantin özeti", "role": "parent", "student_id": str(data["children"][0].id)})]
    assert all(r.status_code == 503 and "PRIVATE" not in r.text for r in responses), [r.text for r in responses]


async def test_staff_chatbot_detail_action_and_direct_parent_service_guard(consumer, monkeypatch):
    from app.application.services.recorded_canteen import get_recorded_canteen_summary
    from app.core.exceptions import ForbiddenException
    from app.core.tenant import TenantContext
    controlled_canteen(monkeypatch, operation="details")
    client, sessions, data = consumer
    async with sessions() as db:
        db.add(movement(data["children"][0], "12"))
        await db.commit()
        strict_parent = TenantContext(user_id=data["user"].id, organization_id=data["org"].id,
            role_slugs={"parent", "canteen_staff"}, parent_portal=True, permissions={"canteen.read"})
        with pytest.raises(ForbiddenException):
            await get_recorded_canteen_summary(db, strict_parent, purpose="chatbot")
    response = await client.post("/api/v1/chatbot/process-query", headers=headers(data["teacher"]),
        json={"query": "Kantin detayları", "role": "parent", "student_id": str(data["children"][0].id)})
    assert response.status_code == 200, response.text
    assert "Kayıtlı satış: 12.00 TL" in response.json()["data"]["response_markdown"]
    assert [a["action_tag"] for a in response.json()["data"]["suggested_actions"]] == ["VIEW_CANTEEN"]
