"""In-memory provider for the disposable browser runner only. No HTTP or funds."""
import hashlib
import hmac
import os
from decimal import Decimal
from types import SimpleNamespace

from cryptography.fernet import Fernet

from app.application.services.saas_gateway import SaasGateway, get_saas_gateway


def install(app):
    database = os.environ.get("DATABASE_URL", "")
    if os.environ.get("APP_ENV") != "test" or not ("scs360_acceptance_browser_" in database or "scs360-acceptance-" in database):
        raise RuntimeError("Fake payments are restricted to the disposable browser database")
    gateway = AcceptanceGateway()
    app.dependency_overrides[get_saas_gateway] = lambda: gateway


class AcceptanceGateway(SaasGateway):
    def __init__(self):
        super().__init__(SimpleNamespace(APP_ENV="test", SAAS_PAYMENT_ENABLED=True,
            SAAS_IYZICO_API_KEY="acceptance-only", SAAS_IYZICO_SECRET_KEY="acceptance-provider-secret",
            SAAS_IYZICO_BASE_URL="https://sandbox-api.iyzipay.com", SAAS_IYZICO_CALLBACK_URL="http://127.0.0.1:5016/api/subscription/iyzico/callback",
            SAAS_PORTAL_URL="http://127.0.0.1:5176", SAAS_CHECKOUT_ENCRYPTION_KEY=Fernet.generate_key().decode()))
        self.records, self.reads = {}, {}

    async def initialize(self, payload):
        token = "browser-acceptance-" + payload["conversationId"]
        self.records[token] = {"status": "success", "paymentStatus": "SUCCESS", "paymentId": "browser-" + payload["conversationId"],
            "token": token, "conversationId": payload["conversationId"], "basketId": payload["basketId"],
            "currency": payload["currency"], "price": payload["price"], "paidPrice": payload["paidPrice"],
            "itemTransactions": [{"itemId": payload["basketId"], "price": payload["price"], "paymentTransactionId": "browser-item-" + payload["conversationId"]}]}
        signature = hmac.new(self.settings.IYZICO_SECRET_KEY.encode(), f'{payload["conversationId"]}:{token}'.encode(), hashlib.sha256).hexdigest()
        return {"status": "success", "conversationId": payload["conversationId"], "token": token, "signature": signature,
            "paymentPageUrl": "https://sandbox-api.iyzipay.com/checkoutform/" + token, "tokenExpireTime": 1800}

    async def retrieve(self, token, conversation_id):
        self.reads[token] = self.reads.get(token, 0) + 1
        result = {**self.records[token], "fraudStatus": 0 if self.reads[token] == 1 else 1}
        fields = ("paymentStatus", "paymentId", "currency", "basketId", "conversationId", "paidPrice", "price", "token")
        values = [format(Decimal(str(result[key])).normalize(), "f") if key in {"price", "paidPrice"} else str(result[key]) for key in fields]
        result["signature"] = hmac.new(self.settings.IYZICO_SECRET_KEY.encode(), ":".join(values).encode(), hashlib.sha256).hexdigest()
        return result
