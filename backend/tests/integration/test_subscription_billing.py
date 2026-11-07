import asyncio
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select

from test_saas_platform import platform_client, plan_and_tenant  # noqa: F401
from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.domain.entities.saas import OrganizationSubscription, SubscriptionInvoice
from app.infrastructure.models.models import User


async def prepare(platform_client):
    client, sessions, data = platform_client
    plan, tenant, body = await plan_and_tenant(client, data)
    async with sessions() as db:
        owner = (await db.execute(select(User).where(User.email == body["owner_email"]))).scalar_one()
    return client, sessions, {**data, "owner": owner, "tenant": tenant, "plan": plan}


async def test_subscription_invoice_uses_server_price_and_retries_do_not_duplicate(platform_client):
    client, sessions, data = await prepare(platform_client)
    auth = headers(data["owner"])
    body = {"plan_id": data["plan"]["id"], "request_id": str(uuid4())}
    responses = await asyncio.gather(*[client.post("/api/subscription/invoices", headers=auth, json=body) for _ in range(2)])
    assert all(row.status_code == 200 for row in responses), [row.text for row in responses]
    first = responses[0].json()["data"]
    assert first["id"] == responses[1].json()["data"]["id"] and Decimal(first["amount"]) == Decimal("100.00")
    assert (await client.post("/api/subscription/invoices", headers=auth, json={**body, "amount": "1.00"})).status_code == 422
    assert (await client.get("/api/subscription/invoices", headers=headers(data["user"]))).status_code == 403
    async with sessions() as db:
        assert len((await db.execute(select(SubscriptionInvoice))).scalars().all()) == 1


async def test_verified_manual_receipt_extends_once_and_reference_cannot_pay_two_invoices(platform_client):
    client, sessions, data = await prepare(platform_client)
    auth = headers(data["owner"]); root = headers(data["root"])
    body = {"plan_id": data["plan"]["id"], "request_id": str(uuid4())}
    invoice = await client.post("/api/subscription/invoices", headers=auth, json=body)
    assert invoice.status_code == 200, invoice.text
    invoice_id = invoice.json()["data"]["id"]
    paid = {"payment_reference": "BANK-ACCEPTANCE-1", "amount": "100.00", "currency": "TRY"}
    assert (await client.post(f"/api/platform/invoices/{invoice_id}/settle", headers=auth, json=paid)).status_code == 403
    wrong = await client.post(f"/api/platform/invoices/{invoice_id}/settle", headers=root, json={**paid, "amount": "1.00"})
    assert wrong.status_code == 422, wrong.text
    first = await client.post(f"/api/platform/invoices/{invoice_id}/settle", headers=root, json=paid)
    again = await client.post(f"/api/platform/invoices/{invoice_id}/settle", headers=root, json=paid)
    assert first.status_code == again.status_code == 200, (first.text, again.text)
    assert first.json()["data"] == again.json()["data"]
    async with sessions() as db:
        membership = await db.get(OrganizationSubscription, UUID(data["tenant"]["organization_id"]))
        end = membership.period_end
    second = await client.post("/api/subscription/invoices", headers=auth, json={**body, "request_id": str(uuid4())})
    assert second.status_code == 200, second.text
    duplicate = await client.post(f'/api/platform/invoices/{second.json()["data"]["id"]}/settle', headers=root, json=paid)
    assert duplicate.status_code == 409, duplicate.text
    async with sessions() as db:
        assert (await db.get(OrganizationSubscription, UUID(data["tenant"]["organization_id"]))).period_end == end


async def test_payment_does_not_reopen_closed_school_and_cancelled_quote_does_not_activate(platform_client):
    client, sessions, data = await prepare(platform_client)
    auth = headers(data["owner"]); root = headers(data["root"]); org = data["tenant"]["organization_id"]
    created = await client.post("/api/subscription/invoices", headers=auth, json={"plan_id": data["plan"]["id"], "request_id": str(uuid4())})
    assert created.status_code == 200, created.text
    identifier = created.json()["data"]["id"]
    cancelled = await client.post(f"/api/subscription/invoices/{identifier}/cancel", headers=auth)
    assert cancelled.status_code == 200, cancelled.text
    denied = await client.post(f"/api/platform/invoices/{identifier}/settle", headers=root, json={"payment_reference": "BANK-CANCELLED", "amount": "100.00", "currency": "TRY"})
    assert denied.status_code == 409, denied.text
    second = await client.post("/api/subscription/invoices", headers=auth, json={"plan_id": data["plan"]["id"], "request_id": str(uuid4())})
    assert second.status_code == 200, second.text
    assert (await client.patch(f"/api/platform/tenants/{org}/status", headers=root, json={"is_active": False})).status_code == 200
    paid = await client.post(f'/api/platform/invoices/{second.json()["data"]["id"]}/settle', headers=root,
        json={"payment_reference": "BANK-CLOSED", "amount": "100.00", "currency": "TRY"})
    assert paid.status_code == 200, paid.text
    access = await client.get("/api/subscription/access", headers=auth)
    assert access.json()["data"]["access"]["status"] == "SUSPENDED"
    assert (await client.get("/api/users", headers=auth)).status_code == 402


async def test_old_invoice_cannot_overwrite_a_revised_commercial_contract(platform_client):
    client, sessions, data = await prepare(platform_client)
    auth = headers(data["owner"]); root = headers(data["root"])
    created = await client.post("/api/subscription/invoices", headers=auth, json={"plan_id": data["plan"]["id"], "request_id": str(uuid4())})
    assert created.status_code == 200, created.text
    async with sessions() as db:
        member = await db.get(OrganizationSubscription, UUID(data["tenant"]["organization_id"]))
        member.package_snapshot = {**member.package_snapshot, "price": "200.00", "student_limit": 5}
        await db.commit()
    response = await client.post(f'/api/platform/invoices/{created.json()["data"]["id"]}/settle', headers=root,
        json={"payment_reference": "BANK-STALE", "amount": "100.00", "currency": "TRY"})
    assert response.status_code == 409, response.text
    async with sessions() as db:
        member = await db.get(OrganizationSubscription, UUID(data["tenant"]["organization_id"]))
        assert member.package_snapshot["price"] == "200.00" and member.package_snapshot["student_limit"] == 5
