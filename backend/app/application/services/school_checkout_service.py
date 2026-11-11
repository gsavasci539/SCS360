"""Durable school checkouts: one reserved request, immutable merchant and verified settlement."""
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from uuid import UUID, uuid4

from sqlalchemy import select, update

from app.application.services.cash_payment_service import locked_debt, state
from app.application.services.platform_service import lock_organization
from app.application.services import school_payment_merchant as merchants
from app.core.exceptions import AppException, ConflictException, ForbiddenException, NotFoundException, ValidationException
from app.core.student_access import require_parent_child_access, require_student_access
from app.domain.services.debt_calculator import DebtCalculator
from app.infrastructure.models.models import (AuditAction, AuditLog, Debt, DebtStatus, NotificationChannel,
    NotificationJob, Payment, PaymentCheckout, PaymentMethod, Receipt, Student)
from app.infrastructure.repositories.base import BaseRepository


OPEN = {"INITIALIZING", "PENDING", "FRAUD_REVIEW", "PAID_REVIEW", "PROCESSING", "REVIEW"}


def now(): return datetime.now(UTC)


def token_hash(value): return hashlib.sha256(value.encode()).hexdigest()


def utc(value): return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def message(row):
    return {"INITIALIZING": "Ödeme başlatma sonucu bekleniyor; aynı işlemden devam edin.",
        "PENDING": "Ödeme sağlayıcısının sonucu bekleniyor.", "FRAUD_REVIEW": "Ödeme sağlayıcının risk incelemesinde.",
        "PAID_REVIEW": "Doğrulanmış ödeme için kurumun mutabakatı gerekiyor. Yeniden ödeme yapmayın.",
        "COMPLETED": "Ödeme doğrulandı ve borca uygulandı.", "FAILED": "Sağlayıcı işlemi tamamlamadı.",
        "REFUNDED": "Sağlayıcıda yapılan iade referansı kaydedildi."}.get(row.status, "Ödeme kaydı kurum tarafından kontrol edilmeli.")


def actions(tenant, row):
    own = row.created_by == tenant.user_id
    if tenant.parent_portal:
        return own and tenant.has_permission("parent.make_payment")
    return tenant.has_permission("finance.write") or (own and tenant.has_permission("parent.make_payment"))


async def allowed_actions(db, tenant, row, debt):
    if not actions(tenant, row):
        return False
    if tenant.parent_portal or not tenant.has_permission("finance.write"):
        try:
            await require_parent_child_access(db, tenant.user_id, debt.student_id)
        except ForbiddenException:
            return False
    return True


def secret(row):
    return merchants.open_school_secret(row.checkout_secret) if row.checkout_secret else None


def view(row, tenant, include_url=False, *, can_act=None):
    permitted = actions(tenant, row) if can_act is None else can_act
    stored = secret(row) if row.status == "PENDING" and row.checkout_secret and permitted else None
    expires = None
    if stored and stored.get("expires_at"):
        try: expires = datetime.fromisoformat(stored["expires_at"])
        except (TypeError, ValueError): pass
    resumable = bool(stored and stored.get("url") and expires and utc(expires) > now() and row.status == "PENDING")
    result = {"id": str(row.id), "conversation_id": str(row.id), "debt_id": str(row.debt_id),
        "amount": format(row.amount, ".2f"), "currency": row.currency, "status": row.status,
        "payment_id": str(row.payment_id) if row.payment_id else None, "message": message(row),
        "can_resume": permitted and resumable,
        "can_refresh": permitted and row.status in OPEN}
    if include_url and resumable and permitted:
        result.update(checkout_url=stored["url"], payment_page_url=stored["url"])
    return result


async def authorized(db, tenant, identifier, *, action=False):
    repository = BaseRepository(db, tenant)
    row = await repository.get_by_id(identifier, PaymentCheckout)
    debt = await repository.get_by_id(row.debt_id, Debt)
    parent = tenant.parent_portal or not tenant.has_any_permission(["finance.read", "finance.write"])
    if parent:
        await require_parent_child_access(db, tenant.user_id, debt.student_id)
        if row.created_by != tenant.user_id:
            raise ForbiddenException("Ödeme oturumu başka bir kullanıcıya ait")
    await require_student_access(db, tenant, debt.student_id)
    if action and not await allowed_actions(db, tenant, row, debt):
        raise ForbiddenException("Ödeme oturumunu yalnız başlatan kullanıcı veya yetkili finans personeli yönetebilir")
    return row


async def status(db, tenant, identifier):
    row = await authorized(db, tenant, identifier)
    debt = await BaseRepository(db, tenant).get_by_id(row.debt_id, Debt)
    return {**view(row, tenant, can_act=await allowed_actions(db, tenant, row, debt)), "remaining_amount": str(debt.remaining_amount)}


async def resume(db, tenant, identifier): return view(await authorized(db, tenant, identifier, action=True), tenant, True)


def payer_values(body):
    buyer = body.buyer or {}
    result = {}
    for key, limit in (("identityNumber", 100), ("registrationAddress", 1000), ("city", 100), ("country", 100), ("gsmNumber", 50)):
        raw = buyer.get(key, "")
        if raw is None: raw = ""
        if not isinstance(raw, str) or len(raw) > limit:
            raise ValidationException("Ödeme fatura bilgilerini kontrol edin")
        result[key] = raw.strip()
    if not all(result[key] for key in ("identityNumber", "registrationAddress", "city", "country")):
        raise ValidationException("Ödeme için kimlik numarası, adres, şehir ve ülke bilgileri gerekli")
    return result


def digest(tenant, body, buyer):
    value = {"actor": str(tenant.user_id), "organization": str(tenant.organization_id), "debt": str(body.debt_id),
        "amount": format(body.amount, ".2f"), "currency": body.currency, "buyer": buyer}
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


async def initialize(db, tenant, user, body, ip):
    buyer = payer_values(body)
    debt = await locked_debt(db, tenant, body.debt_id)
    if tenant.parent_portal or not tenant.has_permission("finance.write"):
        await require_parent_child_access(db, tenant.user_id, debt.student_id)
    await require_student_access(db, tenant, debt.student_id)
    await BaseRepository(db, tenant).get_by_id(debt.student_id, Student)
    identifier = body.request_id or uuid4()
    request_digest = digest(tenant, body, buyer)
    row = (await db.execute(select(PaymentCheckout).where(PaymentCheckout.id == identifier)
        .execution_options(populate_existing=True))).scalar_one_or_none()
    if row:
        if row.organization_id != debt.organization_id or row.created_by != tenant.user_id or not row.request_digest or not hmac.compare_digest(row.request_digest, request_digest):
            raise ConflictException("İstek kimliği farklı bir ödeme oturumunda kullanılmış")
        return view(row, tenant, True)
    raw = PaymentCheckout.__table__
    if (await db.execute(select(raw.c.id).where(raw.c.id == identifier))).first():
        raise ConflictException("İstek kimliği kullanılamıyor")
    active = (await db.execute(select(PaymentCheckout).where(PaymentCheckout.debt_id == debt.id,
        PaymentCheckout.organization_id == debt.organization_id, PaymentCheckout.status.in_(OPEN))
        .execution_options(populate_existing=True))).scalars().all()
    if active:
        if not body.request_id and len(active) == 1 and active[0].created_by == tenant.user_id and active[0].request_digest == request_digest:
            return view(active[0], tenant, True)
        raise ConflictException("Bu borç için açık ödeme oturumu bulunuyor; önce önceki işlemin sonucunu kontrol edin")
    if debt.status == DebtStatus.CANCELLED:
        raise ConflictException("İptal edilen borca ödeme yapılamaz")
    principal, paid = state(debt)
    try: DebtCalculator.validate_payment(principal, paid, body.amount)
    except ValueError as exc: raise ValidationException(str(exc)) from exc
    context = await merchants.resolve_gateway(db, debt.organization_id)
    gateway = context["gateway"]
    gateway.configured()
    if hasattr(gateway, "validate_payer"):
        gateway.validate_payer({**buyer, "gsmNumber": buyer["gsmNumber"] or user.phone or "", "email": user.email})
    snapshot = context["merchant_snapshot"] or merchants.snapshot_gateway(gateway, debt.organization_id, context["merchant_scope"])
    row = PaymentCheckout(id=identifier, organization_id=debt.organization_id, debt_id=debt.id,
        created_by=user.id, amount=body.amount, currency=body.currency, status="INITIALIZING",
        request_digest=request_digest, merchant_account_id=context["merchant_account_id"],
        merchant_scope=context["merchant_scope"], merchant_snapshot=snapshot,
        checkout_secret=merchants.seal_school_secret({"return_path": f"/parent/finances?checkout={identifier}"
            if tenant.parent_portal else f"/payment?checkout={identifier}", "callback_key": secrets.token_urlsafe(32)}))
    db.add(row); await db.flush()
    debt_id, description, organization_id = debt.id, debt.description, debt.organization_id
    # Reserve once and release the school's write lock before contacting the provider.
    await db.commit()
    callback = urlparse(gateway.settings.IYZICO_CALLBACK_URL)
    callback_key = secret(row).get("callback_key")
    query = [*parse_qsl(callback.query), ("checkout_id", str(identifier))]
    if getattr(gateway, "provider", "iyzico") != "iyzico":
        query.append(("callback_key", callback_key))
    callback_url = urlunparse(callback._replace(query=urlencode(query)))
    payer = {"id": str(user.id), "name": user.first_name, "surname": user.last_name, "email": user.email,
        **buyer, "gsmNumber": buyer["gsmNumber"] or user.phone or "", "ip": ip}
    billing = {"contactName": f"{user.first_name} {user.last_name}", "city": buyer["city"], "country": buyer["country"], "address": buyer["registrationAddress"]}
    payload = {"locale": "tr", "conversationId": str(identifier), "basketId": str(debt_id),
        "price": format(body.amount, ".2f"), "paidPrice": format(body.amount, ".2f"), "currency": body.currency,
        "paymentGroup": "PRODUCT", "enabledInstallments": [1], "callbackUrl": callback_url,
        "buyer": payer, "billingAddress": billing, "shippingAddress": billing,
        "basketItems": [{"id": str(debt_id), "name": description or "Okul ödemesi", "category1": "Eğitim", "itemType": "VIRTUAL", "price": format(body.amount, ".2f")}]}
    try:
        result = await gateway.initialize(payload)
    except AppException:
        # A timeout is not proof that no hosted session exists. Keep its UUID.
        raise AppException("Ödeme başlatma sonucu belirsiz; aynı ödeme oturumunun sonucunu kontrol edin", status_code=502) from None
    await lock_organization(db, organization_id)
    row = (await db.execute(select(PaymentCheckout).where(PaymentCheckout.id == identifier)
        .with_for_update().execution_options(populate_existing=True))).scalar_one()
    if row.status != "INITIALIZING": return view(row, tenant, True)
    if (isinstance(result, dict) and result.get("status") == "failure" and result.get("errorCode")
        and not result.get("token") and not result.get("paymentPageUrl")):
        # A definitive initialize rejection from the authenticated HTTPS API
        # differs from a timeout or a corrupt successful response.
        row.status, row.review_reason = "FAILED", "PROVIDER_INITIALIZE_REJECTED"
        await db.flush(); await db.commit()
        return view(row, tenant)
    if not gateway.verify_initial(result, identifier) or not gateway.valid_hosted_url(result.get("paymentPageUrl") if isinstance(result, dict) else None):
        raise AppException("Ödeme başlatma yanıtı doğrulanamadı; aynı oturumun sonucunu kontrol edin", status_code=502)
    ttl = result.get("tokenExpireTime", 1800)
    if isinstance(ttl, bool) or not isinstance(ttl, int) or not 1 <= ttl <= 86400:
        raise AppException("Ödeme oturumu süresi doğrulanamadı", status_code=502)
    row.token_hash = token_hash(result["token"])
    row.checkout_secret = merchants.seal_school_secret({"token": result["token"], "url": result["paymentPageUrl"],
        "expires_at": (now() + timedelta(seconds=ttl)).isoformat(),
        "callback_key": callback_key,
        "return_path": f"/parent/finances?checkout={identifier}" if tenant.parent_portal else f"/payment?checkout={identifier}"})
    row.status = "PENDING"
    await db.flush(); await db.commit()
    return view(row, tenant, True)


def proof(gateway, result, row, token):
    if hasattr(gateway, "capture_proof"):
        return gateway.capture_proof(result, row, token)
    if not gateway.verify(result) or not isinstance(result, dict):
        raise AppException("Ödeme sonucu doğrulanamadı", status_code=400)
    if result.get("token") != token or result.get("conversationId") != str(row.id):
        raise AppException("Ödeme oturumu eşleşmedi", status_code=400)
    if result.get("status") != "success" or result.get("paymentStatus") != "SUCCESS":
        return None
    provider_id = result.get("paymentId")
    if not isinstance(provider_id, str) or not 1 <= len(provider_id) <= 100:
        raise AppException("Ödeme işlem referansı doğrulanamadı", status_code=400)
    try:
        charged, price = Decimal(str(result.get("paidPrice"))), Decimal(str(result.get("price")))
    except (InvalidOperation, TypeError, ValueError):
        raise AppException("Ödeme tutarı doğrulanamadı", status_code=400) from None
    if not charged.is_finite() or not price.is_finite() or not Decimal("0") < charged <= Decimal("9999999999.99"):
        raise AppException("Ödeme tutarı doğrulanamadı", status_code=400)
    evidence = {"provider_payment_id": provider_id, "conversation_id": str(row.id), "basket_id": str(result.get("basketId", ""))[:100],
        "amount": format(charged, ".2f"), "currency": str(result.get("currency", ""))[:3], "verified_at": now().isoformat()}
    matching = result.get("basketId") == str(row.debt_id) and charged == price == row.amount and result.get("currency") == row.currency
    items = result.get("itemTransactions")
    transaction_id = None
    if isinstance(items, list) and len(items) == 1 and isinstance(items[0], dict):
        item = items[0]
        try:
            matching = matching and item.get("itemId") == str(row.debt_id) and Decimal(str(item.get("price"))) == row.amount and Decimal(str(item.get("paidPrice"))) == row.amount and str(item.get("transactionStatus")) in {"1", "2"}
        except (InvalidOperation, TypeError, ValueError): matching = False
        transaction_id = item.get("paymentTransactionId")
    else: matching = False
    if not isinstance(transaction_id, str) or not 1 <= len(transaction_id) <= 255: matching = False
    evidence["transaction_id"] = transaction_id if isinstance(transaction_id, str) and len(transaction_id) <= 255 else None
    evidence["matches_checkout"] = bool(matching)
    evidence["fraud_status"] = str(result.get("fraudStatus"))[:20]
    return evidence


async def apply_verified(db, row, actor_id=None):
    actor_id = actor_id or row.created_by
    debt = (await db.execute(select(Debt).where(Debt.id == row.debt_id).with_for_update()
        .execution_options(populate_existing=True))).scalar_one_or_none()
    if debt is None or debt.organization_id != row.organization_id or debt.deleted_at is not None or debt.status == DebtStatus.CANCELLED:
        row.status, row.review_reason = "PAID_REVIEW", "DEBT_UNAVAILABLE"; return
    try:
        principal, paid = state(debt)
        new_paid = DebtCalculator.apply_payment(principal, paid, row.amount)
    except (ValueError, ValidationException):
        row.status, row.review_reason = "PAID_REVIEW", "BALANCE_CHANGED"; return
    # The authorized original student needs a whole-school receipt snapshot,
    # including historical debts in another branch; no registry rows are exposed.
    table = Debt.__table__
    balances = (await db.execute(select(table.c.amount, table.c.paid_amount).where(table.c.organization_id == row.organization_id,
        table.c.student_id == debt.student_id, table.c.deleted_at.is_(None), table.c.status != DebtStatus.CANCELLED))).all()
    valid = all(amount is not None and paid is not None and amount.is_finite() and paid.is_finite() and
        Decimal("0") < amount <= Decimal("9999999999.99") and Decimal("0") <= paid <= amount for amount, paid in balances)
    remaining = sum((amount - paid for amount, paid in balances), Decimal("0")) - row.amount if valid else None
    if remaining is None or not Decimal("0") <= remaining <= Decimal("9999999999.99"):
        row.status, row.review_reason = "PAID_REVIEW", "STUDENT_BALANCE_INVALID"; return
    debt.paid_amount, debt.status = new_paid, DebtCalculator.calculate_status(principal, new_paid, debt.due_date)
    payment = Payment(organization_id=row.organization_id, branch_id=debt.branch_id, student_id=debt.student_id,
        debt_id=debt.id, amount=row.amount, payment_method=PaymentMethod.CREDIT_CARD, received_by=actor_id,
        notes=f'{(row.verified_metadata or {}).get("provider", "iyzico")}: {row.provider_payment_id}')
    db.add(payment); await db.flush()
    import base64
    receipt = Receipt(organization_id=row.organization_id, branch_id=debt.branch_id, student_id=debt.student_id,
        payment_id=payment.id, receipt_number=("IYZ-" if (row.verified_metadata or {}).get("provider", "iyzico") == "iyzico" else "ONL-") + base64.b32encode(payment.id.bytes).decode().rstrip("="),
        issued_by=actor_id, remaining_debt=remaining)
    db.add(receipt)
    db.add(NotificationJob(organization_id=row.organization_id, branch_id=debt.branch_id,
        channel=NotificationChannel.EMAIL, template_code="payment_received", subject="Ödeme Bildirimi",
        body=f"Ödeme doğrulandı: {row.amount} TL - Makbuz: {receipt.receipt_number}", reference_type="payment",
        reference_id=payment.id, created_by=actor_id))
    db.add(AuditLog(organization_id=row.organization_id, branch_id=debt.branch_id, user_id=actor_id,
        action=AuditAction.PAYMENT, entity_type="payment", entity_id=payment.id,
        new_values={"checkout_id": str(row.id), "amount": str(row.amount), "provider_payment_id": row.provider_payment_id}))
    row.payment_id, row.status, row.review_reason = payment.id, "COMPLETED", None
    await db.flush()


async def reconcile(db, token, identifier=None):
    query = select(PaymentCheckout).where(PaymentCheckout.id == identifier) if identifier else select(PaymentCheckout).where(PaymentCheckout.token_hash == token_hash(token))
    row = (await db.execute(query)).scalar_one_or_none()
    if row is None: raise NotFoundException("Ödeme oturumu bulunamadı")
    if not row.merchant_snapshot: raise ConflictException("Eski ödeme oturumu kendi doğrulama akışından kontrol edilmeli")
    if row.token_hash and not hmac.compare_digest(row.token_hash, token_hash(token)):
        raise AppException("Ödeme oturumu eşleşmedi", status_code=400)
    if row.payment_id or row.status == "REFUNDED": return row
    context = await merchants.resolve_gateway(db, row.organization_id, checkout=row)
    result = await context["gateway"].retrieve(token, row.id)
    evidence = proof(context["gateway"], result, row, token)
    organization_id, checkout_id = row.organization_id, row.id
    await lock_organization(db, organization_id, include_deleted=True)
    row = (await db.execute(select(PaymentCheckout).where(PaymentCheckout.id == checkout_id)
        .with_for_update().execution_options(populate_existing=True))).scalar_one()
    if row.payment_id or row.status == "REFUNDED": return row
    if row.token_hash and not hmac.compare_digest(row.token_hash, token_hash(token)):
        raise AppException("Ödeme oturumu eşleşmedi", status_code=400)
    if evidence is None:
        # No captured proof: retain the pending session; a failed/early poll is
        # not permission to initialize a second potentially chargeable session.
        if str(result.get("paymentStatus", "")).upper() in {"FAILURE", "FAILED"}:
            row.status, row.review_reason = "FAILED", "VERIFIED_PROVIDER_FAILURE"
            await db.flush(); await db.commit()
        return row
    duplicates = (await db.execute(select(PaymentCheckout.id).where(PaymentCheckout.id != row.id,
        PaymentCheckout.merchant_scope == row.merchant_scope, PaymentCheckout.provider_payment_id == evidence["provider_payment_id"])) ).first()
    if duplicates: raise ConflictException("Bu sağlayıcı ödemesi daha önce kaydedilmiş")
    row.token_hash = token_hash(token)
    row.provider_payment_id, row.provider_transaction_id = evidence["provider_payment_id"], evidence["transaction_id"]
    row.paid_amount, row.paid_currency = Decimal(evidence["amount"]), evidence["currency"]
    row.verified_at, row.verified_metadata = now(), evidence
    previous_secret = secret(row) or {"return_path": f"/payment?checkout={row.id}"}
    if not previous_secret.get("token"):
        row.checkout_secret = merchants.seal_school_secret({**previous_secret, "token": token})
    if evidence["fraud_status"] != "1":
        row.status, row.review_reason = "FRAUD_REVIEW", "PROVIDER_REVIEW"
    elif not evidence["matches_checkout"]:
        row.status, row.review_reason = "PAID_REVIEW", "PROOF_MISMATCH"
    else: await apply_verified(db, row)
    await db.flush(); await db.commit()
    return row


async def refresh(db, tenant, identifier):
    row = await authorized(db, tenant, identifier, action=True)
    if row.status not in OPEN: return view(row, tenant)
    stored = secret(row)
    token = stored.get("token") if stored else None
    if not token:
        context = await merchants.resolve_gateway(db, row.organization_id, checkout=row)
        if getattr(context["gateway"], "provider", "iyzico") in {"paytr", "sipay"}:
            token = row.id.hex
    if not token: return view(row, tenant)
    row = await reconcile(db, token, row.id)
    return view(row, tenant)


async def callback_return(db, row):
    context = await merchants.resolve_gateway(db, row.organization_id, checkout=row)
    portal = getattr(context["gateway"], "portal_url", "")
    stored = secret(row)
    path = stored.get("return_path") if stored else None
    if not path or not path.startswith(("/payment?checkout=", "/parent/finances?checkout=")):
        path = f"/payment?checkout={row.id}"
    return portal.rstrip("/") + path if portal else None
