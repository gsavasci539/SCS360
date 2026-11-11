import base64
import hashlib
import hmac
from datetime import date
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from test_material_files import headers, materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from test_school_payment_merchants import merchant_client  # noqa: F401

from app.application.services import school_payment_merchant
from app.application.services.payment_providers import FIELDS, HostedGateway
from app.infrastructure.models.models import (
    AuditLog,
    Debt,
    DebtType,
    Payment,
    PaymentCheckout,
    SchoolPaymentMerchant,
)


def setup_body(provider, **values):
    return {"request_id": str(uuid4()), "expected_revision": None, "provider": provider,
        "environment": "LIVE", "enabled": True,
        "credentials": {field: "123456" if field == "merchant_id" else "synthetic-" + field for field in FIELDS[provider]}, **values}


@pytest.mark.parametrize("provider", ["paytr", "craftgate", "sipay"])
async def test_provider_accounts_are_scoped_encrypted_and_keep_original_checkout_account(merchant_client, monkeypatch, provider):  # noqa: F811
    client, sessions, data = merchant_client
    request = setup_body(provider)
    response = await client.put("/api/payments/merchant", headers=headers(data["user"]), json=request)
    assert response.status_code == 200, response.text
    status = response.json()["data"]
    assert status["provider"] == provider and status["available"] is True and status["provider_acceptance_verified"] is False
    assert all(status["credential_status"].values())
    assert "synthetic-" not in response.text
    assert (await client.put("/api/payments/merchant", headers=headers(data["user"]), json=request)).json()["data"] == status
    assert (await client.put("/api/payments/merchant", headers=headers(data["finance"]), json=setup_body(provider))).status_code == 403
    async with sessions() as db:
        merchant = (await db.execute(select(SchoolPaymentMerchant))).scalar_one()
        assert "synthetic-" not in merchant.credentials_ciphertext
        debt = Debt(organization_id=data["org"].id, branch_id=data["branch"].id, student_id=data["children"][0].id,
            debt_type=DebtType.EDUCATION, amount=100, paid_amount=0, due_date=date(2026, 12, 10))
        db.add(debt)
        await db.commit()
    attempts = {}

    async def provider_api(adapter, method, path, payload=None, **kwargs):
        if path.endswith("/token"):
            return {"status_code": 100, "data": {"token": "synthetic-token"}}
        if "get-token" in path:
            return {"status": "success", "token": "synthetic-iframe"}
        if path.endswith("/init"):
            attempts["basket"] = payload["externalId"]
            attempts["identifier"] = payload["conversationId"]
            return {"data": {"token": "synthetic-craft-token", "pageUrl": "https://checkout.craftgate.io/synthetic-session"}}
        if path.endswith("/purchase/link"):
            return {"status": True, "status_code": 100, "link": "https://app.sipay.com.tr/ccpayment/makepayment/synthetic-session"}
        if "durum-sorgu" in path:
            return {"status": "success", "payment_date": "2026-11-11", "payment_amount": "25.00", "payment_total": "25.00", "currency": "TL", "test_mode": "0", "returns": []}
        if "checkout-payments/" in path:
            return {"data": {"id": 123, "conversationId": attempts["identifier"], "externalId": attempts["basket"], "price": 25, "paidPrice": 25,
                "currency": "TRY", "paymentStatus": "SUCCESS", "paymentPhase": "AUTH", "paymentTransactions": [{"id": 456, "externalId": attempts["basket"],
                    "price": 25, "paidPrice": 25, "transactionStatus": "APPROVED"}]}}
        return {"status_code": 100, "transaction_status": "Completed", "transaction_type": "Auth", "invoice_id": payload["invoice_id"],
            "order_id": "sipay-order", "transaction_id": "sipay-transaction", "transaction_amount": 25, "product_price": 25, "currency_code": "TRY", "total_refunded_amount": 0}

    monkeypatch.setattr(HostedGateway, "request", provider_api)
    payment = {"request_id": str(uuid4()), "debt_id": str(debt.id), "amount": "25.00", "currency": "TRY", "payment_channel": "MOBILE",
        "buyer": {"identityNumber": "SYNTHETIC-ONLY", "registrationAddress": "Synthetic address", "city": "Synthetic", "country": "Turkey", "gsmNumber": "5550000000"}}
    started = await client.post("/api/payments/online/initialize", headers=headers(data["finance"]), json=payment)
    assert started.status_code == 200, started.text
    identifier = UUID(started.json()["data"]["conversation_id"])
    async with sessions() as db:
        checkout = await db.get(PaymentCheckout, identifier)
        original = school_payment_merchant.open_school_secret(checkout.merchant_snapshot)
        assert original["provider"] == provider and original["version"] == 2
        stored = school_payment_merchant.open_school_secret(checkout.checkout_secret)
    browser = await client.get(f"/api/payments/{provider}/callback", params={"checkout_id": str(identifier), "callback_key": stored["callback_key"], "status": "success"})
    assert browser.status_code == 303
    async with sessions() as db:
        assert await db.scalar(select(func.count(Payment.id))) == 0, "Browser success navigation must never settle"
    replacement = setup_body("iyzico", expected_revision=status["revision"], replace_account=True)
    changed = await client.put("/api/payments/merchant", headers=headers(data["user"]), json=replacement)
    assert changed.status_code == 200 and changed.json()["data"]["provider"] == "iyzico", changed.text
    if provider == "paytr":
        fields = {"merchant_oid": identifier.hex, "status": "success", "total_amount": "2500"}
        material = identifier.hex + "synthetic-merchant_salt" + "success" + "2500"
        fields["hash"] = base64.b64encode(hmac.new(b"synthetic-merchant_key", material.encode(), hashlib.sha256).digest()).decode()
        bad = await client.post("/api/payments/paytr/callback", data={**fields, "hash": "bad"})
        assert bad.status_code == 403
        for _ in range(2):
            reply = await client.post("/api/payments/paytr/callback", data=fields)
            assert reply.status_code == 200 and reply.text == "OK", reply.text
    else:
        fields = {"token": "synthetic-craft-token"} if provider == "craftgate" else {"invoice_id": identifier.hex, "status": "1"}
        bad = await client.post(f"/api/payments/{provider}/callback", params={"checkout_id": str(identifier), "callback_key": "bad"}, data=fields)
        assert bad.status_code == 403
        called = await client.post(f"/api/payments/{provider}/callback", params={"checkout_id": str(identifier), "callback_key": stored["callback_key"]}, data=fields)
        assert called.status_code == 303, called.text
        for _ in range(2):
            reply = await client.post(f"/api/payments/online/checkouts/{identifier}/refresh", headers=headers(data["finance"]))
            assert reply.status_code == 200 and reply.json()["data"]["status"] == "COMPLETED", reply.text
    async with sessions() as db:
        assert await db.scalar(select(func.count(Payment.id))) == 1
        assert (await db.get(Debt, debt.id)).paid_amount == 25
        checkout = await db.get(PaymentCheckout, identifier)
        assert checkout.verified_metadata["provider"] == provider
        assert "synthetic-" not in str((await db.execute(select(AuditLog.new_values))).scalars().all())
