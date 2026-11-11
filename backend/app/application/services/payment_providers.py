"""Hosted-payment adapters. No card data is accepted by SCS360.

Protocols: dev.paytr.com/iframe-api and /durum-sorgu;
github.com/craftgate/craftgate-python-client; apidocs.sipay.com.tr.
Provider acceptance with actual merchant credentials remains a separate check.
"""
import base64
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from types import SimpleNamespace
from urllib.parse import quote, unquote_plus, urlparse
from uuid import UUID

import httpx
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from app.core.config import get_settings
from app.core.exceptions import AppException, ValidationException

FIELDS = {"iyzico": ("api_key", "secret_key"), "paytr": ("merchant_id", "merchant_key", "merchant_salt"),
    "craftgate": ("api_key", "secret_key"), "sipay": ("merchant_key", "app_id", "app_secret")}
HOSTS = {"paytr": {"LIVE": "https://www.paytr.com", "SANDBOX": "https://www.paytr.com"},
    "craftgate": {"LIVE": "https://api.craftgate.io", "SANDBOX": "https://sandbox-api.craftgate.io"},
    "sipay": {"LIVE": "https://app.sipay.com.tr", "SANDBOX": "https://provisioning.sipay.com.tr"}}


def catalog():
    return [{"id": identifier, "name": {"iyzico": "iyzico", "paytr": "PayTR", "craftgate": "Craftgate", "sipay": "Sipay"}[identifier],
        "credential_fields": list(fields), "channels": ["WEB", "MOBILE"],
        "provider_acceptance_required": True, "bank_pos_mode": "CONNECTED_MERCHANT_POS" if identifier == "craftgate" else None}
        for identifier, fields in FIELDS.items()]


class ProviderResponse(dict):
    """In-process evidence of an authenticated server API call, never a callback dict."""
    def __init__(self, owner, **values):
        super().__init__(values)
        self.owner = owner


class ProviderRejected(AppException):
    """A definite request/auth rejection, not a transport timeout or unknown result."""


def money(value):
    try:
        amount = Decimal(str(value).replace(",", "."))
        if not amount.is_finite() or not Decimal("0") < amount <= Decimal("9999999999.99") or amount != amount.quantize(Decimal("0.01")):
            raise ValueError()
        return amount
    except (ValueError, TypeError, InvalidOperation):
        raise AppException("Sağlayıcı ödeme tutarı doğrulanamadı", status_code=502) from None


class HostedGateway:
    def __init__(self, values):
        self.values = values
        self.provider = values.get("provider")
        self.environment = values.get("environment")
        self.portal_url = values.get("portal_url", "")
        self.settings = SimpleNamespace(IYZICO_CALLBACK_URL=values.get("callback_url", ""))
        self.owner = hashlib.sha256(json.dumps(values, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def configured(self):
        from app.application.services.school_payment_merchant import valid_callback, valid_portal
        if not isinstance(self.provider, str) or self.provider not in HOSTS or not isinstance(self.environment, str) or self.environment not in {"LIVE", "SANDBOX"}:
            raise ValidationException("Ödeme sağlayıcısı veya ortamı desteklenmiyor")
        if not all(isinstance(self.values.get(key), str) and 1 <= len(self.values[key]) <= 2048 for key in FIELDS[self.provider]):
            raise AppException("Sağlayıcının üye işyeri anahtarları eksik", status_code=503)
        if not valid_callback(self.settings.IYZICO_CALLBACK_URL, self.provider) or not valid_portal(self.portal_url):
            raise AppException("Sağlayıcı dönüş ve portal adresleri yapılandırılmalı", status_code=503)
        if (self.environment == "LIVE" or get_settings().APP_ENV == "production") and (
            urlparse(self.settings.IYZICO_CALLBACK_URL).scheme != "https" or urlparse(self.portal_url).scheme != "https"):
            raise AppException("Canlı tahsilat için HTTPS dönüş ve portal adresleri gerekli", status_code=503)
        if get_settings().APP_ENV == "production" and self.environment != "LIVE":
            raise AppException("Üretimde sandbox tahsilatı açılamaz", status_code=503)

    def require_organization(self, organization_id):
        if str(organization_id) != self.values.get("organization_id"):
            raise AppException("Sağlayıcı hesabı bu kuruma ait değil", status_code=403)

    def verify(self, value):
        return isinstance(value, ProviderResponse) and hmac.compare_digest(value.owner, self.owner)

    def verify_initial(self, value, identifier):
        return self.verify(value) and value.get("status") == "success" and value.get("conversationId") == str(identifier) and isinstance(value.get("token"), str)

    def valid_hosted_url(self, value):
        if not isinstance(value, str) or len(value) > 4096:
            return False
        try:
            url = urlparse(value)
            if url.scheme != "https" or url.username or url.password or url.fragment or url.port not in {None, 443}:
                return False
            host = url.hostname or ""
            if self.provider == "paytr":
                return host == "www.paytr.com" and url.path.startswith("/odeme/guvenli/")
            if self.provider == "sipay":
                return host == urlparse(HOSTS[self.provider][self.environment]).hostname and url.path.startswith("/ccpayment/makepayment/")
            return host.endswith(".craftgate.io") and ("sandbox" in host) == (self.environment == "SANDBOX")
        except ValueError:
            return False

    async def request(self, method, path, payload=None, *, bearer=None, form=False, idempotency=None):
        self.configured()
        base = HOSTS[self.provider][self.environment]
        headers = {}
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) if payload is not None and not form else ""
        if self.provider == "craftgate":
            nonce = secrets.token_hex(16)
            signature = base64.b64encode(hashlib.sha256((unquote_plus(base + path) + self.values["api_key"] + self.values["secret_key"] + nonce + body).encode()).digest()).decode()
            headers.update({"x-api-key": self.values["api_key"], "x-rnd-key": nonce, "x-auth-version": "v1", "x-signature": signature})
            if idempotency:
                headers["x-idempotency-key"] = idempotency
        if bearer:
            headers["Authorization"] = "Bearer " + bearer
        if body:
            headers["Content-Type"] = "application/json"
        try:
            async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
                response = await client.request(method, base + path, headers=headers,
                    **({"data": payload} if form else {"content": body.encode()} if body else {}))
                if response.status_code in {400, 401, 403, 404, 422}:
                    raise ProviderRejected("Sağlayıcı isteği reddetti", status_code=502)
                response.raise_for_status()
                result = response.json()
            if not isinstance(result, dict):
                raise ValueError()
            return result
        except (httpx.HTTPError, ValueError, TypeError):
            raise AppException("Ödeme sağlayıcısı doğrulanabilir yanıt vermedi; aynı oturumun durumunu kontrol edin", status_code=502) from None

    def paytr_token(self, value):
        return base64.b64encode(hmac.new(self.values["merchant_key"].encode(), (value + self.values["merchant_salt"]).encode(), hashlib.sha256).digest()).decode()

    async def sipay_token(self):
        result = await self.request("POST", "/ccpayment/api/token", {"app_id": self.values["app_id"], "app_secret": self.values["app_secret"], "app_lang": "tr"})
        token = result.get("data", {}).get("token") if isinstance(result.get("data"), dict) else None
        if result.get("status_code") != 100 or not isinstance(token, str) or not 1 <= len(token) <= 8192:
            raise ProviderRejected("Sipay üye işyeri oturumu doğrulanamadı", status_code=502)
        return token

    def sipay_hash(self, text):
        iv = secrets.token_hex(8)
        salt = secrets.token_hex(2)
        password = hashlib.sha1(self.values["app_secret"].encode()).hexdigest()
        key = hashlib.sha256((password + salt).encode()).hexdigest()[:32].encode()
        padder = padding.PKCS7(128).padder()
        data = padder.update(text.encode()) + padder.finalize()
        encryptor = Cipher(algorithms.AES(key), modes.CBC(iv.encode())).encryptor()
        encrypted = base64.b64encode(encryptor.update(data) + encryptor.finalize()).decode()
        return f"{iv}:{salt}:{encrypted}".replace("/", "__")

    def validate_payer(self, payer):
        if self.provider == "paytr" and (not payer.get("gsmNumber") or not isinstance(payer.get("email"), str) or not payer["email"].isascii()):
            raise ValidationException("PayTR için ödeme telefonu ve ASCII karakterli e-posta adresi gerekli")

    async def initialize(self, payload):
        try:
            return await self._initialize(payload)
        except ProviderRejected:
            return ProviderResponse(self.owner, status="failure", errorCode="PROVIDER_INITIALIZE_REJECTED")

    async def _initialize(self, payload):
        identifier = str(UUID(payload["conversationId"]))
        reference = UUID(identifier).hex
        amount = money(payload["paidPrice"])
        payer = payload["buyer"]
        if self.provider == "paytr":
            basket = base64.b64encode(json.dumps([[payload["basketItems"][0]["name"], format(amount, ".2f"), 1]], ensure_ascii=False).encode()).decode()
            values = {"merchant_id": self.values["merchant_id"], "user_ip": payer["ip"], "merchant_oid": reference,
                "email": payer["email"], "payment_amount": str(int(amount * 100)), "user_basket": basket,
                "no_installment": "1", "max_installment": "0", "currency": "TL", "test_mode": "1" if self.environment == "SANDBOX" else "0"}
            signed = "".join(values[key] for key in ("merchant_id", "user_ip", "merchant_oid", "email", "payment_amount", "user_basket", "no_installment", "max_installment", "currency", "test_mode"))
            values.update({"paytr_token": self.paytr_token(signed), "user_name": f'{payer["name"]} {payer["surname"]}',
                "user_address": payer["registrationAddress"], "user_phone": payer["gsmNumber"], "merchant_ok_url": payload["callbackUrl"],
                "merchant_fail_url": payload["callbackUrl"], "timeout_limit": "30", "debug_on": "0", "lang": "tr"})
            response = await self.request("POST", "/odeme/api/get-token", values, form=True)
            if response.get("status") == "failed":
                raise ProviderRejected("PayTR oturumu reddetti", status_code=502)
            token = response.get("token")
            if response.get("status") != "success" or not isinstance(token, str) or not 1 <= len(token) <= 2048:
                raise AppException("PayTR ödeme sayfası başlatılamadı", status_code=502)
            url = "https://www.paytr.com/odeme/guvenli/" + quote(token, safe="")
            session_token = reference
        elif self.provider == "craftgate":
            response = await self.request("POST", "/payment/v1/checkout-payments/init", {
                "price": float(amount), "paidPrice": float(amount), "currency": "TRY", "paymentGroup": "LISTING_OR_SUBSCRIPTION",
                "paymentPhase": "AUTH", "conversationId": identifier, "externalId": payload["basketId"], "orderId": reference,
                "callbackUrl": payload["callbackUrl"], "clientIp": payer["ip"], "enabledInstallments": [1], "forceThreeDS": True,
                "enabledPaymentMethods": ["CARD"], "allowOnlyCreditCard": True,
                "items": [{"name": payload["basketItems"][0]["name"], "price": float(amount), "externalId": payload["basketId"]}]}, idempotency=identifier)
            data = response.get("data")
            if response.get("errors"):
                raise ProviderRejected("Craftgate oturumu reddetti", status_code=502)
            if not isinstance(data, dict) or not isinstance(data.get("token"), str) or not 1 <= len(data["token"]) <= 2048:
                raise AppException("Craftgate ödeme oturumu doğrulanamadı", status_code=502)
            url, session_token = data.get("pageUrl"), data["token"]
        else:
            token = await self.sipay_token()
            invoice = {"invoice_id": reference, "invoice_description": payload["basketItems"][0]["name"], "total": format(amount, ".2f"),
                "return_url": payload["callbackUrl"], "cancel_url": payload["callbackUrl"], "response_method": "POST",
                "items": [{"name": payload["basketItems"][0]["name"], "price": format(amount, ".2f"), "quantity": 1}],
                "bill_email": payer["email"], "bill_phone": payer["gsmNumber"], "bill_address1": payer["registrationAddress"], "bill_city": payer["city"]}
            response = await self.request("POST", "/ccpayment/purchase/link", {"merchant_key": self.values["merchant_key"],
                "name": payer["name"], "surname": payer["surname"], "currency_code": "TRY", "invoice": json.dumps(invoice, ensure_ascii=False)}, bearer=token)
            if response.get("status") is not True or response.get("status_code") != 100:
                raise ProviderRejected("Sipay ödeme sayfası başlatılamadı", status_code=502)
            url, session_token = response.get("link"), reference
        if not self.valid_hosted_url(url):
            raise AppException("Sağlayıcının ödeme sayfası adresi doğrulanamadı", status_code=502)
        return ProviderResponse(self.owner, status="success", conversationId=identifier, token=session_token,
            paymentPageUrl=url, tokenExpireTime=1800)

    async def retrieve(self, token, identifier):
        identifier = str(UUID(str(identifier)))
        reference = UUID(identifier).hex
        if self.provider in {"paytr", "sipay"} and token != reference:
            raise AppException("Ödeme oturumu eşleşmedi", status_code=400)
        if self.provider == "paytr":
            data = await self.request("POST", "/odeme/durum-sorgu", {"merchant_id": self.values["merchant_id"], "merchant_oid": reference,
                "paytr_token": self.paytr_token(self.values["merchant_id"] + reference)}, form=True)
            if data.get("status") != "success":
                raise AppException("PayTR henüz doğrulanmış ödeme sonucu vermedi", status_code=502)
            environment_matches = str(data.get("test_mode")) == ("1" if self.environment == "SANDBOX" else "0")
            state = "CAPTURED" if data.get("payment_date") and not data.get("returns") and environment_matches else "REVIEW"
            normalized = {"state": state, "order_id": identifier, "provider_payment_id": reference, "transaction_id": reference,
                "amount": data.get("payment_total"), "price": data.get("payment_amount"), "currency": "TRY" if data.get("currency") in {"TL", "TRY"} else data.get("currency")}
        elif self.provider == "craftgate":
            response = await self.request("GET", "/payment/v1/checkout-payments/" + quote(token, safe=""))
            data = response.get("data")
            if not isinstance(data, dict):
                raise AppException("Craftgate ödeme sonucu doğrulanamadı", status_code=502)
            transactions = data.get("paymentTransactions") or []
            transaction = transactions[0] if isinstance(transactions, list) and len(transactions) == 1 and isinstance(transactions[0], dict) else {}
            state = "CAPTURED" if data.get("paymentStatus") == "SUCCESS" and data.get("paymentPhase") == "AUTH" and transaction.get("transactionStatus") in {"APPROVED", "PAYOUT_STARTED"} else "FAILED" if data.get("paymentStatus") == "FAILURE" else "REVIEW"
            normalized = {"state": state, "order_id": data.get("conversationId"), "provider_payment_id": str(data.get("id") or ""),
                "transaction_id": str(transaction.get("id") or ""), "amount": data.get("paidPrice"), "price": data.get("price"),
                "currency": data.get("currency"), "basket_id": data.get("externalId"), "item_id": transaction.get("externalId"),
                "item_price": transaction.get("price"), "item_paid": transaction.get("paidPrice")}
        else:
            bearer = await self.sipay_token()
            data = await self.request("POST", "/ccpayment/api/checkstatus", {"invoice_id": reference, "merchant_key": self.values["merchant_key"],
                "hash_key": self.sipay_hash(reference + "|" + self.values["merchant_key"])}, bearer=bearer)
            if data.get("invoice_id") != reference:
                raise AppException("Sipay sipariş referansı eşleşmedi", status_code=502)
            captured = data.get("status_code") == 100 and data.get("transaction_status") == "Completed" and data.get("transaction_type") == "Auth" and not data.get("total_refunded_amount")
            normalized = {"state": "CAPTURED" if captured else "PENDING", "order_id": identifier,
                "provider_payment_id": data.get("order_id"), "transaction_id": data.get("transaction_id"),
                "amount": data.get("transaction_amount"), "price": data.get("product_price"),
                # Absence of a confirmed currency never credits a debt.
                "currency": data.get("currency_code", data.get("currency", ""))}
        return ProviderResponse(self.owner, status="success", token=token, conversationId=identifier,
            paymentStatus="FAILED" if normalized["state"] == "FAILED" else "SUCCESS" if normalized["state"] == "CAPTURED" else "PENDING",
            normalized=normalized)

    def capture_proof(self, result, row, token):
        if not self.verify(result) or result.get("token") != token or result.get("conversationId") != str(row.id):
            raise AppException("Sağlayıcı ödeme kanıtı doğrulanamadı", status_code=400)
        data = result["normalized"]
        if data["order_id"] != str(row.id):
            raise AppException("Sağlayıcının sipariş referansı eşleşmedi", status_code=400)
        if data["state"] not in {"CAPTURED", "REVIEW"} or data.get("amount") is None:
            return None
        amount, price = money(data["amount"]), money(data["price"])
        identifier, transaction = data.get("provider_payment_id"), data.get("transaction_id")
        if not isinstance(identifier, str) or not 1 <= len(identifier) <= 100 or not isinstance(transaction, str) or not 1 <= len(transaction) <= 255:
            raise AppException("Sağlayıcı işlem referansı doğrulanamadı", status_code=502)
        matching = data["order_id"] == str(row.id) and amount == price == row.amount and data.get("currency") == row.currency
        if self.provider == "craftgate":
            matching = matching and data.get("basket_id") == str(row.debt_id) and data.get("item_id") == str(row.debt_id) and money(data.get("item_price")) == row.amount and money(data.get("item_paid")) == row.amount
        return {"provider": self.provider, "proof_type": "authenticated_provider_api", "provider_payment_id": identifier,
            "conversation_id": str(row.id), "basket_id": str(row.debt_id), "amount": format(amount, ".2f"),
            "currency": str(data.get("currency") or "")[:3], "transaction_id": transaction,
            "matches_checkout": bool(matching), "fraud_status": "1" if data["state"] == "CAPTURED" else "0",
            "verified_at": datetime.now(UTC).isoformat()}
