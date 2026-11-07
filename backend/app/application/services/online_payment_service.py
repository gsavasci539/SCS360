"""Hosted checkout with scoped debts and idempotent, verified reconciliation.

Protocol: https://docs.iyzico.com/en/payment-methods/checkoutform/cf-implementation/cf-retrieve
Auth: https://docs.iyzico.com/en/getting-started/preliminaries/authentication/hmacsha256-auth
"""
import base64
import hashlib
import hmac
import json
import re
import secrets
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse
from uuid import UUID

import httpx
from sqlalchemy import select, update

from app.core.config import get_settings
from app.core.exceptions import AppException, ConflictException, NotFoundException, ValidationException
from app.core.student_access import require_student_access, require_parent_child_access
from app.domain.services.debt_calculator import DebtCalculator
from app.application.services.platform_service import lock_organization
from app.infrastructure.models.models import Debt, DebtStatus, Payment, PaymentCheckout, PaymentMethod, Receipt, Student
from app.infrastructure.repositories.base import BaseRepository


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


class IyzicoGateway:
    def __init__(self, settings=None):
        self.settings = settings or get_settings()

    def configured(self):
        value = self.settings
        if not all([value.IYZICO_API_KEY, value.IYZICO_SECRET_KEY, value.IYZICO_CALLBACK_URL]):
            raise AppException("Online ödeme sağlayıcısı yapılandırılmamış", status_code=503)
        parsed = urlparse(value.IYZICO_BASE_URL)
        if parsed.scheme != "https" or parsed.netloc not in {"sandbox-api.iyzipay.com", "api.iyzipay.com"}:
            raise AppException("Ödeme sağlayıcısı adresi geçersiz", status_code=503)
        if value.APP_ENV == "production" and parsed.hostname != "api.iyzipay.com":
            raise AppException("Üretimde öğrenci borcu test ödemesiyle kapatılamaz", status_code=503)
        callback = urlparse(value.IYZICO_CALLBACK_URL)
        if callback.scheme != "https" and not (value.APP_ENV in {"development", "test"} and callback.hostname in {"localhost", "127.0.0.1"}):
            raise AppException("Ödeme dönüş adresi HTTPS olmalı", status_code=503)

    def require_organization(self, organization_id):
        # A legacy merchant belongs to one school, never every SaaS customer.
        try:
            bound = UUID(str(self.settings.IYZICO_ORGANIZATION_ID))
        except (AttributeError, TypeError, ValueError):
            bound = None
        if not getattr(self.settings, "IYZICO_PAYMENT_ENABLED", False) or bound != organization_id:
            raise AppException("Bu kurum için online öğrenci ödemesi açık değil", status_code=503)

    def available_for(self, organization_id):
        try:
            self.configured(); self.require_organization(organization_id)
            return True
        except AppException:
            return False

    async def post(self, path, payload):
        self.configured()
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        nonce = secrets.token_hex(16)
        signature = hmac.new(self.settings.IYZICO_SECRET_KEY.encode(), (nonce + path + body).encode(), hashlib.sha256).hexdigest()
        authorization = base64.b64encode(f"apiKey:{self.settings.IYZICO_API_KEY}&randomKey:{nonce}&signature:{signature}".encode()).decode()
        try:
            async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
                response = await client.post(self.settings.IYZICO_BASE_URL.rstrip("/") + path, content=body.encode(),
                    headers={"Authorization": "IYZWSv2 " + authorization, "x-iyzi-rnd": nonce, "Content-Type": "application/json"})
                response.raise_for_status()
                return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AppException("Ödeme sağlayıcısı yanıt veremedi; işlemi daha sonra kontrol edin", status_code=502) from exc

    async def initialize(self, payload):
        return await self.post("/payment/iyzipos/checkoutform/initialize/auth/ecom", payload)

    async def retrieve(self, token, conversation_id):
        return await self.post("/payment/iyzipos/checkoutform/auth/ecom/detail", {"locale": "tr", "token": token, "conversationId": str(conversation_id)})

    def verify_initial(self, response, identifier):
        if not isinstance(response, dict) or response.get("status") != "success" or response.get("conversationId") != str(identifier):
            return False
        token, signature = response.get("token"), response.get("signature")
        if not isinstance(token, str) or not 1 <= len(token) <= 2048 or not isinstance(signature, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", signature):
            return False
        expected = hmac.new(self.settings.IYZICO_SECRET_KEY.encode(), f"{identifier}:{token}".encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature.lower())

    def valid_hosted_url(self, value):
        if not isinstance(value, str) or len(value) > 4096:
            return False
        try:
            hosted = urlparse(value)
            return hosted.scheme == "https" and not hosted.username and not hosted.password and (hosted.hostname or "").endswith(".iyzipay.com") and hosted.port in {None, 443}
        except ValueError:
            return False

    def verify(self, response):
        if not isinstance(response, dict):
            return False
        fields = ("paymentStatus", "paymentId", "currency", "basketId", "conversationId", "paidPrice", "price", "token")
        values = []
        for field in fields:
            value = str(response.get(field, ""))
            if field in {"paidPrice", "price"}:
                try:
                    value = format(Decimal(value), "f")
                    if "." in value:
                        value = value.rstrip("0").rstrip(".")
                except InvalidOperation:
                    return False
            values.append(value)
        calculated = hmac.new(self.settings.IYZICO_SECRET_KEY.encode(), ":".join(values).encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(calculated, str(response.get("signature", "")))


async def initialize(db, tenant, user, body, ip, gateway=None):
    if gateway is None:
        from app.application.services import school_checkout_service, school_payment_merchant
        if getattr(body, "request_id", None):
            return await school_checkout_service.initialize(db, tenant, user, body, ip)
        selected_debt = await BaseRepository(db, tenant).get_by_id(body.debt_id, Debt)
        context = await school_payment_merchant.resolve_gateway(db, selected_debt.organization_id)
        if context["merchant_snapshot"]:
            return await school_checkout_service.initialize(db, tenant, user, body, ip)
        gateway = context["gateway"]
    gateway = gateway or IyzicoGateway()
    repo = BaseRepository(db, tenant)
    debt = await repo.get_by_id(body.debt_id, Debt)
    if not tenant.has_permission("finance.write"):
        await require_parent_child_access(db, tenant.user_id, debt.student_id)
    await require_student_access(db, tenant, debt.student_id)
    await repo.get_by_id(debt.student_id, Student)
    gateway.require_organization(debt.organization_id)
    amount = Decimal(str(body.amount)).quantize(Decimal("0.01"))
    if debt.status == DebtStatus.CANCELLED:
        raise ConflictException("İptal edilen borca ödeme yapılamaz")
    try:
        principal, previously_paid = Decimal(str(debt.amount)), Decimal(str(debt.paid_amount))
        valid_balance = principal.is_finite() and previously_paid.is_finite() and Decimal("0") < principal <= Decimal("9999999999.99") and Decimal("0") <= previously_paid <= principal
    except (InvalidOperation, TypeError, ValueError):
        valid_balance = False
    if not valid_balance:
        raise ValidationException("Borç kaydının eski tutar veya ödeme bilgileri incelenmeli")
    try:
        DebtCalculator.validate_payment(debt.amount, debt.paid_amount, amount)
    except ValueError as exc:
        raise ValidationException(str(exc)) from exc
    buyer = body.buyer or {}
    address = body.billing_address or {}
    if not all([buyer.get("identityNumber"), buyer.get("registrationAddress"), buyer.get("city"), buyer.get("country")]):
        raise ValidationException("Ödeme için kimlik numarası, adres, şehir ve ülke bilgileri gerekli")
    gateway.configured()
    checkout = PaymentCheckout(organization_id=debt.organization_id, debt_id=debt.id, created_by=user.id,
        amount=amount, currency="TRY")
    db.add(checkout); await db.flush()
    payer = {"id": str(user.id), "name": user.first_name, "surname": user.last_name,
        "email": user.email, "gsmNumber": str(buyer.get("gsmNumber") or user.phone or ""), "identityNumber": str(buyer["identityNumber"]),
        "registrationAddress": str(buyer["registrationAddress"]), "city": str(buyer["city"]),
        "country": str(buyer["country"]), "ip": ip}
    billing = {"contactName": f"{user.first_name} {user.last_name}", "city": payer["city"],
        "country": payer["country"], "address": payer["registrationAddress"]}
    payload = {"locale": "tr", "conversationId": str(checkout.id), "basketId": str(debt.id),
        "price": str(amount), "paidPrice": str(amount), "currency": "TRY", "paymentGroup": "PRODUCT",
        "callbackUrl": get_settings().IYZICO_CALLBACK_URL, "enabledInstallments": [1], "buyer": payer,
        "billingAddress": billing, "shippingAddress": billing,
        "basketItems": [{"id": str(debt.id), "name": debt.description or "Okul ödemesi", "category1": "Eğitim",
            "itemType": "VIRTUAL", "price": str(amount)}]}
    result = await gateway.initialize(payload)
    if not gateway.verify_initial(result, checkout.id):
        raise AppException("Ödeme başlatma yanıtı doğrulanamadı", status_code=502)
    if not gateway.valid_hosted_url(result.get("paymentPageUrl")):
        raise AppException("Ödeme sayfası doğrulanamadı", status_code=502)
    checkout.token_hash = token_hash(result["token"])
    await db.flush()
    return {"payment_page_url": result["paymentPageUrl"], "checkout_url": result["paymentPageUrl"],
        "conversation_id": str(checkout.id), "status": "PENDING"}


async def reconcile(db, token, gateway=None, checkout_id=None):
    if gateway is None:
        from app.application.services import school_checkout_service
        selection = select(PaymentCheckout).where(PaymentCheckout.id == checkout_id) if checkout_id else select(PaymentCheckout).where(PaymentCheckout.token_hash == token_hash(token))
        candidate = (await db.execute(selection)).scalar_one_or_none()
        if candidate is not None and candidate.merchant_snapshot:
            row = await school_checkout_service.reconcile(db, token, candidate.id)
            return {"status": "SUCCESS" if row.payment_id else row.status, "conversation_id": str(row.id),
                "payment_id": str(row.payment_id) if row.payment_id else None, "amount": str(row.amount)}
    gateway = gateway or IyzicoGateway()
    checkout = (await db.execute(select(PaymentCheckout).where(PaymentCheckout.token_hash == token_hash(token)))).scalar_one_or_none()
    if checkout is None:
        raise NotFoundException("Ödeme oturumu bulunamadı")
    organization_id, checkout_id = checkout.organization_id, checkout.id
    await lock_organization(db, organization_id)
    checkout = (await db.execute(select(PaymentCheckout).where(PaymentCheckout.id == checkout_id,
        PaymentCheckout.organization_id == organization_id).with_for_update().execution_options(populate_existing=True))).scalar_one()
    if checkout.payment_id:
        return {"status": "SUCCESS", "payment_id": str(checkout.payment_id)}
    # Existing callbacks remain verifiable when new checkout is disabled. The
    # merchant still must belong to the original institution.
    try:
        bound = UUID(str(gateway.settings.IYZICO_ORGANIZATION_ID))
    except (AttributeError, TypeError, ValueError):
        bound = None
    if bound != checkout.organization_id:
        raise AppException("Ödeme sağlayıcısı kurum bağlantısı kontrol edilmeli", status_code=503)
    result = await gateway.retrieve(token, checkout.id)
    if not gateway.verify(result):
        raise AppException("Ödeme sonucu doğrulanamadı", status_code=400)
    if result.get("token") != token or result.get("conversationId") != str(checkout.id) or result.get("basketId") != str(checkout.debt_id):
        raise AppException("Ödeme oturumu eşleşmedi", status_code=400)
    if result.get("status") != "success" or result.get("paymentStatus") != "SUCCESS":
        return {"status": "FAILED"}
    try:
        valid_amount = Decimal(str(result.get("price"))) == checkout.amount and Decimal(str(result.get("paidPrice"))) == checkout.amount
    except InvalidOperation:
        valid_amount = False
    if not valid_amount or result.get("currency") != checkout.currency or not result.get("paymentId"):
        raise AppException("Ödeme tutarı veya para birimi eşleşmedi", status_code=400)
    # A successful card authorization can still await the provider's risk
    # review. Only an approved result may reduce the student's debt.
    fraud = str(result.get("fraudStatus"))
    if fraud == "-1":
        return {"status": "FAILED"}
    if fraud != "1":
        checkout.status = "FRAUD_REVIEW"
        await db.flush()
        return {"status": "REVIEW", "message": "Ödeme sağlayıcının incelemesinde"}
    claim = await db.execute(update(PaymentCheckout).where(PaymentCheckout.id == checkout.id,
        PaymentCheckout.status.in_(["PENDING", "FRAUD_REVIEW"]), PaymentCheckout.payment_id.is_(None)).values(status="PROCESSING"))
    if claim.rowcount != 1:
        await db.refresh(checkout)
        return {"status": "SUCCESS" if checkout.payment_id else checkout.status, "payment_id": str(checkout.payment_id) if checkout.payment_id else None}
    debt = (await db.execute(select(Debt).where(Debt.id == checkout.debt_id).with_for_update())).scalar_one()
    checkout.provider_payment_id = str(result["paymentId"])
    if checkout.merchant_scope is None:
        checkout.merchant_scope = f"legacy:{checkout.organization_id}"
    balances = (await db.execute(select(Debt.amount, Debt.paid_amount).where(Debt.organization_id == checkout.organization_id,
        Debt.student_id == debt.student_id, Debt.deleted_at.is_(None), Debt.status != DebtStatus.CANCELLED))).all()
    valid_balances = all(amount is not None and paid is not None and amount.is_finite() and paid.is_finite() and
        Decimal("0") < amount <= Decimal("9999999999.99") and Decimal("0") <= paid <= amount for amount, paid in balances)
    student_remaining = sum((amount - paid for amount, paid in balances), Decimal("0")) - checkout.amount if valid_balances else None
    if debt.organization_id != checkout.organization_id or student_remaining is None or not Decimal("0") <= student_remaining <= Decimal("9999999999.99"):
        checkout.status = "REVIEW"
        await db.flush()
        return {"status": "REVIEW", "message": "Sağlayıcı ödemesi alındı; öğrenci bakiyesi için yönetici incelemesi gerekli"}
    applied = await db.execute(update(Debt).where(Debt.id == debt.id, Debt.deleted_at.is_(None),
        Debt.status != DebtStatus.CANCELLED, Debt.amount - Debt.paid_amount >= checkout.amount)
        .values(paid_amount=Debt.paid_amount + checkout.amount))
    if applied.rowcount != 1:
        checkout.status = "REVIEW"
        return {"status": "REVIEW", "message": "Sağlayıcı ödemesi alındı; borç mutabakatı için yönetici incelemesi gerekli"}
    await db.refresh(debt)
    debt.status = DebtCalculator.calculate_status(debt.amount, debt.paid_amount, debt.due_date)
    payment = Payment(organization_id=debt.organization_id, branch_id=debt.branch_id, student_id=debt.student_id,
        debt_id=debt.id, amount=checkout.amount, payment_method=PaymentMethod.CREDIT_CARD,
        received_by=checkout.created_by, notes=f"iyzico: {checkout.provider_payment_id}")
    db.add(payment); await db.flush()
    db.add(Receipt(organization_id=debt.organization_id, branch_id=debt.branch_id, student_id=debt.student_id,
        payment_id=payment.id, receipt_number="IYZ-" + base64.b32encode(payment.id.bytes).decode().rstrip("="), issued_by=checkout.created_by,
        remaining_debt=student_remaining))
    checkout.payment_id, checkout.status = payment.id, "COMPLETED"
    await db.flush()
    return {"status": "SUCCESS", "payment_id": str(payment.id), "debt_id": str(debt.id),
        "amount": str(checkout.amount), "remaining_amount": str(debt.remaining_amount)}


async def available_for(db, organization_id):
    from app.application.services import school_payment_merchant
    try:
        context = await school_payment_merchant.resolve_gateway(db, organization_id)
        context["gateway"].configured()
        if not context["merchant_snapshot"]:
            school_payment_merchant.snapshot_gateway(context["gateway"], organization_id, context["merchant_scope"])
        return True
    except AppException:
        return False
