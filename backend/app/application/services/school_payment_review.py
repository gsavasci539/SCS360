"""Review captured school payments; never sends a provider payment or refund."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import hmac
import json
import re

from sqlalchemy import and_, func, or_, select

from app.application.services.platform_service import lock_organization
from app.application.services.school_checkout_service import apply_verified, utc
from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException, ValidationException
from app.core.responses import paginate
from app.core.student_access import accessible_student_ids
from app.infrastructure.models.models import (AuditAction, AuditLog, Branch, Debt, DebtStatus, PaymentCheckout,
    Receipt, SchoolPaymentMerchant, Student)

EVENT = "SCHOOL_PAYMENT_REVIEW_COMPLETED"
MAX_MONEY = Decimal("9999999999.99")


def require_access(tenant, write=False):
    if tenant.is_super_admin or tenant.organization_id is None or tenant.parent_portal or not tenant.has_any_permission(["finance.write"] if write else ["finance.read", "finance.write"]):
        raise ForbiddenException("Mutabakat için seçilmiş kurumda güncel finans yetkisi gerekli")


async def scoped(db, tenant):
    require_access(tenant)
    debt, branches = Debt.__table__, Branch.__table__
    allowed = and_(debt.c.organization_id == tenant.organization_id,
        debt.c.branch_id.in_(select(branches.c.id).where(branches.c.organization_id == tenant.organization_id)))
    children = await accessible_student_ids(db, tenant)
    if tenant.branch_ids:
        allowed = and_(allowed, debt.c.branch_id.in_(tenant.branch_ids))
    if children is not None:
        allowed = and_(allowed, debt.c.student_id.in_(children))
    if not tenant.branch_ids and children is None:
        allowed = or_(allowed, debt.c.id.is_(None))
    return select(PaymentCheckout).outerjoin(debt, debt.c.id == PaymentCheckout.debt_id).where(
        PaymentCheckout.organization_id == tenant.organization_id, allowed)


async def load(db, tenant, identifier, locked=False):
    query = (await scoped(db, tenant)).where(PaymentCheckout.id == identifier).execution_options(populate_existing=True)
    if locked: query = query.with_for_update(of=PaymentCheckout)
    row = (await db.execute(query)).scalar_one_or_none()
    if row is None: raise NotFoundException("Ödeme inceleme kaydı bulunamadı")
    return row


def money(value):
    try:
        result = Decimal(str(value))
        return result if result.is_finite() and 0 <= result <= MAX_MONEY else None
    except (InvalidOperation, TypeError, ValueError):
        return None


def text_money(value):
    known = money(value)
    return format(known, ".2f") if known is not None else None


async def debt_data(db, row, locked=False):
    table = Debt.__table__
    query = select(table).where(table.c.id == row.debt_id, table.c.organization_id == row.organization_id)
    if locked: query = query.with_for_update()
    return (await db.execute(query)).mappings().first()


async def eligibility(db, tenant, row, debt):
    proof = row.verified_metadata if isinstance(row.verified_metadata, dict) else {}
    amount, paid = money(row.amount), money(row.paid_amount)
    scope = "school:" + str(row.merchant_account_id) if row.merchant_account_id else "legacy:" + str(row.organization_id)
    verified = bool(row.status == "PAID_REVIEW" and not row.payment_id and row.verified_at and row.merchant_snapshot
        and row.merchant_scope == scope and row.provider_payment_id and paid is not None and paid > 0
        and isinstance(row.paid_currency, str) and re.fullmatch(r"[A-Z]{3}", row.paid_currency)
        and proof.get("provider_payment_id") == row.provider_payment_id and proof.get("conversation_id") == str(row.id)
        and money(proof.get("amount")) == paid and proof.get("currency") == row.paid_currency and proof.get("fraud_status") == "1"
        and proof.get("transaction_id") == row.provider_transaction_id)
    apply = bool(verified and amount is not None and amount > 0 and paid == amount and row.paid_currency == row.currency
        and proof.get("matches_checkout") is True and proof.get("basket_id") == str(row.debt_id)
        and isinstance(row.provider_transaction_id, str) and 1 <= len(row.provider_transaction_id) <= 255
        and debt and debt["deleted_at"] is None and str(getattr(debt["status"], "value", debt["status"])) != "CANCELLED")
    if apply:
        principal, already = money(debt["amount"]), money(debt["paid_amount"])
        apply = principal is not None and principal > 0 and already is not None and 0 <= already <= principal and principal - already >= amount
        table = Debt.__table__
        balances = (await db.execute(select(table.c.amount, table.c.paid_amount).where(table.c.organization_id == row.organization_id,
            table.c.student_id == debt["student_id"], table.c.deleted_at.is_(None), table.c.status != DebtStatus.CANCELLED))).all()
        valid = all(money(a) is not None and money(a) > 0 and money(p) is not None and 0 <= money(p) <= money(a) for a, p in balances)
        remaining = sum((money(a)-money(p) for a, p in balances), Decimal(0))-amount if valid else None
        apply = bool(apply and remaining is not None and 0 <= remaining <= MAX_MONEY)
    write = not tenant.parent_portal and tenant.has_permission("finance.write")
    return bool(write and apply), bool(write and verified)


def revision(row, debt):
    values = {key: getattr(row, key) for key in ("id", "organization_id", "debt_id", "merchant_scope", "merchant_account_id", "status",
        "amount", "currency", "payment_id", "provider_payment_id", "provider_transaction_id", "paid_amount", "paid_currency", "verified_at", "verified_metadata")}
    values["debt"] = dict(debt) if debt else None
    return hashlib.sha256(json.dumps(values, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


async def metadata(db, tenant, row, events=True):
    debt = await debt_data(db, row)
    student = None
    if debt:
        table = Student.__table__
        student = (await db.execute(select(table.c.id, table.c.first_name, table.c.last_name).where(table.c.id == debt["student_id"], table.c.organization_id == row.organization_id))).first()
    can_apply, can_refund = await eligibility(db, tenant, row, debt)
    receipt_id = await db.scalar(select(Receipt.id).where(Receipt.payment_id == row.payment_id)) if row.payment_id else None
    environment = await db.scalar(select(SchoolPaymentMerchant.environment).where(SchoolPaymentMerchant.id == row.merchant_account_id,
        SchoolPaymentMerchant.organization_id == row.organization_id)) if row.merchant_account_id else None
    remaining = money(debt["amount"])-money(debt["paid_amount"]) if debt and money(debt["amount"]) is not None and money(debt["paid_amount"]) is not None else None
    result = {"id": str(row.id), "debt_id": str(row.debt_id), "student_id": str(student.id) if student else None,
        "student_name": f"{student.first_name} {student.last_name}" if student else None,
        "amount": text_money(row.amount), "currency": row.currency, "paid_amount": text_money(row.paid_amount), "paid_currency": row.paid_currency,
        "status": row.status, "review_reason": row.review_reason, "provider_payment_id": row.provider_payment_id,
        "provider_transaction_id": row.provider_transaction_id, "verified_at": utc(row.verified_at).isoformat() if row.verified_at else None,
        "created_at": utc(row.created_at).isoformat(), "remaining_amount": text_money(remaining), "revision": revision(row, debt),
        "can_apply": can_apply, "can_refund": can_refund, "environment": environment,
        "payment_id": str(row.payment_id) if row.payment_id else None, "receipt_id": str(receipt_id) if receipt_id else None, "review_events": []}
    if events:
        logs = (await db.execute(select(AuditLog).where(AuditLog.organization_id == row.organization_id, AuditLog.entity_type == "school_payment_review",
            AuditLog.entity_id == row.id, AuditLog.user_id == tenant.user_id).order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(10))).scalars().all()
        result["review_events"] = [{"request_id": str(log.id), "action": (log.new_values or {}).get("action"),
            "result_status": (log.new_values or {}).get("result_status"), "created_at": utc(log.created_at).isoformat()} for log in logs]
    return result


async def listing(db, tenant, page, page_size):
    query = (await scoped(db, tenant)).where(PaymentCheckout.status == "PAID_REVIEW")
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    rows = (await db.execute(query.order_by(PaymentCheckout.created_at, PaymentCheckout.id).offset((page-1)*page_size).limit(page_size))).scalars().all()
    return paginate([await metadata(db, tenant, row, False) for row in rows], total, page, page_size)


async def review(db, tenant, identifier, body):
    require_access(tenant, True)
    await load(db, tenant, identifier)
    await lock_organization(db, tenant.organization_id, include_deleted=True)
    row = await load(db, tenant, identifier, True)
    digest = hashlib.sha256(json.dumps({"actor": str(tenant.user_id), "organization": str(tenant.organization_id), "checkout": str(identifier),
        "body": body.model_dump(mode="json", exclude={"request_id"})}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    table = AuditLog.__table__
    prior = (await db.execute(select(table).where(table.c.id == body.request_id))).mappings().first()
    if prior:
        values = prior["new_values"] or {}
        if prior["organization_id"] != tenant.organization_id or prior["user_id"] != tenant.user_id or prior["entity_id"] != identifier or values.get("event") != EVENT or not hmac.compare_digest(values.get("digest", ""), digest):
            raise ConflictException("İstek kimliği farklı bir mutabakat işleminde kullanılmış")
        return values["response"]
    debt = await debt_data(db, row, True)
    if body.expected_revision != revision(row, debt):
        raise ConflictException("Ödeme veya borç değişmiş; güncel inceleme kaydını yükleyin")
    can_apply, can_refund = await eligibility(db, tenant, row, debt)
    if body.action == "APPLY":
        if not can_apply: raise ConflictException("Bu ödeme özgün borca uygulanmaya uygun değil; doğrulanmış iade veya kayıt incelemesi gerekli")
        await apply_verified(db, row, actor_id=tenant.user_id)
        if row.status != "COMPLETED": raise ConflictException("Borç bakiyesi değişmiş; güncel kaydı inceleyin")
    else:
        if not can_refund: raise ConflictException("Bu kayıtta doğrulanmış ve iade kaydı bekleyen ödeme yok")
        if body.refund_amount != row.paid_amount or body.refund_currency != row.paid_currency:
            raise ConflictException("Yalnız doğrulanmış tahsilatın tam tutarı ve para birimiyle iade kaydedilebilir")
        if body.refunded_at < utc(row.created_at)-timedelta(minutes=5):
            raise ValidationException("İade tarihi ödeme oturumu oluşturulmadan önce olamaz")
        duplicate = await db.scalar(select(table.c.id).where(table.c.organization_id == row.organization_id,
            table.c.entity_type == "school_payment_review", table.c.new_values["event"].as_string() == EVENT,
            table.c.new_values["merchant_scope"].as_string() == row.merchant_scope,
            table.c.new_values["refund_reference"].as_string() == body.refund_reference))
        if duplicate: raise ConflictException("Bu sağlayıcı hesabında iade referansı daha önce kaydedilmiş")
        row.status, row.review_reason = "REFUNDED", "EXTERNAL_REFUND_RECORDED"
    log = AuditLog(id=body.request_id, organization_id=row.organization_id, branch_id=debt["branch_id"] if debt else None,
        user_id=tenant.user_id, action=AuditAction.UPDATE, entity_type="school_payment_review", entity_id=row.id, created_at=datetime.now(UTC),
        new_values={"event": EVENT, "digest": digest, "action": body.action, "result_status": row.status, "reason": body.reason,
            "merchant_scope": row.merchant_scope, "provider_payment_id": row.provider_payment_id,
            "refund_reference": body.refund_reference, "refund_amount": text_money(body.refund_amount), "refund_currency": body.refund_currency,
            "refunded_at": body.refunded_at.isoformat() if body.refunded_at else None})
    db.add(log); await db.flush()
    response = await metadata(db, tenant, row)
    log.new_values = {**log.new_values, "response": response}
    await db.flush()
    return response
