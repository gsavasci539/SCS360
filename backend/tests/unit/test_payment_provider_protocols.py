import base64
import hashlib
import hmac
import json
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from app.application.services.payment_providers import HostedGateway, ProviderResponse
from app.core.config import get_settings
from app.core.exceptions import AppException


def gateway(provider, monkeypatch):
    monkeypatch.setattr(get_settings(), "APP_ENV", "test")
    return HostedGateway({"provider": provider, "environment": "SANDBOX", "organization_id": "school",
        "callback_url": f"http://127.0.0.1:8000/api/payments/{provider}/callback", "portal_url": "http://127.0.0.1:5173",
        "api_key": "synthetic-api", "secret_key": "synthetic-secret", "merchant_id": "123456",
        "merchant_key": "synthetic-merchant", "merchant_salt": "synthetic-salt", "app_id": "synthetic-app", "app_secret": "synthetic-app-secret"})


@pytest.mark.parametrize("provider", ["paytr", "craftgate", "sipay"])
async def test_hosted_provider_initialization_uses_authenticated_fixed_endpoints(provider, monkeypatch):
    adapter = gateway(provider, monkeypatch)
    identifier, basket = str(uuid4()), str(uuid4())
    requests = []

    def transport(request):
        requests.append(request)
        if provider == "paytr":
            from urllib.parse import parse_qs
            fields = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
            signed = "".join(fields[key] for key in ("merchant_id", "user_ip", "merchant_oid", "email", "payment_amount", "user_basket", "no_installment", "max_installment", "currency", "test_mode"))
            assert fields["paytr_token"] == base64.b64encode(hmac.new(b"synthetic-merchant", (signed + "synthetic-salt").encode(), hashlib.sha256).digest()).decode()
            assert fields["payment_amount"] == "1250" and fields["test_mode"] == "1"
            return httpx.Response(200, json={"status": "success", "token": "synthetic-hosted-token"})
        if provider == "craftgate":
            body = json.loads(request.content)
            assert body["price"] == 12.5 and body["conversationId"] == identifier and body["forceThreeDS"] is True
            expected = base64.b64encode(hashlib.sha256((str(request.url) + "synthetic-api" + "synthetic-secret" + request.headers["x-rnd-key"] + request.content.decode()).encode()).digest()).decode()
            assert request.headers["x-signature"] == expected and request.headers["x-idempotency-key"] == identifier
            return httpx.Response(200, json={"data": {"token": "craftgate-token", "pageUrl": "https://sandbox-checkout.craftgate.io/session"}})
        if request.url.path.endswith("/token"):
            assert json.loads(request.content)["app_id"] == "synthetic-app"
            return httpx.Response(200, json={"status_code": 100, "data": {"token": "synthetic-bearer"}})
        assert request.headers["Authorization"] == "Bearer synthetic-bearer"
        assert json.loads(json.loads(request.content)["invoice"])["total"] == "12.50"
        return httpx.Response(200, json={"status": True, "status_code": 100, "link": "https://provisioning.sipay.com.tr/ccpayment/makepayment/session"})

    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(transport), **kwargs))
    result = await adapter.initialize({"conversationId": identifier, "basketId": basket, "paidPrice": "12.50",
        "callbackUrl": adapter.settings.IYZICO_CALLBACK_URL,
        "buyer": {"name": "Synthetic", "surname": "Payer", "email": "payer@test.invalid", "ip": "127.0.0.1", "registrationAddress": "Synthetic", "gsmNumber": "5550000000", "city": "Synthetic"},
        "basketItems": [{"name": "Synthetic tuition"}]})
    assert adapter.verify_initial(result, identifier) and adapter.valid_hosted_url(result["paymentPageUrl"])
    assert not adapter.verify(dict(result)), "A callback JSON must never become authenticated server evidence"
    assert requests


def test_sipay_hash_matches_documented_aes_format_without_exposing_secret(monkeypatch):
    adapter = gateway("sipay", monkeypatch)
    value = "invoice|synthetic-merchant"
    encoded = adapter.sipay_hash(value)
    iv, salt, ciphertext = encoded.replace("__", "/").split(":", 2)
    password = hashlib.sha1(b"synthetic-app-secret").hexdigest()
    key = hashlib.sha256((password + salt).encode()).hexdigest()[:32].encode()
    decryptor = Cipher(algorithms.AES(key), modes.CBC(iv.encode())).decryptor()
    data = decryptor.update(base64.b64decode(ciphertext)) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    assert (unpadder.update(data) + unpadder.finalize()).decode() == value
    assert "synthetic-app-secret" not in encoded


@pytest.mark.parametrize("provider", ["paytr", "craftgate", "sipay"])
def test_provider_capture_requires_exact_account_reference_amount_and_currency(provider, monkeypatch):
    adapter = gateway(provider, monkeypatch)
    row = SimpleNamespace(id=uuid4(), debt_id=uuid4(), amount=Decimal("12.50"), currency="TRY")
    data = {"state": "CAPTURED", "order_id": str(row.id), "provider_payment_id": "provider-payment", "transaction_id": "provider-transaction",
        "amount": "12.50", "price": "12.50", "currency": "TRY", "basket_id": str(row.debt_id), "item_id": str(row.debt_id), "item_price": "12.50", "item_paid": "12.50"}
    result = ProviderResponse(adapter.owner, token="token", conversationId=str(row.id), normalized=data)
    assert adapter.capture_proof(result, row, "token")["matches_checkout"] is True
    for field, bad in (("currency", "EUR"), ("amount", "12.51")):
        changed = ProviderResponse(adapter.owner, token="token", conversationId=str(row.id), normalized={**data, field: bad})
        assert adapter.capture_proof(changed, row, "token")["matches_checkout"] is False
    other = HostedGateway({**adapter.values, "merchant_id": "other-account"})
    with pytest.raises(AppException):
        other.capture_proof(result, row, "token")
    with pytest.raises(AppException):
        adapter.capture_proof(ProviderResponse(adapter.owner, token="token", conversationId=str(row.id), normalized={**data, "order_id": str(uuid4())}), row, "token")


@pytest.mark.parametrize("provider", ["paytr", "craftgate", "sipay"])
async def test_definite_rejection_is_retryable_but_timeout_remains_uncertain(provider, monkeypatch):
    adapter = gateway(provider, monkeypatch)
    payload = {"conversationId": str(uuid4()), "basketId": str(uuid4()), "paidPrice": "12.50",
        "callbackUrl": adapter.settings.IYZICO_CALLBACK_URL,
        "buyer": {"name": "Synthetic", "surname": "Payer", "email": "payer@test.invalid", "ip": "127.0.0.1",
            "registrationAddress": "Synthetic", "gsmNumber": "5550000000", "city": "Synthetic"},
        "basketItems": [{"name": "Synthetic tuition"}]}
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(lambda request: httpx.Response(401, json={"error": "unauthorized"})), **kwargs))
    result = await adapter.initialize(payload)
    assert result["status"] == "failure" and result["errorCode"] == "PROVIDER_INITIALIZE_REJECTED"
    def timeout(request):
        raise httpx.ReadTimeout("Synthetic timeout", request=request)
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(timeout), **kwargs))
    with pytest.raises(AppException):
        await adapter.initialize(payload)
