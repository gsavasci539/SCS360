"""Expense writes share one scoped ledger across native and web APIs."""
import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import func, select
from test_finance_compatibility import auth, finance_client  # noqa: F401
from test_material_files import materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from test_saas_platform import platform_client  # noqa: F401
from app.infrastructure.models.models import Branch, Expense, NotificationJob, Payment, UserBranch, User


def payload(data):
    return {"branch_id": str(data["branch"].id), "category": "Synthetic category", "title": "Synthetic expense",
        "amount": "100.01", "date": "2027-01-15", "request_id": str(uuid4())}


async def test_cross_surface_cents_identity_and_soft_delete(finance_client):  # noqa: F811
    client, sessions, data = finance_client
    body = payload(data)
    created = await client.post("/api/expenses", headers=auth(data["accountant"]), json={**body, "amount": 100.01})
    assert created.status_code == 200, created.text
    row = created.json()["data"]
    assert row["id"] == body["request_id"] and row["branch_id"] == body["branch_id"]
    assert row["category"] == body["category"] and Decimal(row["amount"]) == Decimal("100.01")
    replay = await client.post("/api/finance/expenses", headers=auth(data["accountant"]), json={
        "request_id": body["request_id"], "branch_id": body["branch_id"], "description": body["title"],
        "category": body["category"], "amount": body["amount"], "expense_date": row["expense_date"]})
    assert replay.status_code == 200 and replay.json()["data"]["replayed"] is True, replay.text
    reply = await client.get("/api/finance/expenses", headers=auth(data["accountant"]))
    web = reply.json()["data"]["items"][0]
    assert web["id"] == row["id"] and web["description"] == body["title"] and web["date"] == body["date"]
    assert Decimal(web["amount"]) == Decimal("100.01")
    await client.delete(f'/api/finance/expenses/{row["id"]}', headers=auth(data["accountant"]))
    assert (await client.get("/api/expenses", headers=auth(data["accountant"]))).json()["data"] == []
    assert (await client.get("/api/finance/expenses", headers=auth(data["accountant"]))).json()["data"]["total"] == 0
    replay = await client.post("/api/expenses", headers=auth(data["accountant"]), json=body)
    assert replay.status_code == 409
    async with sessions() as db:
        assert (await db.execute(select(func.count()).select_from(Expense))).scalar_one() == 1


async def test_selected_branch_paging_and_authorization_match_on_both_apis(finance_client):  # noqa: F811
    client, sessions, data = finance_client
    async with sessions() as db:
        second = Branch(name="Synthetic other branch", organization_id=data["org"].id)
        db.add(second); await db.flush()
        for branch, count in ((data["branch"], 102), (second, 1), (data["other_branch"], 1)):
            db.add_all([Expense(organization_id=branch.organization_id, branch_id=branch.id, description="Synthetic expense",
                category="Synthetic", amount=Decimal("100.01"), expense_date=datetime(2027, 1, 15, tzinfo=UTC)) for _ in range(count)])
        await db.commit()
    for path in ("/api/expenses", "/api/finance/expenses"):
        seen = []
        for page, size in ((1, 100), (2, 2)):
            response = await client.get(path, headers=auth(data["accountant"]), params={"branch_id": str(data["branch"].id), "page": page, "page_size": 100})
            assert response.status_code == 200, response.text
            result = response.json()["data"]
            assert result["total"] == 102 and len(result["items"]) == size
            seen.extend(row["id"] for row in result["items"])
        assert len(set(seen)) == 102
        assert (await client.get(path, headers=auth(data["accountant"]), params={"branch_id": str(data["other_branch"].id)})).status_code == 404
        assert (await client.get(path, headers=auth(data["user"]))).status_code == 403
    async with sessions() as db:
        db.add(UserBranch(user_id=data["accountant"].id, branch_id=data["branch"].id)); await db.commit()
    for path in ("/api/expenses", "/api/finance/expenses"):
        assert (await client.get(path, headers=auth(data["accountant"]), params={"branch_id": str(second.id)})).status_code == 404


async def test_same_identity_race_and_invalid_money_never_duplicate_expense(finance_client):  # noqa: F811
    client, sessions, data = finance_client
    body = payload(data)
    replies = await asyncio.gather(*(client.post("/api/expenses", headers=auth(data["accountant"]), json=body) for _ in range(2)))
    assert [r.status_code for r in replies] == [200, 200], [r.text for r in replies]
    assert all(r.json()["data"]["id"] == body["request_id"] for r in replies)
    assert (await client.post("/api/expenses", headers=auth(data["accountant"]), json={**body, "amount": "100.02"})).status_code == 409
    for amount in ("100.001", "NaN", "0", "10000000000"):
        assert (await client.post("/api/expenses", headers=auth(data["accountant"]), json={**body, "request_id": str(uuid4()), "amount": amount})).status_code == 422
    async with sessions() as db:
        assert (await db.execute(select(func.count()).select_from(Expense))).scalar_one() == 1
        assert (await db.execute(select(func.count()).select_from(Payment))).scalar_one() == 0
        assert (await db.execute(select(func.count()).select_from(NotificationJob))).scalar_one() == 0


async def test_foreign_or_readonly_actor_never_writes_expense(finance_client):  # noqa: F811
    client, sessions, data = finance_client
    body = payload(data)
    assert (await client.post("/api/expenses", headers=auth(data["accountant"]), json={**body, "branch_id": str(data["other_branch"].id)})).status_code == 404
    assert (await client.post("/api/expenses", headers=auth(data["user"]), json=body)).status_code == 403
    async with sessions() as db:
        assert (await db.execute(select(func.count()).select_from(Expense))).scalar_one() == 0


async def test_branch_choices_need_finance_write_not_profile_permission(finance_client):  # noqa: F811
    client, _, data = finance_client
    path = "/api/expenses/branch-options"
    response = await client.get(path, headers=auth(data["accountant"]), params={"branch_id": str(data["branch"].id)})
    assert response.status_code == 200, response.text
    assert response.json()["data"]["items"] == [{"id": str(data["branch"].id), "name": data["branch"].name}]
    assert response.json()["data"]["allows_organization_wide"] is False
    assert (await client.get(path, headers=auth(data["accountant"]), params={"branch_id": str(data["other_branch"].id)})).status_code == 404
    assert (await client.get(path, headers=auth(data["user"]))).status_code == 403


async def test_web_invalid_updates_do_not_corrupt_canonical_mobile_rows(finance_client):  # noqa: F811
    client, _, data = finance_client
    created = (await client.post("/api/expenses", headers=auth(data["accountant"]), json=payload(data))).json()["data"]
    path = f'/api/finance/expenses/{created["id"]}'
    for patch in ({"amount": None}, {"amount": "10.001"}, {"amount": "NaN"}, {"expense_date": None}, {"description": None}, {"category": "  "}):
        reply = await client.put(path, headers=auth(data["accountant"]), json=patch)
        assert reply.status_code == 422, reply.text
    updated = await client.put(path, headers=auth(data["accountant"]), json={"amount": "110.02", "description": "Changed through web"})
    assert updated.status_code == 200, updated.text
    mobile = (await client.get("/api/expenses", headers=auth(data["accountant"]))).json()["data"][0]
    assert mobile["title"] == "Changed through web" and Decimal(mobile["amount"]) == Decimal("110.02")


async def test_web_offset_timestamp_preserves_school_calendar_day(finance_client):  # noqa: F811
    client, _, data = finance_client
    response = await client.post("/api/finance/expenses", headers=auth(data["accountant"]), json={
        "description": "Synthetic midnight expense", "category": "Synthetic", "amount": "100.01",
        "branch_id": str(data["branch"].id), "expense_date": "2027-01-15T00:00:00+03:00"})
    assert response.status_code == 200, response.text
    assert response.json()["data"]["date"] == "2027-01-15"
    mobile = (await client.get("/api/expenses", headers=auth(data["accountant"]))).json()["data"][0]
    assert mobile["date"] == "2027-01-15"


async def test_changed_body_identity_race_cannot_create_two_expenses(finance_client):  # noqa: F811
    client, sessions, data = finance_client
    body = payload(data)
    replies = await asyncio.gather(*(client.post("/api/expenses", headers=auth(data["accountant"]), json=value)
        for value in (body, {**body, "amount": "100.02"})))
    assert sorted(r.status_code for r in replies) == [200, 409], [r.text for r in replies]
    async with sessions() as db:
        assert (await db.execute(select(func.count()).select_from(Expense))).scalar_one() == 1


async def test_root_expense_stays_in_explicit_workspace_without_reassigning_operator(platform_client):  # noqa: F811
    client, sessions, data = platform_client
    headers = {**auth(data["root"]), "X-SCS360-Organization-Id": str(data["org"].id)}
    denied = await client.get("/api/expenses", headers=auth(data["root"]))
    assert denied.status_code == 403
    created = await client.post("/api/expenses", headers=headers, json=payload(data))
    assert created.status_code == 200, created.text
    row = created.json()["data"]
    assert row["organization_id"] == str(data["org"].id) and row["created_by"] == str(data["root"].id)
    listed = await client.get("/api/finance/expenses", headers=headers)
    assert [item["id"] for item in listed.json()["data"]["items"]] == [row["id"]]
    assert (await client.get("/api/expenses", headers=headers, params={"branch_id": str(data["other_branch"].id)})).status_code == 404
    async with sessions() as db:
        actor = await db.get(User, data["root"].id)
        assert actor.is_super_admin and actor.organization_id is None
