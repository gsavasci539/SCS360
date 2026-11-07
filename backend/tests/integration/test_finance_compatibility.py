from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import select

from test_material_files import materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.core.security import create_access_token
from app.infrastructure.models.models import (Debt, NotificationJob, NotificationStatus, Parent, Permission,
    Role, User, Payment, Receipt, ReceiptStatus)


def auth(user):
    return {"Authorization": "Bearer " + create_access_token(user.id)}


@pytest.fixture
async def finance_client(materials_client):
    client, sessions, data = materials_client
    async with sessions() as db:
        role = Role(name="Finance", slug="accountant", organization_id=data["org"].id,
            permissions=[Permission(code=code, name=code, module=code.split('.')[0]) for code in ("finance.read", "finance.write", "receipt.read")])
        user = User(first_name="Accountant", last_name="Test", email="accountant@test.invalid", password_hash="unused",
            organization_id=data["org"].id, roles=[role])
        db.add(user)
        parent = (await db.execute(select(Parent).where(Parent.user_id == data["user"].id))).scalar_one()
        parent.email = "parent@test.invalid"
        await db.commit()
    yield client, sessions, {**data, "accountant": user}


async def generate(client, data):
    response = await client.post("/api/payments/finances/invoices/generate-plan", headers=auth(data["accountant"]),
        json={"student_id": str(data["children"][0].id), "total_amount": "100.00", "down_payment": "0",
            "installment_count": 3, "first_due_date": "2027-01-31", "category": "EDUCATION"})
    assert response.status_code == 200, response.text
    return response.json()["data"]


async def test_plan_preserves_cents_and_calendar_months(finance_client):
    client, sessions, data = finance_client
    plan = await generate(client, data)
    assert [row["due_date"] for row in plan["invoices"]] == ["2027-01-31", "2027-02-28", "2027-03-31"]
    assert sum(Decimal(row["amount"]) for row in plan["invoices"]) == Decimal("100")
    assert plan["installment_amounts"] == ["33.34", "33.33", "33.33"]
    async with sessions() as db:
        debts = (await db.execute(select(Debt))).scalars().all()
        assert len(debts) == 3 and all(row.branch_id == data["branch"].id for row in debts)
    bad = await client.post("/api/payments/finances/invoices/generate-plan", headers=auth(data["accountant"]),
        json={"student_id": str(data["children"][0].id), "total_amount": "100", "down_payment": "101",
            "installment_count": 3, "first_due_date": "2027-01-31", "category": "EDUCATION"})
    assert bad.status_code == 422


async def test_legacy_collection_pdf_and_delete_use_the_canonical_ledger(finance_client):
    client, sessions, data = finance_client
    debt = (await generate(client, data))["invoices"][0]
    response = await client.post("/api/payments/finances/payments/collect", headers=auth(data["accountant"]),
        json={"invoice_id": debt["id"], "amount": "10.01", "payment_method": "CASH", "transaction_ref": "REF-TEST"})
    assert response.status_code == 200, response.text
    payment_id = response.json()["data"]["payment_id"]
    pdf_path = f"/api/payments/finances/payments/{payment_id}/receipt-pdf"
    pdf = await client.get(pdf_path, headers=auth(data["accountant"]))
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF-")
    assert pdf.headers["content-type"] == "application/pdf" and pdf.headers["cache-control"] == "private, no-store"
    assert (await client.put(f"/api/payments/{payment_id}", headers=auth(data["accountant"]), json={"amount": "12.00"})).status_code == 422
    updated = await client.put(f"/api/payments/{payment_id}", headers=auth(data["accountant"]), json={"notes": "Muhasebe notu"})
    assert updated.status_code == 200, updated.text
    async with sessions() as db:
        assert (await db.get(Debt, UUID(debt["id"]))).paid_amount == Decimal("10.01")
    cancelled = await client.delete(f"/api/payments/{payment_id}", headers=auth(data["accountant"]))
    assert cancelled.status_code == 200, cancelled.text
    async with sessions() as db:
        assert (await db.get(Debt, UUID(debt["id"]))).paid_amount == 0
        assert (await db.get(Payment, UUID(payment_id))).cancelled_at is not None
        assert (await db.execute(select(Receipt).where(Receipt.payment_id == UUID(payment_id)))).scalar_one().status == ReceiptStatus.CANCELLED
    pdf = await client.get(pdf_path, headers=auth(data["accountant"]))
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF-")
    printed = await client.get(f'/api/receipts/{response.json()["data"]["receipt_id"]}/print', headers=auth(data["accountant"]))
    assert "İPTAL EDİLMİŞ MAKBUZ" in printed.text


async def test_reminders_queue_real_recipients_and_never_claim_sent(finance_client):
    client, sessions, data = finance_client
    plan = await generate(client, data)
    ids = [plan["invoices"][0]["id"]] * 2
    path = "/api/payments/finances/reminders/send"
    response = await client.post(path, headers=auth(data["accountant"]), json={"invoice_ids": ids, "channel": "EMAIL"})
    assert response.status_code == 200, response.text
    result = response.json()["data"]
    assert result["total_sent"] == 0 and result["total_queued"] == 1 and result["reminders"][0]["status"] == "QUEUED"
    async with sessions() as db:
        jobs = (await db.execute(select(NotificationJob).where(NotificationJob.reference_type == "DEBT_REMINDER"))).scalars().all()
        assert len(jobs) == 1 and jobs[0].status == NotificationStatus.PENDING
    assert (await client.post(path, headers=auth(data["accountant"]), json={"invoice_ids": ids, "channel": "PUSH"})).status_code == 422
    assert (await client.post(path, headers=auth(data["user"]), json={"invoice_ids": ids, "channel": "EMAIL"})).status_code == 403
