"""Actual school checkout APIs with an isolated signed provider adapter."""
import asyncio
from datetime import date
from decimal import Decimal
import hashlib
import hmac
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from app.application.services.online_payment_service import IyzicoGateway
from app.core.exceptions import AppException
from app.infrastructure.models.models import (AuditAction, AuditLog, Debt, DebtType, NotificationJob, Parent,
    Payment, PaymentCheckout, Permission, Receipt, Role, StudentParent, User)
from test_school_payment_merchants import merchant_client, body as merchant_body, configure  # noqa: F401
from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401


def sign(values, secret):
    fields = ("paymentStatus", "paymentId", "currency", "basketId", "conversationId", "paidPrice", "price", "token")
    parts = [format(Decimal(str(values[key])).normalize(), "f") if key in {"paidPrice", "price"} else str(values.get(key, "")) for key in fields]
    return hmac.new(secret.encode(), ":".join(parts).encode(), hashlib.sha256).hexdigest()


class Provider:
    def __init__(self):
        self.attempts, self.initialized, self.retrieved = {}, [], []
        self.lose_initial_response = False
        self.reject_initial = False

    async def post(self, gateway, path, payload):
        identifier = payload["conversationId"]
        secret = gateway.settings.IYZICO_SECRET_KEY
        if "initialize" in path:
            self.initialized.append(identifier)
            if self.reject_initial:
                return {"status": "failure", "errorCode": "ACCEPTANCE-REJECTED", "errorMessage": "Isolated definitive rejection"}
            token = "school-token-" + identifier
            result = {"status": "success", "paymentStatus": "SUCCESS", "paymentId": "same-provider-reference",
                "currency": payload["currency"], "basketId": payload["basketId"], "conversationId": identifier,
                "paidPrice": payload["paidPrice"], "price": payload["price"], "token": token, "fraudStatus": 1,
                "itemTransactions": [{"itemId": payload["basketId"], "price": payload["price"], "paidPrice": payload["paidPrice"],
                    "transactionStatus": 1, "paymentTransactionId": "transaction-"+identifier}]}
            self.attempts[identifier] = {"token": token, "secret": secret, "result": result, "payload": payload}
            await asyncio.sleep(0.02)
            if self.lose_initial_response:
                raise AppException("Isolated lost provider response", status_code=502)
            return {"status": "success", "conversationId": identifier, "token": token,
                "signature": hmac.new(secret.encode(), f"{identifier}:{token}".encode(), hashlib.sha256).hexdigest(),
                "paymentPageUrl": "https://sandbox-cpp.iyzipay.com/checkout/"+token, "tokenExpireTime": 1800}
        saved = self.attempts[identifier]
        assert saved["token"] == payload["token"] and saved["secret"] == secret
        self.retrieved.append(identifier)
        result = {**saved["result"]}
        return {**result, "signature": sign(result, secret)}


@pytest.fixture
async def school_checkout_client(merchant_client, monkeypatch):
    client, sessions, data = merchant_client
    configured = await configure(client, data["user"], merchant_body())
    assert configured.status_code == 200, configured.text
    provider = Provider()
    async def fake_post(gateway, path, payload): return await provider.post(gateway, path, payload)
    monkeypatch.setattr(IyzicoGateway, "post", fake_post)
    async with sessions() as db:
        debt = Debt(organization_id=data["org"].id, branch_id=data["branch"].id, student_id=data["children"][0].id,
            debt_type=DebtType.EDUCATION, amount=100, paid_amount=0, due_date=date(2026, 11, 5))
        sibling = Debt(organization_id=data["org"].id, branch_id=data["branch"].id, student_id=data["children"][0].id,
            debt_type=DebtType.EDUCATION, amount=50, paid_amount=0, due_date=date(2026, 12, 5))
        db.add_all([debt, sibling]); await db.commit()
    return client, sessions, {**data, "debt": debt, "merchant": configured.json()["data"]}, provider


def payment(data, **values):
    return {"request_id": str(uuid4()), "debt_id": str(data["debt"].id), "amount": "25.00", "currency": "TRY",
        "buyer": {"identityNumber": "ACCEPTANCE-ONLY", "registrationAddress": "Acceptance billing address", "city": "Istanbul", "country": "Turkey"}, **values}


async def start(client, data, request):
    return await client.post("/api/parent/payments/initialize", headers=headers(data["user"]), json=request)


async def callback(client, provider, identifier, **kwargs):
    return await client.post("/api/payments/iyzico/callback", params={"checkout_id": identifier},
        data={"token": provider.attempts[identifier]["token"]}, **kwargs)


async def test_checkout_reserves_same_nonce_once_and_replays_original_resume(school_checkout_client):
    client, sessions, data, provider = school_checkout_client
    request = payment(data)
    replies = await asyncio.gather(start(client, data, request), start(client, data, request))
    assert all(reply.status_code == 200 for reply in replies), [reply.text for reply in replies]
    assert {reply.json()["data"]["conversation_id"] for reply in replies} == {request["request_id"]}
    repeated = await start(client, data, request)
    assert repeated.status_code == 200 and repeated.json()["data"]["checkout_url"].startswith("https://sandbox-cpp.iyzipay.com/"), repeated.text
    assert provider.initialized == [request["request_id"]]
    changed = await start(client, data, {**request, "amount": "26.00"})
    assert changed.status_code == 409, changed.text
    other_actor = await client.post("/api/payments/iyzico/initialize", headers=headers(data["finance"]), json=request)
    assert other_actor.status_code == 409, other_actor.text
    async with sessions() as db:
        assert await db.scalar(select(func.count(PaymentCheckout.id))) == 1
        row = (await db.execute(select(PaymentCheckout))).scalar_one()
        assert row.request_digest and row.merchant_snapshot and row.checkout_secret
        assert provider.attempts[request["request_id"]]["token"] not in row.checkout_secret


async def test_rotated_disabled_merchant_callback_uses_old_snapshot_and_whole_student_balance(school_checkout_client):
    client, sessions, data, provider = school_checkout_client
    request = payment(data)
    first = await start(client, data, request)
    assert first.status_code == 200, first.text
    rotated = await configure(client, data["user"], merchant_body(expected_revision=data["merchant"]["revision"], secret_key="rotated-during-checkout"))
    assert rotated.status_code == 200, rotated.text
    disabled = await configure(client, data["user"], merchant_body(expected_revision=rotated.json()["data"]["revision"], enabled=False, api_key=None, secret_key=None))
    assert disabled.status_code == 200, disabled.text
    a = await callback(client, provider, request["request_id"])
    b = await callback(client, provider, request["request_id"])
    assert a.status_code == b.status_code == 200, (a.text, b.text)
    async with sessions() as db:
        assert (await db.get(Debt, data["debt"].id)).paid_amount == 25
        assert await db.scalar(select(func.count(Payment.id))) == 1
        assert (await db.execute(select(Receipt))).scalar_one().remaining_debt == 125
        assert await db.scalar(select(func.count(NotificationJob.id)).where(NotificationJob.reference_type == "payment")) == 1
        assert await db.scalar(select(func.count(AuditLog.id)).where(AuditLog.action == AuditAction.PAYMENT)) == 1


async def test_lost_initialize_response_stays_reserved_and_late_callback_returns_to_parent(school_checkout_client):
    client, sessions, data, provider = school_checkout_client
    provider.lose_initial_response = True
    request = payment(data)
    lost = await start(client, data, request)
    assert lost.status_code == 502, lost.text
    status = await client.get(f'/api/parent/payments/checkouts/{request["request_id"]}', headers=headers(data["user"]))
    assert status.status_code == 200 and status.json()["data"]["status"] == "INITIALIZING", status.text
    assert "school-token-" not in status.text and "acceptance-school-secret" not in status.text
    retry = await start(client, data, request)
    assert retry.status_code == 200 and provider.initialized == [request["request_id"]], retry.text
    returned = await callback(client, provider, request["request_id"], headers={"Accept": "text/html"}, follow_redirects=False)
    assert returned.status_code == 303, returned.text
    assert returned.headers["location"] == f'https://portal.test.invalid/parent/finances?checkout={request["request_id"]}'
    async with sessions() as db:
        row = await db.get(PaymentCheckout, UUID(request["request_id"]))
        assert row.status == "COMPLETED" and row.token_hash
        assert await db.scalar(select(func.count(Payment.id))) == 1


async def test_other_guardian_cannot_read_or_resume_and_finance_read_is_metadata_only(school_checkout_client):
    client, sessions, data, provider = school_checkout_client
    request = payment(data)
    assert (await start(client, data, request)).status_code == 200
    async with sessions() as db:
        parent_role = (await db.execute(select(Role).where(Role.slug == "parent"))).scalar_one()
        read_permission = (await db.execute(select(Permission).where(Permission.code == "finance.read"))).scalar_one()
        other = User(email="second-parent-v2@test.invalid", password_hash="unused", first_name="Second", last_name="Parent", organization_id=data["org"].id, roles=[parent_role])
        reader = User(email="read-finance-v2@test.invalid", password_hash="unused", first_name="Read", last_name="Finance", organization_id=data["org"].id,
            roles=[Role(name="Read finance", slug="read_finance", organization_id=data["org"].id, permissions=[read_permission])])
        db.add_all([other, reader]); await db.flush()
        contact = Parent(user_id=other.id, organization_id=data["org"].id, first_name="Second", last_name="Parent")
        db.add(contact); await db.flush(); db.add(StudentParent(parent_id=contact.id, student_id=data["children"][0].id)); await db.commit()
    identifier = request["request_id"]
    assert (await client.get(f"/api/parent/payments/checkouts/{identifier}", headers=headers(other))).status_code == 403
    for action in ("resume", "refresh"):
        assert (await client.post(f"/api/parent/payments/checkouts/{identifier}/{action}", headers=headers(other))).status_code == 403
        assert (await client.post(f"/api/payments/iyzico/checkouts/{identifier}/{action}", headers=headers(reader))).status_code == 403
    metadata = await client.get(f"/api/payments/iyzico/checkouts/{identifier}", headers=headers(reader))
    assert metadata.status_code == 200 and not metadata.json()["data"]["can_resume"] and not metadata.json()["data"]["can_refresh"], metadata.text
    assert "school-token-" not in metadata.text
    resume = await client.post(f"/api/payments/iyzico/checkouts/{identifier}/resume", headers=headers(data["finance"]))
    assert resume.status_code == 200 and resume.json()["data"]["can_resume"] is True, resume.text


@pytest.mark.parametrize("mismatch", ["amount", "currency", "item"])
async def test_signed_mismatch_preserves_review_evidence_without_ledger(school_checkout_client, mismatch):
    client, sessions, data, provider = school_checkout_client
    request = payment(data)
    assert (await start(client, data, request)).status_code == 200
    saved = provider.attempts[request["request_id"]]["result"]
    if mismatch == "amount": saved.update(price="26.00", paidPrice="26.00")
    elif mismatch == "currency": saved["currency"] = "USD"
    else: saved["itemTransactions"][0]["itemId"] = str(uuid4())
    response = await callback(client, provider, request["request_id"])
    assert response.status_code == 200 and response.json()["data"]["status"] == "PAID_REVIEW", response.text
    async with sessions() as db:
        row = await db.get(PaymentCheckout, UUID(request["request_id"]))
        assert row.provider_payment_id == "same-provider-reference" and row.paid_amount and row.paid_currency
        assert row.verified_metadata and row.verified_metadata["matches_checkout"] is False
        assert "school-token-" not in str(row.verified_metadata)
        assert (await db.get(Debt, data["debt"].id)).paid_amount == 0
        assert await db.scalar(select(func.count(Payment.id))) == 0
        assert await db.scalar(select(func.count(Receipt.id))) == 0


async def test_late_fraud_callback_adopts_token_for_later_authorized_refresh(school_checkout_client):
    from app.application.services.school_payment_merchant import open_school_secret
    client, sessions, data, provider = school_checkout_client
    provider.lose_initial_response = True
    request = payment(data)
    assert (await start(client, data, request)).status_code == 502
    provider.attempts[request["request_id"]]["result"]["fraudStatus"] = 0
    reviewed = await callback(client, provider, request["request_id"])
    assert reviewed.status_code == 200, reviewed.text
    async with sessions() as db:
        row = await db.get(PaymentCheckout, UUID(request["request_id"]))
        assert row.status == "FRAUD_REVIEW" and not row.payment_id
        values = open_school_secret(row.checkout_secret)
        assert values["token"] == provider.attempts[request["request_id"]]["token"]
        assert values["return_path"] == f'/parent/finances?checkout={request["request_id"]}'
    provider.attempts[request["request_id"]]["result"]["fraudStatus"] = 1
    refreshed = await client.post(f'/api/parent/payments/checkouts/{request["request_id"]}/refresh', headers=headers(data["user"]))
    assert refreshed.status_code == 200 and refreshed.json()["data"]["status"] == "COMPLETED", refreshed.text
    assert provider.initialized == [request["request_id"]]
    async with sessions() as db:
        assert await db.scalar(select(func.count(Payment.id))) == 1


async def test_definitive_initialize_rejection_is_failed_and_new_request_can_start(school_checkout_client):
    client, sessions, data, provider = school_checkout_client
    provider.reject_initial = True
    request = payment(data)
    rejected = await start(client, data, request)
    assert rejected.status_code == 200 and rejected.json()["data"]["status"] == "FAILED", rejected.text
    async with sessions() as db:
        row = await db.get(PaymentCheckout, UUID(request["request_id"]))
        assert row.status == "FAILED" and row.token_hash is None and not row.payment_id
        assert await db.scalar(select(func.count(Payment.id))) == 0
    provider.reject_initial = False
    second = payment(data)
    created = await start(client, data, second)
    assert created.status_code == 200 and created.json()["data"]["status"] == "PENDING", created.text
    assert provider.initialized == [request["request_id"], second["request_id"]]
