"""Hosted subscription checkout, verified receipts and explicit reconciliation.

No card details are accepted or stored. Initialization commits its reservation
before the network call so normal school writes do not wait on the provider.
"""
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import hmac
import json
from types import SimpleNamespace
from uuid import UUID

from sqlalchemy import inspect, select

from app.application.services import platform_service as platform
from app.application.services import subscription_billing_service as billing
from app.application.services.subscription_access import utc
from app.application.services.online_payment_service import token_hash
from app.core.config import get_settings
from app.core.exceptions import AppException, ConflictException, ForbiddenException, NotFoundException
from app.domain.entities.saas import OrganizationSubscription, SubscriptionCheckout, SubscriptionInvoice
from app.infrastructure.models.models import AuditLog

ACTIVE = {"INITIALIZING", "PENDING", "REVIEW", "PAID", "PAID_REVIEW"}


async def latest(db, invoice_id):
    return (await db.execute(select(SubscriptionCheckout).where(SubscriptionCheckout.invoice_id == invoice_id)
        .order_by(SubscriptionCheckout.created_at.desc(), SubscriptionCheckout.id.desc()).limit(1))).scalar_one_or_none()


def result(row, attempt=None, **extra):
    return {"invoice": billing.invoice_data(row), "status": attempt.status if attempt else row.status,
        "checkout_id": str(attempt.id) if attempt else None, **extra}


def fingerprint(user, invoice_id, body):
    content = {"user": str(user.id), "invoice": str(invoice_id), "buyer": body.model_dump(mode="json", exclude={"request_id", "client_channel"})}
    return hmac.new(get_settings().JWT_SECRET_KEY.encode(), json.dumps(content, sort_keys=True).encode(), hashlib.sha256).hexdigest()


async def current_member(db, org_id):
    return (await db.execute(select(OrganizationSubscription).where(OrganizationSubscription.organization_id == org_id))).scalar_one_or_none()


async def validate_quote(db, org, row):
    if not org.is_active or org.deleted_at is not None:
        raise ConflictException("Kapatılmış kurum için ödeme başlatılamaz")
    member = await current_member(db, org.id)
    if member and member.admin_status != "ACTIVE":
        raise ConflictException("Kurum üyeliği yönetici tarafından kapatılmış")
    if utc(row.valid_until) <= datetime.now(UTC):
        raise ConflictException("Ödeme talebinin süresi doldu; iptal edip güncel bir talep oluşturun")
    if billing.membership_digest(member) != row.base_membership_digest:
        raise ConflictException("Üyelik değişmiş; ödeme talebini güncelleyerek devam edin")
    used = await platform.usage(db, org.id)
    if any(used[key] > row.package_snapshot[key] for key in used):
        raise ConflictException("Seçilen paket mevcut kayıt sayısına yetmiyor")


def hosted(row, attempt, user, gateway):
    if attempt.created_by != user.id:
        raise ConflictException("Devam eden ödeme oturumunu başlatan kullanıcı tamamlamalı")
    secret = gateway.open(attempt.checkout_secret)
    if not isinstance(secret, dict) or not gateway.valid_hosted_url(secret.get("url")):
        raise AppException("Ödeme oturumu doğrulanamadı", status_code=503)
    try:
        expires = datetime.fromisoformat(secret["expires"])
    except (KeyError, TypeError, ValueError) as exc:
        raise AppException("Ödeme oturumunun süresi okunamadı", status_code=503) from exc
    if utc(expires) <= datetime.now(UTC):
        raise ConflictException("Ödeme oturumu zaman aşımına uğradı; sonucu kontrol edin")
    return result(row, attempt, checkout_url=secret["url"])


async def initialize(db, user, invoice_id, body, ip, gateway):
    await billing.require_manager(db, user)
    if body.client_channel in {"IOS", "ANDROID"}:
        raise AppException("Native üyelik satın alımı için mağaza ödeme akışı henüz yapılandırılmamış", status_code=409)
    organization_id = user.organization_id
    if not gateway.available():
        raise AppException("Online üyelik ödemesi şu anda açık değil", status_code=503)
    gateway.configured()
    org = await platform.lock_organization(db, organization_id)
    row = await billing.invoice(db, invoice_id, org.id)
    if row.status == "PAID":
        return result(row)
    if row.status != "PENDING":
        raise ConflictException("Ödeme talebi şu anda yeni tahsilata açık değil")
    digest = fingerprint(user, row.id, body)
    previous = (await db.execute(select(AuditLog).where(AuditLog.id == body.request_id))).scalar_one_or_none()
    if previous:
        values = previous.new_values or {}
        if previous.user_id != user.id or values.get("event") != "SUBSCRIPTION_CHECKOUT_REQUESTED" or not hmac.compare_digest(values.get("digest", ""), digest):
            raise ConflictException("İstek kimliği farklı bir ödeme işleminde kullanılmış")
        attempt = await db.get(SubscriptionCheckout, UUID(values["checkout_id"]))
        if attempt is None:
            raise ConflictException("Ödeme oturumu incelenmeli")
        if attempt.status == "PENDING":
            return hosted(row, attempt, user, gateway)
        return result(row, attempt)
    active = await latest(db, row.id)
    if active and active.status in ACTIVE:
        raise ConflictException("Devam eden ödeme var; önce sonucunu kontrol edin veya mevcut oturuma devam edin")
    await validate_quote(db, org, row)
    if row.amount <= 0:
        raise ConflictException("Sıfır tutarlı üyelik talebini platform yöneticisi etkinleştirmeli")
    now = datetime.now(UTC)
    attempt = SubscriptionCheckout(id=body.request_id, organization_id=org.id, invoice_id=row.id, created_by=user.id,
        request_digest=digest, status="INITIALIZING", created_at=now, updated_at=now)
    db.add(attempt)
    platform.audit(db, user, org, "SUBSCRIPTION_CHECKOUT_REQUESTED", {"digest": digest, "checkout_id": str(attempt.id), "invoice_id": str(row.id)}, body.request_id)
    address = {"contactName": f"{user.first_name} {user.last_name}", "city": body.city, "country": body.country, "address": body.address}
    payload = {"locale": "tr", "conversationId": str(attempt.id), "basketId": str(row.id), "price": str(row.amount), "paidPrice": str(row.amount),
        "currency": row.currency, "paymentGroup": "SUBSCRIPTION", "callbackUrl": gateway.settings.IYZICO_CALLBACK_URL, "enabledInstallments": [1],
        "buyer": {"id": str(user.id), "name": user.first_name, "surname": user.last_name, "email": user.email,
            "gsmNumber": body.phone, "identityNumber": body.identity_number, "registrationAddress": body.address,
            "city": body.city, "country": body.country, "ip": ip}, "billingAddress": address, "shippingAddress": address,
        "basketItems": [{"id": str(row.id), "name": str(row.package_snapshot.get("name") or "SCS360 üyeliği")[:120],
            "category1": "SaaS", "itemType": "VIRTUAL", "price": str(row.amount)}]}
    identifier = attempt.id
    await platform.commit(db)
    try:
        response = await gateway.initialize(payload)
        if not gateway.verify_initial(response, identifier) or not gateway.valid_hosted_url(response.get("paymentPageUrl")):
            raise AppException("Üyelik ödeme sayfası doğrulanamadı", status_code=502)
        ttl = response.get("tokenExpireTime", 1800)
        if type(ttl) is not int or not 1 <= ttl <= 86400:
            raise AppException("Ödeme oturumu süresi geçersiz", status_code=502)
        expires = datetime.now(UTC) + timedelta(seconds=ttl)
        org = await platform.lock_organization(db, organization_id)
        await db.refresh(row); await db.refresh(attempt)
        if row.status != "PENDING" or attempt.status != "INITIALIZING" or not org.is_active:
            raise ConflictException("Ödeme başlatılırken kurum veya talep değişti; durumu kontrol edin")
        attempt.token_hash = token_hash(response["token"])
        attempt.checkout_secret = gateway.seal({"token": response["token"], "url": response["paymentPageUrl"], "expires": expires.isoformat()})
        attempt.status, attempt.updated_at = "PENDING", datetime.now(UTC)
        if expires > utc(row.valid_until):
            row.valid_until = expires
        await platform.commit(db)
        return result(row, attempt, checkout_url=response["paymentPageUrl"])
    except AppException:
        await db.rollback()
        await platform.lock_organization(db, organization_id)
        saved = await db.get(SubscriptionCheckout, identifier)
        if saved and saved.status == "INITIALIZING":
            saved.status, saved.updated_at = "FAILED", datetime.now(UTC)
            await platform.commit(db)
        raise


async def resume(db, user, invoice_id, gateway):
    await billing.require_manager(db, user)
    await platform.lock_organization(db, user.organization_id)
    row = await billing.invoice(db, invoice_id, user.organization_id)
    if row.status == "PAID":
        return result(row)
    attempt = await latest(db, row.id)
    if attempt is None or attempt.status != "PENDING":
        raise ConflictException("Devam edilebilecek ödeme oturumu yok; sonucu kontrol edin")
    return hosted(row, attempt, user, gateway)


def money(value):
    try:
        amount = Decimal(str(value))
        if amount.is_finite() and 0 <= amount <= Decimal("9999999999.99"):
            return amount
    except (InvalidOperation, ValueError):
        pass
    raise AppException("Sağlayıcı ödeme tutarı geçersiz", status_code=400)


async def reconcile(db, token, gateway):
    attempt = (await db.execute(select(SubscriptionCheckout).where(SubscriptionCheckout.token_hash == token_hash(token)))).scalar_one_or_none()
    if attempt is None:
        raise NotFoundException("Üyelik ödeme oturumu bulunamadı")
    row = await billing.invoice(db, attempt.invoice_id)
    if attempt.status in {"PAID", "PAID_REVIEW", "REFUNDED"}:
        return result(row, attempt)
    organization_id, attempt_id = attempt.organization_id, attempt.id
    await db.commit()  # Do not hold the institution's write lock during network I/O.
    response = await gateway.retrieve(token, attempt_id)
    org = await platform.lock_organization(db, organization_id, include_deleted=True)
    await db.refresh(attempt); await db.refresh(row)
    if attempt.status in {"PAID", "PAID_REVIEW", "REFUNDED"}:
        return result(row, attempt)
    if not gateway.verify(response) or response.get("token") != token or response.get("conversationId") != str(attempt.id) or response.get("basketId") != str(row.id):
        raise AppException("Üyelik ödeme sonucu doğrulanamadı", status_code=400)
    if response.get("status") != "success" or response.get("paymentStatus") != "SUCCESS":
        attempt.status, attempt.updated_at = "FAILED", datetime.now(UTC)
        if row.status == "PAYMENT_REVIEW":
            row.status = "PENDING"
        await platform.commit(db)
        return result(row, attempt)
    payment_id = response.get("paymentId")
    if not isinstance(payment_id, (str, int)) or not 1 <= len(str(payment_id)) <= 240:
        raise AppException("Sağlayıcı ödeme referansı geçersiz", status_code=400)
    payment_id = str(payment_id)
    table = SubscriptionCheckout.__table__
    if (await db.execute(select(table.c.id).where(table.c.provider_payment_id == payment_id, table.c.id != attempt.id))).first():
        raise ConflictException("Sağlayıcı ödemesi farklı bir oturumla eşleşiyor")
    if attempt.provider_payment_id and attempt.provider_payment_id != payment_id:
        raise ConflictException("Ödeme oturumunun sağlayıcı referansı değişmiş; inceleme gerekli")
    paid, price = money(response.get("paidPrice")), money(response.get("price"))
    currency = response.get("currency")
    if not isinstance(currency, str) or len(currency) != 3 or not currency.isascii() or not currency.isalpha():
        raise AppException("Sağlayıcı para birimi geçersiz", status_code=400)
    items = response.get("itemTransactions")
    item = items[0] if isinstance(items, list) and len(items) == 1 and isinstance(items[0], dict) else {}
    transaction = item.get("paymentTransactionId")
    valid_item = item.get("itemId") == str(row.id) and transaction is not None and 1 <= len(str(transaction)) <= 255
    if valid_item:
        try:
            valid_item = money(item.get("price")) == row.amount
        except AppException:
            valid_item = False
    attempt.provider_payment_id, attempt.paid_amount, attempt.currency = payment_id, paid, currency
    attempt.provider_transaction_id = str(transaction) if valid_item else None
    attempt.updated_at = datetime.now(UTC)
    fraud = str(response.get("fraudStatus"))
    if fraud == "-1":
        attempt.status = "FAILED"
        if row.status == "PAYMENT_REVIEW":
            row.status = "PENDING"
        await platform.commit(db)
        return result(row, attempt)
    if fraud != "1":
        attempt.status, row.status = "REVIEW", "PAYMENT_REVIEW"
        await platform.commit(db)
        return result(row, attempt)
    reference = "IYZICO:" + payment_id
    reason = None
    if paid != row.amount or price != row.amount or currency != row.currency or not valid_item:
        reason = "Ödeme tutarı, para birimi veya kalemleri taleple eşleşmiyor"
    elif utc(row.period_end) <= datetime.now(UTC):
        reason = "Ödeme doğrulandığında teklifin üyelik dönemi geçmiş"
    elif row.status not in {"PENDING", "PAYMENT_REVIEW"}:
        reason = "Ödeme talebi farklı bir işlemle sonuçlanmış"
    if reason is None:
        try:
            attempt.status = "PAID"
            platform.audit(db, SimpleNamespace(id=None), org, "SUBSCRIPTION_PROVIDER_VERIFIED", {"invoice_id": str(row.id), "provider_payment_id": payment_id})
            await billing.apply_payment(db, org, row, reference, datetime.now(UTC))
            return result(row, attempt)
        except ConflictException as exc:
            if inspect(row).expired or inspect(attempt).expired:
                raise  # A rolled-back uniqueness conflict must not read expired ORM fields.
            reason = exc.message
    attempt.status, row.status = "PAID_REVIEW", "PAID_REVIEW"
    if row.payment_reference is None:
        row.payment_reference, row.paid_at = reference, datetime.now(UTC)
    platform.audit(db, SimpleNamespace(id=None), org, "SUBSCRIPTION_PAYMENT_REVIEW", {"invoice_id": str(row.id), "provider_payment_id": payment_id, "reason": reason})
    await platform.commit(db)
    return result(row, attempt, message=reason)


async def check_status(db, user, invoice_id, gateway, *, platform_user=False):
    if platform_user:
        row = await billing.invoice(db, invoice_id)
    else:
        await billing.require_manager(db, user)
        row = await billing.invoice(db, invoice_id, user.organization_id)
    attempt = await latest(db, row.id)
    if attempt is None:
        return result(row)
    if attempt.status == "INITIALIZING":
        if utc(attempt.created_at) + timedelta(seconds=90) < datetime.now(UTC):
            await platform.lock_organization(db, row.organization_id, include_deleted=platform_user)
            await db.refresh(attempt)
            if attempt.status != "INITIALIZING":
                return result(row, attempt)
            attempt.status, attempt.updated_at = "FAILED", datetime.now(UTC)
            await platform.commit(db)
        return result(row, attempt)
    if attempt.status not in {"PENDING", "REVIEW"}:
        return result(row, attempt)
    gateway.configured()
    secret = gateway.open(attempt.checkout_secret)
    if not isinstance(secret, dict) or not isinstance(secret.get("token"), str):
        raise AppException("Ödeme oturumu okunamadı", status_code=503)
    return await reconcile(db, secret["token"], gateway)


def checkout_data(row, attempt, user=None):
    active = bool(attempt and attempt.status in ACTIVE)
    return {**billing.invoice_data(row), "checkout_status": attempt.status if attempt else None,
        "can_cancel": row.status == "PENDING" and not active,
        "can_checkout": row.status == "PENDING" and not active and row.amount > 0 and utc(row.valid_until) > datetime.now(UTC),
        "can_resume": bool(row.status == "PENDING" and attempt and attempt.status == "PENDING" and user and user.id == attempt.created_by),
        "provider_payment_id": attempt.provider_payment_id if attempt else None,
        "provider_paid_amount": str(attempt.paid_amount) if attempt and attempt.paid_amount is not None else None,
        "provider_currency": attempt.currency if attempt else None}


async def list_data(db, rows, user=None):
    rows = list(rows)
    attempts = (await db.execute(select(SubscriptionCheckout).where(SubscriptionCheckout.invoice_id.in_([row.id for row in rows]))
        .order_by(SubscriptionCheckout.created_at.desc(), SubscriptionCheckout.id.desc()))).scalars()
    newest = {}
    for attempt in attempts:
        newest.setdefault(attempt.invoice_id, attempt)
    return [checkout_data(row, newest.get(row.id), user) for row in rows]


async def review(db, actor, invoice_id, body):
    row = await billing.invoice(db, invoice_id)
    org = await platform.lock_organization(db, row.organization_id, include_deleted=True)
    await db.refresh(row)
    digest = hashlib.sha256(json.dumps({"invoice": str(invoice_id), "actor": str(actor.id), "body": body.model_dump(mode="json", exclude={"request_id"})}, sort_keys=True).encode()).hexdigest()
    previous = await db.get(AuditLog, body.request_id)
    if previous:
        values = previous.new_values or {}
        if previous.user_id != actor.id or values.get("event") != "SUBSCRIPTION_REVIEW_COMPLETED" or values.get("digest") != digest:
            raise ConflictException("İstek kimliği başka bir uzlaştırmada kullanılmış")
        return values["response"]
    attempt = (await db.execute(select(SubscriptionCheckout).where(SubscriptionCheckout.invoice_id == row.id,
        SubscriptionCheckout.status == "PAID_REVIEW").order_by(SubscriptionCheckout.created_at.desc(), SubscriptionCheckout.id.desc()).limit(1))).scalar_one_or_none()
    if row.status != "PAID_REVIEW" or attempt is None or attempt.status != "PAID_REVIEW" or not attempt.provider_payment_id:
        raise ConflictException("Bu talepte doğrulanmış ve uzlaştırma bekleyen ödeme yok")
    reference = "IYZICO:" + attempt.provider_payment_id
    if body.action == "REFUND_RECORDED":
        if not body.refund_reference:
            raise AppException("Kontrol edilen iadenin işlem referansı gerekli", status_code=422)
        # This records an operator-verified external refund. No refund/payment
        # request is sent to a bank or the provider by this endpoint.
        attempt.status = "REFUNDED"
        row.status = "PAID" if row.payment_reference and row.payment_reference != reference else "REFUNDED"
        platform.audit(db, actor, org, "SUBSCRIPTION_REFUND_RECORDED", {"invoice_id": str(row.id), "provider_payment_id": attempt.provider_payment_id,
            "refund_reference": body.refund_reference, "amount": str(attempt.paid_amount), "currency": attempt.currency, "reason": body.reason})
    else:
        if attempt.paid_amount != row.amount or attempt.currency != row.currency or not attempt.provider_transaction_id:
            raise ConflictException("Sağlayıcı tutarı, para birimi veya kalemi uyuşmuyor; önce ödeme/iade uzlaştırılmalı")
        if row.payment_reference and row.payment_reference != reference:
            raise ConflictException("Talep başka bir tahsilatla sonuçlanmış; ek ödeme iade edilmeli")
        if not org.is_active or org.deleted_at is not None:
            raise ConflictException("Kapatılmış kuruma uzlaştırmayla erişim açılamaz; önce kurum durumunu kontrol edin")
        if body.period_start is None or body.period_end is None:
            raise AppException("Uzlaştırılan üyelik başlangıcı ve bitişi gerekli", status_code=422)
        start, end = utc(body.period_start), utc(body.period_end)
        if end <= start or end <= datetime.now(UTC):
            raise AppException("Uzlaştırılan üyelik dönemi geçerli olmalı", status_code=422)
        member = await current_member(db, org.id)
        if member and member.period_end and end < utc(member.period_end):
            raise ConflictException("Uzlaştırma mevcut üyeliğin bitişini kısaltamaz")
        used = await platform.usage(db, org.id)
        if any(used[key] > row.package_snapshot[key] for key in used):
            raise ConflictException("Ödenen paket mevcut kayıt sayısına yetmiyor; kayıtlar korunur")
        if member is None:
            member = OrganizationSubscription(organization_id=org.id, admin_status="ACTIVE", owner_user_id=row.created_by)
            db.add(member)
        member.plan_id, member.package_snapshot, member.period_start, member.period_end = row.plan_id, row.package_snapshot, start, end
        # admin_status is preserved: money never overrides an operator closure.
        attempt.status, row.status, row.settled_by = "PAID", "PAID", actor.id
        platform.audit(db, actor, org, "SUBSCRIPTION_PAYMENT_RECONCILED", {"invoice_id": str(row.id), "reason": body.reason,
            "period_start": start.isoformat(), "period_end": end.isoformat()})
    attempt.updated_at = datetime.now(UTC)
    response = checkout_data(row, attempt, actor)
    platform.audit(db, actor, org, "SUBSCRIPTION_REVIEW_COMPLETED", {"digest": digest, "invoice_id": str(row.id), "response": response}, body.request_id)
    await platform.commit(db)
    return response


async def activate_free(db, user, invoice_id):
    await billing.require_manager(db, user)
    org = await platform.lock_organization(db, user.organization_id)
    row = await billing.invoice(db, invoice_id, org.id)
    if row.status == "PAID":
        return result(row)
    if row.status != "PENDING" or row.amount != 0:
        raise ConflictException("Yalnız sıfır tutarlı ve açık paket talebi ücretsiz etkinleştirilebilir")
    attempt = await latest(db, row.id)
    if attempt and attempt.status in ACTIVE:
        raise ConflictException("Önce devam eden ödeme sonuçlanmalı")
    await validate_quote(db, org, row)
    platform.audit(db, user, org, "SUBSCRIPTION_FREE_ACTIVATED", {"invoice_id": str(row.id)})
    await billing.apply_payment(db, org, row, "FREE:" + str(row.id), datetime.now(UTC))
    return result(row)
