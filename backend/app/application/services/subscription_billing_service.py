"""Commercial invoices are independent of student debts and tuition receipts."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import hashlib
import json
from uuid import UUID

from sqlalchemy import select

from app.application.services import platform_service as platform
from app.application.services.subscription_access import utc
from app.core.exceptions import AppException, ConflictException, ForbiddenException, NotFoundException
from app.core.tenant import effective_roles
from app.domain.entities.saas import OrganizationSubscription, SubscriptionCheckout, SubscriptionInvoice
from app.infrastructure.models.models import AuditLog


async def can_manage(db, user):
    if user.is_super_admin or any(role.slug in {"owner", "org_admin"} for role in effective_roles(user)):
        return True
    table = OrganizationSubscription.__table__
    owner = (await db.execute(select(table.c.owner_user_id).where(table.c.organization_id == user.organization_id))).scalar_one_or_none()
    return owner == user.id


async def require_manager(db, user):
    if not user.organization_id or not await can_manage(db, user):
        raise ForbiddenException("Üyelik ödemelerini yalnız kurum sahibi veya atanmış ödeme yetkilisi yönetebilir")


def membership_digest(member):
    values = None if member is None else {"plan": str(member.plan_id), "package": member.package_snapshot,
        "start": utc(member.period_start).isoformat() if member.period_start else None,
        "end": utc(member.period_end).isoformat() if member.period_end else None}
    return hashlib.sha256(json.dumps(values, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def invoice_data(row):
    return {"id": str(row.id), "organization_id": str(row.organization_id), "plan_id": str(row.plan_id),
        "package_name": row.package_snapshot.get("name"), "amount": str(row.amount), "currency": row.currency,
        "status": row.status, "period_start": utc(row.period_start).isoformat(), "period_end": utc(row.period_end).isoformat(),
        "valid_until": utc(row.valid_until).isoformat(), "paid_at": utc(row.paid_at).isoformat() if row.paid_at else None,
        "created_at": utc(row.created_at).isoformat()}


async def invoice(db, identifier, org_id=None):
    query = select(SubscriptionInvoice).where(SubscriptionInvoice.id == identifier)
    if org_id:
        query = query.where(SubscriptionInvoice.organization_id == org_id)
    row = (await db.execute(query)).scalar_one_or_none()
    if row is None:
        raise NotFoundException("Üyelik ödeme talebi bulunamadı")
    return row


async def create_invoice(db, user, body):
    await require_manager(db, user)
    org = await platform.lock_organization(db, user.organization_id)
    if not org.is_active:
        raise ConflictException("Kapatılmış kurum için yeni ödeme talebi açılamaz")
    digest = hashlib.sha256(f"{user.id}:{org.id}:{body.plan_id}".encode()).hexdigest()
    previous = (await db.execute(select(AuditLog).where(AuditLog.id == body.request_id))).scalar_one_or_none()
    if previous:
        values = previous.new_values or {}
        if previous.user_id != user.id or values.get("event") != "SUBSCRIPTION_INVOICE_REQUESTED" or values.get("digest") != digest:
            raise ConflictException("İstek kimliği farklı bir ödeme talebinde kullanılmış")
        return invoice_data(await invoice(db, UUID(values["invoice_id"]), org.id))
    audit_table = AuditLog.__table__
    if (await db.execute(select(audit_table.c.id).where(audit_table.c.id == body.request_id))).first():
        raise ConflictException("İstek kimliği kullanılamıyor")
    plan = await platform.get_plan(db, body.plan_id)
    if not plan.is_active:
        raise ConflictException("Paket yeni satın almaya kapalı")
    used = await platform.usage(db, org.id)
    if any(used[key] > getattr(plan, key) for key in used):
        raise ConflictException("Paket mevcut kayıt sayınıza yetmiyor; daha geniş bir paket seçin")
    member = (await db.execute(select(OrganizationSubscription).where(OrganizationSubscription.organization_id == org.id))).scalar_one_or_none()
    if member and member.admin_status != "ACTIVE":
        raise ConflictException("Kurum üyeliği platform yöneticisi tarafından kapatılmış")
    pending = (await db.execute(select(SubscriptionInvoice).where(SubscriptionInvoice.organization_id == org.id,
        SubscriptionInvoice.status.in_(["PENDING", "PAYMENT_REVIEW", "PAID_REVIEW"])).limit(2))).scalars().all()
    if len(pending) > 1:
        raise ConflictException("Birden fazla açık ödeme talebi var; platform yöneticisi incelemeli")
    if pending:
        row = pending[0]
        if row.plan_id != plan.id or row.status != "PENDING":
            raise ConflictException("Mevcut açık talebi sonuçlandırın veya iptal edin")
    else:
        now = datetime.now(UTC)
        end = utc(member.period_end) if member and member.period_end else None
        start = end if end and now < end + timedelta(days=10) else now
        row = SubscriptionInvoice(organization_id=org.id, plan_id=plan.id, created_by=user.id,
            package_snapshot=platform.plan_data(plan), amount=plan.price, currency=plan.currency,
            period_start=start, period_end=platform.add_months(start, plan.period_months), base_period_end=end, base_membership_digest=membership_digest(member),
            valid_until=now + timedelta(days=1), status="PENDING")
        db.add(row); await db.flush(); await db.refresh(row)
    platform.audit(db, user, org, "SUBSCRIPTION_INVOICE_REQUESTED", {"digest": digest, "invoice_id": str(row.id)}, body.request_id)
    await platform.commit(db)
    return invoice_data(row)


async def cancel_invoice(db, user, identifier):
    await require_manager(db, user)
    org = await platform.lock_organization(db, user.organization_id)
    row = await invoice(db, identifier, org.id)
    if row.status == "CANCELLED":
        return invoice_data(row)
    if row.status != "PENDING":
        raise ConflictException("Sonuçlanmış ödeme talebi iptal edilemez")
    active = (await db.execute(select(SubscriptionCheckout.id).where(SubscriptionCheckout.invoice_id == row.id,
        SubscriptionCheckout.status.in_(["INITIALIZING", "PENDING", "REVIEW", "PAID", "PAID_REVIEW"])).limit(1))).first()
    if active:
        raise ConflictException("Ödeme sağlayıcısındaki işlem sonuçlanmadan talep iptal edilemez")
    row.status = "CANCELLED"
    platform.audit(db, user, org, "SUBSCRIPTION_INVOICE_CANCELLED", {"invoice_id": str(row.id)})
    await platform.commit(db)
    return invoice_data(row)


async def apply_payment(db, org, row, reference, paid_at, actor=None):
    member = (await db.execute(select(OrganizationSubscription).where(OrganizationSubscription.organization_id == org.id))).scalar_one_or_none()
    current_end = utc(member.period_end) if member and member.period_end else None
    base = utc(row.base_period_end) if row.base_period_end else None
    if current_end != base or membership_digest(member) != row.base_membership_digest:
        raise ConflictException("Üyelik ödeme talebinden sonra değişti; ödeme uzlaştırılmalı")
    used = await platform.usage(db, org.id)
    if any(used[key] > row.package_snapshot[key] for key in used):
        raise ConflictException("Ödenen paket mevcut kayıt sayısına yetmiyor; ödeme uzlaştırılmalı")
    table = SubscriptionInvoice.__table__
    if (await db.execute(select(table.c.id).where(table.c.payment_reference == reference, table.c.id != row.id))).first():
        raise ConflictException("Ödeme referansı başka bir talep için kullanılmış")
    if member is None:
        member = OrganizationSubscription(organization_id=org.id, admin_status="ACTIVE", owner_user_id=row.created_by)
        db.add(member)
    keep_start = member.period_start is not None and current_end is not None and paid_at < current_end + timedelta(days=10)
    member.period_start = member.period_start if keep_start else row.period_start
    member.period_end = row.period_end
    member.plan_id, member.package_snapshot = row.plan_id, row.package_snapshot
    row.status, row.paid_at, row.payment_reference = "PAID", paid_at, reference
    row.settled_by = actor.id if actor else None
    # Administrative closure is independent of payment and stays in effect.
    if actor:
        platform.audit(db, actor, org, "SUBSCRIPTION_RECEIPT_VERIFIED", {"invoice_id": str(row.id), "amount": str(row.amount), "currency": row.currency})
    await platform.commit(db)
    return invoice_data(row)


async def settle_manual(db, actor, identifier, body):
    row = await invoice(db, identifier)
    org = await platform.lock_organization(db, row.organization_id, include_deleted=True)
    await db.refresh(row)
    if Decimal(body.amount) != row.amount or body.currency != row.currency:
        raise AppException("Ödeme tutarı ve para birimi talep ile eşleşmeli", status_code=422)
    reference = "MANUAL:" + body.payment_reference
    if row.status == "PAID":
        if row.payment_reference != reference:
            raise ConflictException("Talep farklı bir ödeme ile sonuçlanmış")
        return invoice_data(row)
    if row.status != "PENDING":
        raise ConflictException("Bu ödeme talebi tahsilata açık değil")
    online = (await db.execute(select(SubscriptionCheckout.id).where(SubscriptionCheckout.invoice_id == row.id,
        SubscriptionCheckout.status.in_(["INITIALIZING", "PENDING", "REVIEW", "PAID", "PAID_REVIEW"])).limit(1))).first()
    if online:
        raise ConflictException("Online ödeme sonuçlanmadan ayrı tahsilat kaydedilemez")
    paid_at = utc(body.paid_at or datetime.now(UTC))
    if paid_at > datetime.now(UTC) + timedelta(minutes=1) or paid_at > utc(row.valid_until):
        raise AppException("Ödeme tarihi talebin geçerlilik süresi içinde olmalı", status_code=422)
    return await apply_payment(db, org, row, reference, paid_at, actor)
