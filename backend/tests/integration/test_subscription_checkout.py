import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import hashlib
import hmac
import json
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from cryptography.fernet import Fernet

from test_subscription_billing import prepare  # noqa: F401
from test_saas_platform import platform_client  # noqa: F401
from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.application.services.saas_gateway import SaasGateway, get_saas_gateway
from app.core.exceptions import AppException
from app.domain.entities.saas import OrganizationSubscription, SubscriptionCheckout, SubscriptionInvoice
from app.infrastructure.models.models import AuditLog
from app.main import app


class Gateway(SaasGateway):
    def __init__(self):
        source = SimpleNamespace(APP_ENV="test", SAAS_PAYMENT_ENABLED=True, SAAS_IYZICO_API_KEY="test-platform-key", SAAS_IYZICO_SECRET_KEY="test-platform-secret",
            SAAS_IYZICO_BASE_URL="https://sandbox-api.iyzipay.com", SAAS_IYZICO_CALLBACK_URL="http://127.0.0.1:5016/api/subscription/iyzico/callback",
            SAAS_PORTAL_URL="http://127.0.0.1:5176", SAAS_CHECKOUT_ENCRYPTION_KEY=Fernet.generate_key().decode())
        super().__init__(source); self.calls = 0; self.records = {}; self.fail = False

    async def initialize(self, payload):
        self.calls += 1
        await asyncio.sleep(.03)
        if self.fail:
            raise AppException("Test provider unavailable", status_code=502)
        token = "acceptance-token-" + payload["conversationId"]
        self.records[token] = {"status": "success", "paymentStatus": "SUCCESS", "paymentId": "payment-" + payload["conversationId"],
            "token": token, "conversationId": payload["conversationId"], "basketId": payload["basketId"], "price": payload["price"], "paidPrice": payload["paidPrice"],
            "currency": payload["currency"], "fraudStatus": 1, "itemTransactions": [{"itemId": payload["basketId"], "price": payload["price"], "paymentTransactionId": "transaction-" + payload["conversationId"]}]}
        signature = hmac.new(self.settings.IYZICO_SECRET_KEY.encode(), f'{payload["conversationId"]}:{token}'.encode(), hashlib.sha256).hexdigest()
        return {"status": "success", "conversationId": payload["conversationId"], "token": token, "signature": signature,
            "paymentPageUrl": "https://sandbox-api.iyzipay.com/checkoutform/" + token, "tokenExpireTime": 1800}

    async def retrieve(self, token, conversation_id):
        result = dict(self.records[token])
        fields = ("paymentStatus", "paymentId", "currency", "basketId", "conversationId", "paidPrice", "price", "token")
        values = [format(Decimal(str(result[key])).normalize(), "f") if key in {"price", "paidPrice"} else str(result[key]) for key in fields]
        result["signature"] = hmac.new(self.settings.IYZICO_SECRET_KEY.encode(), ":".join(values).encode(), hashlib.sha256).hexdigest()
        return result


@pytest.fixture
async def checkout_client(platform_client):
    client, sessions, data = await prepare(platform_client)
    gateway = Gateway()
    previous = app.dependency_overrides.get(get_saas_gateway)
    app.dependency_overrides[get_saas_gateway] = lambda: gateway
    invoice = await client.post("/api/subscription/invoices", headers=headers(data["owner"]), json={"plan_id": data["plan"]["id"], "request_id": str(uuid4())})
    assert invoice.status_code == 200, invoice.text
    body = {"request_id": str(uuid4()), "identity_number": "11111111111", "phone": "+905000000000", "address": "Acceptance billing address", "city": "Istanbul", "country": "Turkey"}
    try:
        yield client, sessions, data, invoice.json()["data"], body, gateway
    finally:
        if previous is None: app.dependency_overrides.pop(get_saas_gateway, None)
        else: app.dependency_overrides[get_saas_gateway] = previous


async def start(values):
    client, sessions, data, invoice, body, gateway = values
    response = await client.post(f'/api/subscription/invoices/{invoice["id"]}/checkout', headers=headers(data["owner"]), json=body)
    assert response.status_code == 200, response.text
    return "acceptance-token-" + body["request_id"]


@pytest.mark.parametrize("channel", ["IOS", "ANDROID"])
async def test_native_membership_requires_configured_store_billing(checkout_client, channel):
    from sqlalchemy import func, select
    client, sessions, data, invoice, body, gateway = checkout_client
    response = await client.post(f'/api/subscription/invoices/{invoice["id"]}/checkout',
        headers=headers(data["owner"]), json={**body, "client_channel": channel})
    assert response.status_code == 409, response.text
    assert gateway.calls == 0
    async with sessions() as db:
        assert await db.scalar(select(func.count(SubscriptionCheckout.id))) == 0


async def test_web_pwa_share_original_membership_nonce_and_public_capabilities_are_honest(checkout_client):
    client, sessions, data, invoice, body, gateway = checkout_client
    path = f'/api/subscription/invoices/{invoice["id"]}/checkout'
    for channel in ["WEB", "PWA"]:
        response = await client.post(path, headers=headers(data["owner"]), json={**body, "client_channel": channel})
        assert response.status_code == 200, response.text
    assert gateway.calls == 1
    response = await client.get('/api/public/payment-capabilities')
    assert response.status_code == 200
    value = response.json()["data"]
    assert value["membership"]["IOS"] == value["membership"]["ANDROID"] == "STORE_BILLING_NOT_CONFIGURED"
    assert value["membership_and_institution_accounts_separate"] is True
    assert value["institution_collection"]["direct_bank_adapter"] == "BANK_PROTOCOL_REQUIRED"


async def test_checkout_reserves_once_encrypts_token_and_binds_retries_to_buyer(checkout_client):
    client, sessions, data, invoice, body, gateway = checkout_client
    path = f'/api/subscription/invoices/{invoice["id"]}/checkout'; auth = headers(data["owner"])
    responses = await asyncio.gather(*[client.post(path, headers=auth, json=body) for _ in range(2)])
    assert all(row.status_code in {200, 202} for row in responses), [row.text for row in responses]
    retry = await client.post(path, headers=auth, json=body)
    assert retry.status_code == 200 and retry.json()["data"]["checkout_url"].startswith("https://sandbox-api.iyzipay.com/"), retry.text
    assert gateway.calls == 1 and retry.headers["cache-control"] == "no-store"
    changed = await client.post(path, headers=auth, json={**body, "phone": "+905111111111"})
    assert changed.status_code == 409, changed.text
    assert (await client.post(path, headers=auth, json={**body, "amount": "1.00"})).status_code == 422
    assert (await client.post(f'/api/subscription/invoices/{invoice["id"]}/cancel', headers=auth)).status_code == 409
    async with sessions() as db:
        row = await db.get(SubscriptionCheckout, UUID(body["request_id"]))
        assert "acceptance-token-" not in row.checkout_secret and body["identity_number"] not in row.checkout_secret
        audit = await db.get(AuditLog, UUID(body["request_id"]))
        assert body["identity_number"] not in json.dumps(audit.new_values) and "checkout_url" not in json.dumps(audit.new_values)


async def test_verified_callback_extends_once_and_never_opens_administratively_closed_school(checkout_client):
    client, sessions, data, invoice, body, gateway = checkout_client
    token = await start(checkout_client)
    root = headers(data["root"]); org = data["tenant"]["organization_id"]
    assert (await client.patch(f"/api/platform/tenants/{org}/status", headers=root, json={"is_active": False})).status_code == 200
    results = await asyncio.gather(*[client.post("/api/subscription/iyzico/callback", data={"token": token}) for _ in range(2)])
    assert all(row.status_code == 303 for row in results), [row.text for row in results]
    assert all(token not in row.headers["location"] for row in results)
    async with sessions() as db:
        member = await db.get(OrganizationSubscription, UUID(org)); first_end = member.period_end
        assert member.admin_status == "SUSPENDED"
    repeated = await client.post("/api/subscription/iyzico/callback", data={"token": token})
    assert repeated.status_code == 303
    async with sessions() as db:
        assert (await db.get(OrganizationSubscription, UUID(org))).period_end == first_end
    assert (await client.get("/api/subscription/access", headers=headers(data["owner"]))).json()["data"]["access"]["status"] == "SUSPENDED"


async def test_fraud_review_waits_for_approval_and_cannot_be_replaced_by_manual_payment(checkout_client):
    client, sessions, data, invoice, body, gateway = checkout_client
    token = await start(checkout_client); gateway.records[token]["fraudStatus"] = 0
    path = f'/api/subscription/invoices/{invoice["id"]}/payment-status'; auth = headers(data["owner"])
    pending = await client.post(path, headers=auth)
    assert pending.status_code == 200 and pending.json()["data"]["invoice"]["status"] == "PAYMENT_REVIEW", pending.text
    blocked = await client.post(f'/api/platform/invoices/{invoice["id"]}/settle', headers=headers(data["root"]), json={"payment_reference": "SECOND-METHOD", "amount": "100.00", "currency": "TRY"})
    assert blocked.status_code == 409, blocked.text
    gateway.records[token]["fraudStatus"] = 1
    approved = await client.post(path, headers=auth)
    assert approved.status_code == 200 and approved.json()["data"]["invoice"]["status"] == "PAID", approved.text


async def test_stale_paid_quote_needs_explicit_idempotent_platform_reconciliation(checkout_client):
    client, sessions, data, invoice, body, gateway = checkout_client
    token = await start(checkout_client)
    org = UUID(data["tenant"]["organization_id"])
    async with sessions() as db:
        member = await db.get(OrganizationSubscription, org)
        member.package_snapshot = {**member.package_snapshot, "name": "Changed contract"}; await db.commit()
    paid = await client.post(f'/api/subscription/invoices/{invoice["id"]}/payment-status', headers=headers(data["owner"]))
    assert paid.status_code == 200 and paid.json()["data"]["invoice"]["status"] == "PAID_REVIEW", paid.text
    now = datetime.now(UTC)
    values = {"request_id": str(uuid4()), "action": "APPLY", "reason": "Acceptance verified reconciliation", "period_start": now.isoformat(), "period_end": (now + timedelta(days=90)).isoformat()}
    path = f'/api/platform/invoices/{invoice["id"]}/review'; root = headers(data["root"])
    assert (await client.post(path, headers=headers(data["owner"]), json=values)).status_code == 403
    first = await client.post(path, headers=root, json=values); second = await client.post(path, headers=root, json=values)
    assert first.status_code == second.status_code == 200, (first.text, second.text)
    assert first.json()["data"] == second.json()["data"]


async def test_gateway_timeout_leaves_a_retryable_record_without_expired_orm_failure(checkout_client):
    client, sessions, data, invoice, body, gateway = checkout_client
    gateway.fail = True
    response = await client.post(f'/api/subscription/invoices/{invoice["id"]}/checkout', headers=headers(data["owner"]), json=body)
    assert response.status_code == 502, response.text
    async with sessions() as db:
        attempt = await db.get(SubscriptionCheckout, UUID(body["request_id"]))
        assert attempt.status == "FAILED"


async def test_mismatched_payment_is_never_applied_and_external_refund_record_is_idempotent(checkout_client):
    client, sessions, data, invoice, body, gateway = checkout_client
    token = await start(checkout_client)
    gateway.records[token]["paidPrice"] = "1.00"
    path = f'/api/subscription/invoices/{invoice["id"]}/payment-status'
    checked = await client.post(path, headers=headers(data["owner"]))
    assert checked.status_code == 200 and checked.json()["data"]["invoice"]["status"] == "PAID_REVIEW", checked.text
    review = f'/api/platform/invoices/{invoice["id"]}/review'
    values = {"request_id": str(uuid4()), "action": "APPLY", "reason": "Acceptance mismatch must be rejected", "period_start": datetime.now(UTC).isoformat(), "period_end": (datetime.now(UTC) + timedelta(days=90)).isoformat()}
    assert (await client.post(review, headers=headers(data["root"]), json=values)).status_code == 409
    refund = {"request_id": str(uuid4()), "action": "REFUND_RECORDED", "reason": "Acceptance externally verified refund", "refund_reference": "ACCEPTANCE-ONLY-REFUND"}
    first = await client.post(review, headers=headers(data["root"]), json=refund)
    repeat = await client.post(review, headers=headers(data["root"]), json=refund)
    assert first.status_code == repeat.status_code == 200, (first.text, repeat.text)
    assert first.json()["data"]["status"] == "REFUNDED" and first.json() == repeat.json()
    altered = await client.post(review, headers=headers(data["root"]), json={**refund, "refund_reference": "DIFFERENT"})
    assert altered.status_code == 409


async def test_free_package_activation_needs_no_provider_and_is_idempotent(checkout_client):
    client, sessions, data, invoice, body, gateway = checkout_client
    path = f'/api/subscription/invoices/{invoice["id"]}/activate-free'
    assert (await client.post(path, headers=headers(data["owner"]))).status_code == 409
    async with sessions() as db:
        row = await db.get(SubscriptionInvoice, UUID(invoice["id"]))
        row.amount = Decimal("0.00")
        await db.commit()
    gateway.source.SAAS_PAYMENT_ENABLED = False
    responses = await asyncio.gather(*[client.post(path, headers=headers(data["owner"])) for _ in range(2)])
    assert all(row.status_code == 200 for row in responses), [row.text for row in responses]
    assert all(row.json()["data"]["invoice"]["status"] == "PAID" for row in responses)
    assert gateway.calls == 0


async def test_bad_provider_signature_cannot_activate_or_change_invoice(checkout_client):
    client, sessions, data, invoice, body, gateway = checkout_client
    token = await start(checkout_client)
    original = gateway.retrieve
    async def forged(value, conversation):
        result = await original(value, conversation)
        return {**result, "signature": "0" * 64}
    gateway.retrieve = forged
    response = await client.post("/api/subscription/iyzico/callback", data={"token": token})
    assert response.status_code == 400
    async with sessions() as db:
        row = await db.get(SubscriptionInvoice, UUID(invoice["id"]))
        assert row.status == "PENDING"
