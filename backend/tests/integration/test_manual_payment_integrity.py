import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.dates import school_today
from app.infrastructure.models.models import (AuditAction, AuditLog, Debt, DebtStatus, DebtType,
    NotificationJob, Payment, PaymentCheckout, Permission, Receipt, ReceiptStatus, Role, User)
from test_finance_compatibility import finance_client, auth  # noqa: F401
from test_material_files import materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401


@pytest.fixture
async def cash_client(finance_client):
    client, sessions, data = finance_client
    # Match production, including the absence of implicit flush before SELECT.
    sessions.configure(autoflush=False)
    async with sessions() as db:
        def debt(amount, **values):
            return Debt(organization_id=data["org"].id, branch_id=data["branch"].id,
                student_id=data["children"][0].id, debt_type=DebtType.EDUCATION,
                amount=Decimal(amount), paid_amount=0, due_date=school_today() + timedelta(days=30), **values)
        selected = debt("100", description="Selected invoice")
        other = debt("50", description="Other open invoice")
        cancelled = debt("200", status=DebtStatus.CANCELLED)
        deleted = debt("300", deleted_at=datetime.now(UTC))
        foreign = Debt(organization_id=data["stranger"].organization_id, branch_id=data["other_branch"].id,
            student_id=data["stranger"].id, debt_type=DebtType.EDUCATION, amount=100, paid_amount=0,
            due_date=school_today(), description="Foreign private invoice")
        db.add_all([selected, other, cancelled, deleted, foreign]); await db.commit()
    return client, sessions, {**data, "debt": selected, "foreign_debt": foreign}


def payment_body(data, **values):
    return {"debt_id": str(data["debt"].id), "amount": "25.00", "payment_method": "CASH",
            "request_id": str(uuid4()), **values}


async def collect(client, data, body):
    return await client.post("/api/payments", headers=auth(data["accountant"]), json=body)


async def test_receipt_balance_and_retry_remain_correct_with_production_autoflush_disabled(cash_client):
    client, sessions, data = cash_client
    body = payment_body(data, notes="Original intent")
    response = await collect(client, data, body)
    assert response.status_code == 200, response.text
    saved = response.json()["data"]
    assert Decimal(saved["remaining_debt"]) == Decimal("125"), saved
    changed = await client.put(f'/api/payments/{saved["payment_id"]}', headers=auth(data["accountant"]), json={"notes": "Updated metadata"})
    assert changed.status_code == 200, changed.text
    repeated = await collect(client, data, body)
    assert repeated.status_code == 200 and repeated.json()["data"] == saved, repeated.text
    mismatch = await collect(client, data, {**body, "amount": "26.00"})
    assert mismatch.status_code == 409, mismatch.text
    async with sessions() as db:
        assert await db.scalar(select(func.count(Payment.id))) == 1
        receipt = (await db.execute(select(Receipt))).scalar_one()
        assert receipt.remaining_debt == Decimal("125") and len(receipt.receipt_number) <= 30
        assert await db.scalar(select(func.count(NotificationJob.id)).where(NotificationJob.reference_type == "payment")) == 1
        assert await db.scalar(select(func.count(AuditLog.id)).where(AuditLog.action == AuditAction.PAYMENT)) == 1


async def test_simultaneous_retries_create_one_payment_receipt_notification_and_audit(cash_client):
    client, sessions, data = cash_client
    body = payment_body(data, amount="30.00")
    replies = await asyncio.gather(collect(client, data, body), collect(client, data, body))
    assert [row.status_code for row in replies] == [200, 200], [row.text for row in replies]
    assert replies[0].json()["data"] == replies[1].json()["data"]
    async with sessions() as db:
        assert await db.scalar(select(func.count(Payment.id))) == 1
        assert await db.scalar(select(func.count(Receipt.id))) == 1
        assert (await db.get(Debt, data["debt"].id)).paid_amount == 30


async def test_simultaneous_distinct_collections_cannot_overpay_or_lose_a_balance_update(cash_client):
    client, sessions, data = cash_client
    replies = await asyncio.gather(*[collect(client, data, payment_body(data, amount="80.00")) for _ in range(2)])
    assert sorted(row.status_code for row in replies) == [200, 422], [row.text for row in replies]
    async with sessions() as db:
        debt = await db.get(Debt, data["debt"].id)
        total = await db.scalar(select(func.sum(Payment.amount)).where(Payment.cancelled_at.is_(None)))
        assert debt.paid_amount == total == Decimal("80")
        assert await db.scalar(select(func.count(Receipt.id))) == 1


async def test_invalid_financial_input_is_rejected_before_any_mutation(cash_client):
    client, sessions, data = cash_client
    for invalid in ({"debt_id": "bad"}, {"debt_id": None}, {"amount": "NaN"}, {"amount": "invalid"},
                    {"amount": -1}, {"amount": "0"}, {"amount": "0.001"}, {"amount": "10000000000.00"},
                    {"payment_method": "invalid"}, {"request_id": "bad"}, {"notes": "x" * 2001}):
        response = await collect(client, data, payment_body(data, **invalid))
        assert response.status_code == 422, (invalid, response.text)
    async with sessions() as db:
        assert await db.scalar(select(func.count(Payment.id))) == 0
        assert (await db.get(Debt, data["debt"].id)).paid_amount == 0


async def test_cancel_retries_reverse_once_and_an_old_nonce_cannot_reapply_cancelled_money(cash_client):
    client, sessions, data = cash_client
    body = payment_body(data)
    response = await collect(client, data, body)
    assert response.status_code == 200, response.text
    saved = response.json()["data"]
    path = f'/api/payments/{saved["payment_id"]}/cancel'
    replies = await asyncio.gather(*[client.post(path, headers=auth(data["accountant"]), json={"cancel_reason": "Cancellation test"}) for _ in range(2)])
    assert [row.status_code for row in replies] == [200, 200], [row.text for row in replies]
    replay = await collect(client, data, body)
    assert replay.status_code == 409, replay.text
    async with sessions() as db:
        assert (await db.get(Debt, data["debt"].id)).paid_amount == 0
        payment = await db.get(Payment, UUID(saved["payment_id"]))
        assert payment.cancelled_at is not None and payment.status == "cancelled"
        assert (await db.get(Receipt, UUID(saved["receipt_id"]))).status == ReceiptStatus.CANCELLED
        assert await db.scalar(select(func.count(AuditLog.id)).where(AuditLog.action == AuditAction.CANCEL_PAYMENT)) == 1


async def test_online_collection_cannot_be_voided_as_a_cash_refund(cash_client):
    client, sessions, data = cash_client
    response = await collect(client, data, payment_body(data, payment_method="CREDIT_CARD"))
    assert response.status_code == 200, response.text
    saved = response.json()["data"]
    async with sessions() as db:
        db.add(PaymentCheckout(organization_id=data["org"].id, debt_id=data["debt"].id,
            created_by=data["accountant"].id, amount=25, currency="TRY", status="COMPLETED",
            provider_payment_id="isolated-provider-payment", payment_id=UUID(saved["payment_id"])))
        await db.commit()
    denied = await client.post(f'/api/payments/{saved["payment_id"]}/cancel', headers=auth(data["accountant"]), json={"cancel_reason": "No provider refund"})
    assert denied.status_code == 409, denied.text
    detail = await client.get(f'/api/payments/{saved["payment_id"]}', headers=auth(data["accountant"]))
    assert detail.status_code == 200 and detail.json()["data"]["requires_provider_refund"] is True, detail.text
    async with sessions() as db:
        assert (await db.get(Payment, UUID(saved["payment_id"]))).cancelled_at is None
        assert (await db.get(Debt, data["debt"].id)).paid_amount == 25


@pytest.mark.parametrize("permission_code", ["finance.write", "finance.collect_payment"])
async def test_write_only_cashier_has_paged_searchable_debt_choices_without_registry_reads(cash_client, permission_code):
    client, sessions, data = cash_client
    async with sessions() as db:
        role = (await db.execute(select(Role).where(Role.organization_id == data["org"].id,
            Role.slug == "accountant").options(selectinload(Role.permissions)))).scalar_one()
        if permission_code == "finance.collect_payment":
            permission = Permission(code=permission_code, name=permission_code, module="finance")
            db.add(permission)
        else:
            permission = next(row for row in role.permissions if row.code == permission_code)
        role.permissions = [permission]
        db.add_all([Debt(organization_id=data["org"].id, branch_id=data["branch"].id,
            student_id=data["children"][0].id, debt_type=DebtType.EDUCATION, amount=10, paid_amount=0,
            due_date=school_today(), description=f"Invoice {index:03}") for index in range(105)])
        await db.commit()
    header = auth(data["accountant"])
    response = await client.get("/api/payments/debt-options", headers=header, params={"page": 3, "page_size": 50})
    assert response.status_code == 200, response.text
    choices = response.json()["data"]
    assert choices["total"] == 107 and choices["total_pages"] == 3 and len(choices["items"]) == 7, choices
    assert (await client.get("/api/debts", headers=header)).status_code == 403
    search = await client.get("/api/payments/debt-options", headers=header, params={"search": "Invoice 104", "selected_id": str(data["foreign_debt"].id)})
    assert search.status_code == 200 and len(search.json()["data"]["items"]) == 1, search.text
    assert search.json()["data"].get("selected") is None and "Foreign private" not in search.text
    collected = await collect(client, data, payment_body(data))
    assert collected.status_code == 200, collected.text
    if permission_code == "finance.collect_payment":
        denied = await client.post(f'/api/payments/{collected.json()["data"]["payment_id"]}/cancel', headers=header, json={})
        assert denied.status_code == 403, denied.text


async def test_nonce_reuse_by_another_actor_does_not_disclose_or_duplicate_the_original_receipt(cash_client):
    client, sessions, data = cash_client
    body = payment_body(data)
    first = await collect(client, data, body)
    assert first.status_code == 200, first.text
    async with sessions() as db:
        role = (await db.execute(select(Role).where(Role.organization_id == data["org"].id, Role.slug == "accountant"))).scalar_one()
        other = User(organization_id=data["org"].id, email="other-cashier@test.invalid", password_hash="unused",
            first_name="Other", last_name="Cashier", roles=[role])
        db.add(other); await db.commit()
    denied = await client.post("/api/payments", headers=auth(other), json=body)
    assert denied.status_code == 409 and first.json()["data"]["receipt_id"] not in denied.text, denied.text
    async with sessions() as db:
        assert await db.scalar(select(func.count(Payment.id))) == 1


async def test_corrupt_legacy_balances_do_not_generate_a_partial_payment_or_server_error(cash_client):
    client, sessions, data = cash_client
    async with sessions() as db:
        debt = await db.get(Debt, data["debt"].id)
        debt.paid_amount = Decimal("NaN") if db.bind.dialect.name == "postgresql" else Decimal("Infinity")
        await db.commit()
    response = await collect(client, data, payment_body(data))
    assert response.status_code == 422, response.text
    async with sessions() as db:
        assert await db.scalar(select(func.count(Payment.id))) == 0
        assert not (await db.get(Debt, data["debt"].id)).paid_amount.is_finite()


async def test_payment_table_returns_real_names_status_history_and_server_search(cash_client):
    client, sessions, data = cash_client
    first = await collect(client, data, payment_body(data))
    second = await collect(client, data, payment_body(data, amount="10.00"))
    assert first.status_code == second.status_code == 200
    saved = first.json()["data"]
    assert (await client.post(f'/api/payments/{saved["payment_id"]}/cancel', headers=auth(data["accountant"]), json={})).status_code == 200
    active = await client.get("/api/payments", headers=auth(data["accountant"]))
    assert active.status_code == 200 and active.json()["data"]["total"] == 1, active.text
    assert active.json()["data"]["items"][0]["student_name"] == "Child0 Test"
    history = await client.get("/api/payments", headers=auth(data["accountant"]), params={"status": "ALL", "search": "Child0 Test"})
    assert history.status_code == 200 and history.json()["data"]["total"] == 2, history.text
    assert {row["status"] for row in history.json()["data"]["items"]} == {"CANCELLED", "COMPLETED"}
    found = await client.get("/api/payments", headers=auth(data["accountant"]), params={"status": "ALL", "search": saved["receipt_number"]})
    assert found.status_code == 200 and found.json()["data"]["total"] == 1, found.text
    assert found.json()["data"]["items"][0]["id"] == saved["payment_id"]


async def test_cancel_can_repair_a_legacy_overpayment_without_reactivating_cancelled_debt(cash_client):
    client, sessions, data = cash_client
    first = await collect(client, data, payment_body(data))
    assert first.status_code == 200, first.text
    async with sessions() as db:
        debt = await db.get(Debt, data["debt"].id)
        debt.paid_amount = 125
        legacy = Payment(organization_id=data["org"].id, branch_id=data["branch"].id,
            student_id=data["children"][0].id, debt_id=debt.id, amount=100, payment_method="CASH", received_by=data["accountant"].id)
        db.add(legacy); await db.commit()
    fixed = await client.post(f"/api/payments/{legacy.id}/cancel", headers=auth(data["accountant"]), json={})
    assert fixed.status_code == 200, fixed.text
    async with sessions() as db:
        debt = await db.get(Debt, data["debt"].id)
        assert debt.paid_amount == 25
        debt.status = DebtStatus.CANCELLED
        await db.commit()
    cancelled = await client.post(f'/api/payments/{first.json()["data"]["payment_id"]}/cancel', headers=auth(data["accountant"]), json={})
    assert cancelled.status_code == 200, cancelled.text
    async with sessions() as db:
        debt = await db.get(Debt, data["debt"].id)
        assert debt.paid_amount == 0 and debt.status == DebtStatus.CANCELLED
