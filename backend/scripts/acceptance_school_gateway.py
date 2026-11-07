"""Signed, memory-only school provider for the disposable browser runner."""
import hashlib
import hmac
import os
import secrets
from decimal import Decimal

from cryptography.fernet import Fernet
from sqlalchemy import select


async def install():
    database = os.environ.get("DATABASE_URL", "")
    if (os.environ.get("SCS360_ACCEPTANCE_SCHOOL_GATEWAY") != "1" or os.environ.get("APP_ENV") != "test"
        or not ("scs360_acceptance_browser_" in database or "scs360-acceptance-" in database)):
        raise RuntimeError("Fake school payments require the disposable browser database and explicit opt-in")
    from app.application.services.online_payment_service import IyzicoGateway
    from app.core.config import get_settings
    from app.core.database import AsyncSessionLocal, engine
    from app.infrastructure.models.models import User
    async with AsyncSessionLocal() as db:
        organization_id = await db.scalar(select(User.organization_id).where(User.email == "accountant@acceptance.example.com"))
    await engine.dispose()
    if organization_id is None:
        raise RuntimeError("The disposable school must be seeded before installing its fake gateway")
    settings = get_settings()
    settings.IYZICO_PAYMENT_ENABLED = True
    settings.IYZICO_ORGANIZATION_ID = str(organization_id)
    settings.IYZICO_API_KEY = secrets.token_hex(24)
    settings.IYZICO_SECRET_KEY = secrets.token_hex(32)
    settings.IYZICO_BASE_URL = "https://sandbox-api.iyzipay.com"
    settings.IYZICO_CALLBACK_URL = "http://127.0.0.1:5016/api/payments/iyzico/callback"
    settings.SCHOOL_PAYMENT_ENCRYPTION_KEY = Fernet.generate_key().decode()
    settings.SCHOOL_PAYMENT_CALLBACK_URL = settings.IYZICO_CALLBACK_URL
    settings.SCHOOL_PAYMENT_PORTAL_URL = "http://127.0.0.1:5176"
    provider = FakeIyzicoGateway(organization_id, settings.IYZICO_API_KEY, settings.IYZICO_SECRET_KEY)
    async def fake_post(gateway, path, payload):
        return await provider.post(gateway, path, payload)
    # Inherited SchoolGateway.post also stays memory-only when a snapshot is opened.
    IyzicoGateway.post = fake_post


class FakeIyzicoGateway:
    def __init__(self, organization_id, api_key, secret_key):
        self.organization_id, self.api_key, self.secret_key = str(organization_id), api_key, secret_key
        self.records = {}

    async def post(self, gateway, path, payload):
        gateway.configured()
        if (str(gateway.settings.IYZICO_ORGANIZATION_ID) != self.organization_id
            or gateway.settings.IYZICO_API_KEY != self.api_key or gateway.settings.IYZICO_SECRET_KEY != self.secret_key):
            raise RuntimeError("The fake provider is bound only to the disposable school")
        identifier = payload["conversationId"]
        if path.endswith("/initialize/auth/ecom"):
            token = "school-browser-" + identifier
            self.records[token] = {"status": "success", "paymentStatus": "SUCCESS", "fraudStatus": 1,
                "paymentId": "school-browser-" + identifier, "token": token, "conversationId": identifier,
                "basketId": payload["basketId"], "currency": payload["currency"], "price": payload["price"],
                "paidPrice": payload["paidPrice"], "itemTransactions": [{"itemId": payload["basketId"],
                    "price": payload["price"], "paidPrice": payload["paidPrice"], "transactionStatus": 1,
                    "paymentTransactionId": "school-browser-item-" + identifier}]}
            signature = hmac.new(self.secret_key.encode(), f"{identifier}:{token}".encode(), hashlib.sha256).hexdigest()
            return {"status": "success", "conversationId": identifier, "token": token, "signature": signature,
                "paymentPageUrl": "https://sandbox-api.iyzipay.com/scs360-acceptance-school/" + token, "tokenExpireTime": 1800}
        if path != "/payment/iyzipos/checkoutform/auth/ecom/detail":
            raise RuntimeError("Unexpected fake school provider operation; no external call is available")
        result = dict(self.records[payload["token"]])
        if result["conversationId"] != identifier:
            raise RuntimeError("The fake provider session does not match")
        fields = ("paymentStatus", "paymentId", "currency", "basketId", "conversationId", "paidPrice", "price", "token")
        values = [format(Decimal(str(result[key])).normalize(), "f") if key in {"price", "paidPrice"} else str(result[key]) for key in fields]
        result["signature"] = hmac.new(self.secret_key.encode(), ":".join(values).encode(), hashlib.sha256).hexdigest()
        return result
