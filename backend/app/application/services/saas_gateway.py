"""Dedicated platform merchant; no school tuition credentials are reused.

Protocol: https://docs.iyzico.com/en/advanced/response-signature-validation
"""
import hashlib
import hmac
import json
import re
from types import SimpleNamespace
from urllib.parse import urlparse

from cryptography.fernet import Fernet, InvalidToken

from app.application.services.online_payment_service import IyzicoGateway
from app.core.config import get_settings
from app.core.exceptions import AppException


class SaasGateway(IyzicoGateway):
    def __init__(self, source=None):
        self.source = source or get_settings()
        super().__init__(SimpleNamespace(IYZICO_API_KEY=self.source.SAAS_IYZICO_API_KEY,
            IYZICO_SECRET_KEY=self.source.SAAS_IYZICO_SECRET_KEY, IYZICO_BASE_URL=self.source.SAAS_IYZICO_BASE_URL,
            IYZICO_CALLBACK_URL=self.source.SAAS_IYZICO_CALLBACK_URL, APP_ENV=self.source.APP_ENV))

    def cipher(self):
        try:
            return Fernet(self.source.SAAS_CHECKOUT_ENCRYPTION_KEY.encode())
        except (ValueError, TypeError) as exc:
            raise AppException("Üyelik ödeme şifreleme anahtarı yapılandırılmamış", status_code=503) from exc

    def configured(self):
        try:
            super().configured()
            callback = urlparse(self.settings.IYZICO_CALLBACK_URL)
            portal = urlparse(self.source.SAAS_PORTAL_URL)
            _ = callback.port, portal.port
        except ValueError as exc:
            raise AppException("Üyelik ödeme adresleri geçersiz", status_code=503) from exc
        if not callback.hostname or callback.username or callback.password or callback.query or callback.fragment or callback.path != "/api/subscription/iyzico/callback":
            raise AppException("Üyelik ödeme dönüş adresi geçersiz", status_code=503)
        local = self.source.APP_ENV in {"development", "test"} and portal.hostname in {"localhost", "127.0.0.1"}
        if (portal.scheme != "https" and not (local and portal.scheme == "http")) or not portal.hostname or portal.username or portal.password or portal.query or portal.fragment or portal.path not in {"", "/"}:
            raise AppException("Üyelik portal adresi geçersiz", status_code=503)
        if self.source.APP_ENV == "production" and urlparse(self.settings.IYZICO_BASE_URL).hostname != "api.iyzipay.com":
            raise AppException("Üretim üyeliği test tahsilatıyla açılamaz", status_code=503)
        self.cipher()

    def available(self):
        if not self.source.SAAS_PAYMENT_ENABLED:
            return False
        try:
            self.configured()
            return True
        except AppException:
            return False

    def seal(self, values):
        return self.cipher().encrypt(json.dumps(values, separators=(",", ":")).encode()).decode()

    def open(self, value):
        try:
            return json.loads(self.cipher().decrypt(value.encode()))
        except (InvalidToken, ValueError, TypeError, AttributeError) as exc:
            raise AppException("Ödeme oturumu okunamadı; platform yöneticisi kontrol etmeli", status_code=503) from exc

    def verify_initial(self, result, identifier):
        if not isinstance(result, dict) or result.get("status") != "success" or result.get("conversationId") != str(identifier):
            return False
        token = result.get("token")
        if not isinstance(token, str) or not 1 <= len(token) <= 2048:
            return False
        calculated = hmac.new(self.settings.IYZICO_SECRET_KEY.encode(), f"{identifier}:{token}".encode(), hashlib.sha256).hexdigest()
        signature = result.get("signature")
        return isinstance(signature, str) and bool(re.fullmatch(r"[0-9a-fA-F]{64}", signature)) and hmac.compare_digest(calculated, signature.lower())

    def verify(self, result):
        if not isinstance(result, dict) or not isinstance(result.get("signature"), str) or not re.fullmatch(r"[0-9a-fA-F]{64}", result["signature"]):
            return False
        try:
            return super().verify({**result, "signature": result["signature"].lower()})
        except (TypeError, ValueError, ArithmeticError):
            return False

    def valid_hosted_url(self, value):
        if not isinstance(value, str) or len(value) > 4096:
            return False
        try:
            parsed = urlparse(value)
            return parsed.scheme == "https" and not parsed.username and not parsed.password and (parsed.hostname or "").endswith(".iyzipay.com") and parsed.port in {None, 443}
        except ValueError:
            return False

    def return_url(self):
        self.configured()
        return self.source.SAAS_PORTAL_URL.rstrip("/") + "/subscription"

    async def retrieve(self, token, conversation_id):
        return await self.post("/payment/iyzipos/checkoutform/auth/ecom/detail", {"locale": "tr", "token": token, "conversationId": str(conversation_id)})


def get_saas_gateway():
    return SaasGateway()
