import asyncio
from decimal import Decimal
from uuid import UUID, uuid4
from sqlalchemy import select

from test_saas_platform import platform_client, plan_and_tenant  # noqa: F401
from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.domain.entities.saas import OrganizationSubscription
from app.infrastructure.models.models import User


async def test_public_purchase_stays_restricted_until_verified_payment_and_retries_keep_one_account(platform_client):
    client, sessions, data = platform_client
    plan, tenant, body = await plan_and_tenant(client, data)
    public = {**body, "name": "Public School", "owner_email": "public-owner@example.com", "request_id": str(uuid4())}
    catalog = await client.get("/api/public/plans")
    assert catalog.status_code == 200 and catalog.json()["data"][0]["price"] == "100.00", catalog.text
    forbidden = await client.post("/api/public/signup", json={**public, "period_end": "2030-01-01T00:00:00Z"})
    assert forbidden.status_code == 422, forbidden.text
    first = await client.post("/api/public/signup", json=public)
    assert first.status_code == 200 and first.json()["data"]["period_end"] is None, first.text
    again = await asyncio.gather(*[client.post("/api/public/signup", json=public) for _ in range(2)])
    assert all(row.status_code == 200 and row.json()["data"] == first.json()["data"] for row in again), [row.text for row in again]
    login = await client.post("/api/auth/login", json={"email": public["owner_email"], "password": public["owner_password"]})
    assert login.status_code == 200 and login.json()["data"]["user"]["organization_access"]["status"] == "PENDING_PAYMENT", login.text
    auth = {"Authorization": "Bearer " + login.json()["data"]["access_token"]}
    assert (await client.get("/api/students", headers=auth)).status_code == 402
    assert (await client.get("/api/platform/tenants", headers=auth)).status_code in {402, 403}
    invoice = await client.post("/api/subscription/invoices", headers=auth, json={"plan_id": plan["id"], "request_id": str(uuid4())})
    assert invoice.status_code == 200 and Decimal(invoice.json()["data"]["amount"]) == Decimal("100"), invoice.text
    settled = await client.post(f'/api/platform/invoices/{invoice.json()["data"]["id"]}/settle', headers=headers(data["root"]), json={"payment_reference": "PUBLIC-ACCEPTANCE-ONLY", "amount": "100.00", "currency": "TRY"})
    assert settled.status_code == 200, settled.text
    assert (await client.get("/api/auth/me", headers=auth)).json()["data"]["organization_access"]["status"] == "ACTIVE"
    async with sessions() as db:
        owners = (await db.execute(select(User).where(User.email == public["owner_email"]))).scalars().all()
        assert len(owners) == 1 and not owners[0].is_super_admin
        membership = await db.get(OrganizationSubscription, UUID(first.json()["data"]["organization_id"]))
        assert membership.owner_user_id == owners[0].id


async def test_concurrent_public_email_collision_is_a_conflict_and_hidden_plans_are_not_purchasable(platform_client):
    client, sessions, data = platform_client
    plan, tenant, body = await plan_and_tenant(client, data)
    another = {key: value for key, value in plan.items() if key != "id"}
    another["code"] = "SECOND"; another["name"] = "Second package"
    created = await client.post("/api/platform/plans", headers=headers(data["root"]), json=another)
    assert created.status_code == 200, created.text
    second_id = created.json()["data"]["id"]
    values = {**body, "name": "Collision School", "owner_email": "collision@example.com"}
    attempts = await asyncio.gather(*[client.post("/api/public/signup", json={**values, "name": "Collision " + identifier[:8], "plan_id": identifier, "request_id": str(uuid4())}) for identifier in (plan["id"], second_id)])
    assert sorted(row.status_code for row in attempts) == [200, 409], [row.text for row in attempts]
    changed = await client.put(f"/api/platform/plans/{second_id}", headers=headers(data["root"]), json={**another, "is_active": False})
    assert changed.status_code == 200, changed.text
    catalog = await client.get("/api/public/plans")
    assert second_id not in {row["id"] for row in catalog.json()["data"]}
    blocked = await client.post("/api/public/signup", json={**values, "owner_email": "closed-plan@example.com", "plan_id": second_id, "request_id": str(uuid4())})
    assert blocked.status_code == 409, blocked.text
