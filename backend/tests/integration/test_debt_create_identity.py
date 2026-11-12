"""Debt create retries are the same ledger operation, with no delivery/provider IO."""
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import func, select
from test_finance_compatibility import auth, finance_client  # noqa: F401
from test_material_files import materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401

from app.infrastructure.models.models import Debt, NotificationJob


def body(data):
    return {"student_id": str(data["children"][0].id), "debt_type": "EDUCATION",
        "description": "Synthetic tuition", "amount": "100.01", "due_date": "2027-01-15", "request_id": str(uuid4())}


async def test_same_create_identity_replays_without_a_second_debt(finance_client):  # noqa: F811
    client, sessions, data = finance_client
    payload = body(data)
    first = await client.post("/api/debts", headers=auth(data["accountant"]), json=payload)
    assert first.status_code == 200, first.text
    assert first.json()["data"]["id"] == payload["request_id"]
    again = await client.post("/api/debts", headers=auth(data["accountant"]), json=payload)
    assert again.status_code == 200 and again.json()["data"]["replayed"] is True, again.text
    async with sessions() as db:
        assert (await db.execute(select(func.count()).select_from(Debt))).scalar_one() == 1
        row = await db.get(Debt, UUID(payload["request_id"]))
        assert row.amount == Decimal("100.01") and row.paid_amount == 0
        assert (await db.execute(select(func.count()).select_from(NotificationJob))).scalar_one() == 0


async def test_changed_body_deleted_record_and_invalid_identity_do_not_create(finance_client):  # noqa: F811
    client, sessions, data = finance_client
    payload = body(data)
    assert (await client.post("/api/debts", headers=auth(data["accountant"]), json=payload)).status_code == 200
    for patch in ({"amount": "100.02"}, {"description": None}, {"debt_type": "FOOD"}, {"due_date": "2027-01-16"}):
        reply = await client.post("/api/debts", headers=auth(data["accountant"]), json={**payload, **patch})
        assert reply.status_code == 409, reply.text
    async with sessions() as db:
        row = await db.get(Debt, UUID(payload["request_id"]))
        row.deleted_at = datetime.now(UTC); await db.commit()
    assert (await client.post("/api/debts", headers=auth(data["accountant"]), json=payload)).status_code == 409
    assert (await client.post("/api/debts", headers=auth(data["accountant"]), json={**payload, "request_id": "bad"})).status_code == 422
    async with sessions() as db:
        assert (await db.execute(select(func.count()).select_from(Debt))).scalar_one() == 1


async def test_foreign_student_and_readonly_actor_cannot_claim_create_identity(finance_client):  # noqa: F811
    client, sessions, data = finance_client
    payload = body(data)
    assert (await client.post("/api/debts", headers=auth(data["accountant"]), json={**payload, "student_id": str(data["stranger"].id)})).status_code == 404
    assert (await client.post("/api/debts", headers=auth(data["user"]), json=payload)).status_code == 403
    async with sessions() as db:
        assert (await db.execute(select(func.count()).select_from(Debt))).scalar_one() == 0


async def test_student_choices_validate_explicit_branch(finance_client):  # noqa: F811
    client, _, data = finance_client
    reply = await client.get("/api/debts/student-options", headers=auth(data["accountant"]), params={"branch_id": str(data["branch"].id), "page_size": 100})
    assert reply.status_code == 200, reply.text
    assert {row["id"] for row in reply.json()["data"]["items"]} == {str(c.id) for c in data["children"]}
    assert all(set(row) == {"id", "name"} for row in reply.json()["data"]["items"])
    denied = await client.get("/api/debts/student-options", headers=auth(data["accountant"]), params={"branch_id": str(data["other_branch"].id)})
    assert denied.status_code == 404, denied.text


async def test_simultaneous_same_identity_creates_one_debt(finance_client):  # noqa: F811
    import asyncio
    client, sessions, data = finance_client
    payload = body(data)
    replies = await asyncio.gather(*(client.post("/api/debts", headers=auth(data["accountant"]), json=payload) for _ in range(2)))
    assert [r.status_code for r in replies] == [200, 200], [r.text for r in replies]
    assert {r.json()["data"]["id"] for r in replies} == {payload["request_id"]}
    async with sessions() as db:
        assert (await db.execute(select(func.count()).select_from(Debt))).scalar_one() == 1


async def test_simultaneous_changed_body_conflicts_instead_of_second_debt(finance_client):  # noqa: F811
    import asyncio
    client, sessions, data = finance_client
    payload = body(data)
    replies = await asyncio.gather(*(client.post("/api/debts", headers=auth(data["accountant"]), json=item)
        for item in (payload, {**payload, "amount": "100.02"})))
    assert sorted(r.status_code for r in replies) == [200, 409], [r.text for r in replies]
    async with sessions() as db:
        assert (await db.execute(select(func.count()).select_from(Debt))).scalar_one() == 1
