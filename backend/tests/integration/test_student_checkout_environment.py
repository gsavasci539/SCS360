"""A sandbox provider result must never settle real production school debt."""
from datetime import date
from decimal import Decimal
import hashlib
import hmac
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.application.services import online_payment_service as payments
from app.core.exceptions import AppException
from app.infrastructure.models.models import Debt, DebtType, Payment, PaymentCheckout, Receipt
from test_material_files import materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401


def settings(environment, host, organization_id):
    return SimpleNamespace(APP_ENV=environment, IYZICO_API_KEY="isolated-environment-test",
        IYZICO_SECRET_KEY="isolated-test-secret", IYZICO_BASE_URL=f"https://{host}",
        IYZICO_CALLBACK_URL="https://api.test.invalid/api/payments/iyzico/callback",
        IYZICO_ORGANIZATION_ID=str(organization_id), IYZICO_PAYMENT_ENABLED=True)


@pytest.mark.parametrize("environment,host,allowed", [
    ("production", "sandbox-api.iyzipay.com", False),
    ("production", "api.iyzipay.com", True),
    ("development", "sandbox-api.iyzipay.com", True),
])
def test_student_merchant_environment_gate_preserves_live_and_development(environment, host, allowed):
    school = uuid4()
    gateway = payments.IyzicoGateway(settings(environment, host, school))
    if allowed:
        gateway.configured()
    else:
        with pytest.raises(AppException) as blocked:
            gateway.configured()
        assert blocked.value.status_code == 503
    assert gateway.available_for(school) is allowed


@pytest.mark.parametrize("environment,host,allowed", [
    ("production", "sandbox-api.iyzipay.com", False),
    ("production", "api.iyzipay.com", True),
    ("development", "sandbox-api.iyzipay.com", True),
])
async def test_callback_uses_environment_gate_before_provider_and_ledger(materials_client, monkeypatch, environment, host, allowed):
    client, sessions, data = materials_client
    token = "acceptance-environment-token"
    async with sessions() as db:
        debt = Debt(organization_id=data["org"].id, branch_id=data["branch"].id,
            student_id=data["children"][0].id, debt_type=DebtType.EDUCATION,
            amount=100, paid_amount=0, due_date=date.today())
        db.add(debt); await db.flush()
        checkout = PaymentCheckout(organization_id=data["org"].id, debt_id=debt.id,
            created_by=data["user"].id, amount=25, currency="TRY", token_hash=payments.token_hash(token))
        db.add(checkout); await db.commit()
    source = settings(environment, host, data["org"].id)
    gateway_class = payments.IyzicoGateway
    monkeypatch.setattr(payments, "IyzicoGateway", lambda: gateway_class(source))
    result = {"status": "success", "paymentStatus": "SUCCESS", "paymentId": "environment-proof-001",
        "currency": "TRY", "basketId": str(debt.id), "conversationId": str(checkout.id),
        "paidPrice": "25.00", "price": "25.0", "token": token, "fraudStatus": 1}
    fields = ("paymentStatus", "paymentId", "currency", "basketId", "conversationId", "paidPrice", "price", "token")
    values = [format(Decimal(result[key]).normalize(), "f") if key in {"paidPrice", "price"} else str(result[key]) for key in fields]
    result["signature"] = hmac.new(source.IYZICO_SECRET_KEY.encode(), ":".join(values).encode(), hashlib.sha256).hexdigest()
    provider_calls = []

    class FakeReply:
        def raise_for_status(self): pass
        def json(self): return result

    class FakeClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, **kwargs):
            provider_calls.append(url)
            return FakeReply()

    # The real gateway configuration/signing/retrieve path runs; HTTP never leaves this fixture.
    monkeypatch.setattr(payments.httpx, "AsyncClient", FakeClient)
    reply = await client.post("/api/payments/iyzico/callback", data={"token": token})
    assert reply.status_code == (200 if allowed else 503), reply.text
    if allowed:
        assert reply.json()["data"]["status"] == "SUCCESS"
        repeated = await client.post("/api/payments/iyzico/callback", data={"token": token})
        assert repeated.status_code == 200 and repeated.json()["data"]["payment_id"] == reply.json()["data"]["payment_id"]
    assert len(provider_calls) == (1 if allowed else 0)
    async with sessions() as db:
        assert (await db.get(Debt, debt.id)).paid_amount == (25 if allowed else 0)
        assert await db.scalar(select(func.count(Payment.id))) == (1 if allowed else 0)
        assert await db.scalar(select(func.count(Receipt.id))) == (1 if allowed else 0)
        saved = await db.get(PaymentCheckout, checkout.id)
        assert saved.status == ("COMPLETED" if allowed else "PENDING")
