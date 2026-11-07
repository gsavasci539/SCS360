"""Exercise the actual gateway's signed initialize response without external HTTP."""
from decimal import Decimal
import hashlib
import hmac
import json
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select

from app.application.services import online_payment_service as payments
from app.core.dates import school_today
from app.infrastructure.models.models import Debt, DebtType, PaymentCheckout
from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401


@pytest.mark.parametrize("variant,allowed", [
    ("unsigned", False), ("forged", False), ("other-conversation", False),
    ("url-credentials", False), ("url-port", False), ("non-object", False), ("valid-uppercase", True),
])
async def test_student_checkout_requires_initial_signature_and_safe_hosted_url(materials_client, monkeypatch, variant, allowed):
    client, sessions, data = materials_client
    async with sessions() as db:
        debt = Debt(organization_id=data["org"].id, branch_id=data["branch"].id,
            student_id=data["children"][0].id, debt_type=DebtType.EDUCATION, amount=100, paid_amount=0, due_date=school_today())
        db.add(debt); await db.commit()
    source = SimpleNamespace(APP_ENV="test", IYZICO_API_KEY="initial-proof-fixture",
        IYZICO_SECRET_KEY="initial-proof-local-secret", IYZICO_BASE_URL="https://sandbox-api.iyzipay.com",
        IYZICO_CALLBACK_URL="http://127.0.0.1/api/payments/iyzico/callback",
        IYZICO_ORGANIZATION_ID=str(data["org"].id), IYZICO_PAYMENT_ENABLED=True)
    monkeypatch.setattr(payments, "get_settings", lambda: source)
    calls = []
    class FakeResponse:
        def __init__(self, result): self.result = result
        def raise_for_status(self): pass
        def json(self): return self.result
    class FakeClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, **kwargs):
            body = json.loads(kwargs["content"]); calls.append(body)
            conversation = "unrelated-checkout" if variant == "other-conversation" else body["conversationId"]
            result = {"status": "success", "conversationId": conversation, "token": "local-initial-proof-token",
                "paymentPageUrl": "https://sandbox-cpp.iyzipay.com/checkoutform/acceptance"}
            signature = hmac.new(source.IYZICO_SECRET_KEY.encode(), f"{conversation}:{result['token']}".encode(), hashlib.sha256).hexdigest()
            if variant != "unsigned": result["signature"] = "f" * 64 if variant == "forged" else signature.upper()
            if variant == "url-credentials": result["paymentPageUrl"] = "https://user:secret@sandbox-cpp.iyzipay.com/checkoutform/acceptance"
            if variant == "url-port": result["paymentPageUrl"] = "https://sandbox-cpp.iyzipay.com:444/checkoutform/acceptance"
            return FakeResponse([] if variant == "non-object" else result)
    monkeypatch.setattr(payments.httpx, "AsyncClient", FakeClient)
    reply = await client.post("/api/parent/payments/initialize", headers=headers(data["user"]), json={
        "debt_id": str(debt.id), "amount": "25.00", "buyer": {"identityNumber": "ACCEPTANCE-ONLY",
            "registrationAddress": "Isolated test address", "city": "Test", "country": "Turkey"}})
    assert reply.status_code == (200 if allowed else 502), reply.text
    assert len(calls) == 1
    async with sessions() as db:
        assert await db.scalar(select(func.count(PaymentCheckout.id))) == (1 if allowed else 0)
        assert (await db.get(Debt, debt.id)).paid_amount == Decimal("0")
    if allowed:
        assert reply.json()["data"]["payment_page_url"].startswith("https://sandbox-cpp.iyzipay.com/")
    else:
        assert "local-initial-proof-token" not in reply.text and source.IYZICO_SECRET_KEY not in reply.text


async def test_corrupt_legacy_debt_cannot_initialize_an_online_payment(materials_client, monkeypatch):
    client, sessions, data = materials_client
    async with sessions() as db:
        debt = Debt(organization_id=data["org"].id, branch_id=data["branch"].id,
            student_id=data["children"][0].id, debt_type=DebtType.EDUCATION, amount=100,
            paid_amount=Decimal("NaN") if db.bind.dialect.name == "postgresql" else Decimal("Infinity"), due_date=school_today())
        db.add(debt); await db.commit()
    class NeverProvider:
        def require_organization(self, identifier): pass
        def configured(self): pass
        async def initialize(self, payload): raise AssertionError("Invalid old debt must not reach the provider")
    monkeypatch.setattr(payments, "IyzicoGateway", NeverProvider)
    reply = await client.post("/api/parent/payments/initialize", headers=headers(data["user"]), json={
        "debt_id": str(debt.id), "amount": "25.00", "buyer": {"identityNumber": "ACCEPTANCE-ONLY",
            "registrationAddress": "Isolated test address", "city": "Test", "country": "Turkey"}})
    assert reply.status_code == 422, reply.text
    async with sessions() as db:
        assert await db.scalar(select(func.count(PaymentCheckout.id))) == 0
        assert not (await db.get(Debt, debt.id)).paid_amount.is_finite()
