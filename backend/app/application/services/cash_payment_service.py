"""Canonical ledger collection and cancellation with school-level serialization."""
import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select

from app.application.services.platform_service import lock_organization
from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException, ValidationException
from app.core.responses import paginate
from app.domain.services.debt_calculator import DebtCalculator
from app.infrastructure.models.models import (AuditAction, AuditLog, Debt, DebtStatus, NotificationChannel,
    NotificationJob, Payment, PaymentCheckout, PaymentMethod, Receipt, ReceiptStatus, Student)
from app.infrastructure.repositories.base import BaseRepository


MAX_MONEY = Decimal("9999999999.99")


async def locked_debt(db, tenant, identifier):
    probe = await BaseRepository(db, tenant).get_by_id(UUID(str(identifier)), Debt)
    organization_id = probe.organization_id
    await lock_organization(db, organization_id)
    row = (await db.execute(select(Debt).where(Debt.id == probe.id, Debt.organization_id == organization_id, Debt.deleted_at.is_(None))
        .with_for_update().execution_options(populate_existing=True))).scalar_one_or_none()
    if row is None:
        raise NotFoundException("Borç kaydı bulunamadı")
    if not tenant.can_access_branch(row.branch_id):
        raise ForbiddenException()
    return row


def state(debt, *, allow_overpaid=False):
    try:
        amount, paid = Decimal(str(debt.amount)), Decimal(str(debt.paid_amount))
        valid = amount.is_finite() and paid.is_finite() and 0 < amount <= MAX_MONEY and 0 <= paid <= MAX_MONEY
        valid = valid and (allow_overpaid or paid <= amount)
    except (InvalidOperation, TypeError, ValueError):
        valid = False
    if not valid:
        raise ValidationException("Borç kaydının eski tutar veya ödeme bilgileri incelenmeli")
    return amount, paid


def fingerprint(debt, tenant, body):
    values = {"organization_id": str(debt.organization_id), "actor_id": str(tenant.user_id),
        "debt_id": str(debt.id), "amount": format(Decimal(str(body.amount)), ".2f"),
        "payment_method": body.payment_method, "notes": body.notes or None}
    return hashlib.sha256(json.dumps(values, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def response(payment, receipt):
    if receipt.remaining_debt is None or not receipt.remaining_debt.is_finite():
        raise ConflictException("Makbuzun eski bakiye kaydı incelenmeli")
    return {"payment_id": str(payment.id), "receipt_id": str(receipt.id), "receipt_number": receipt.receipt_number,
        "remaining_debt": format(receipt.remaining_debt, ".2f")}


async def replay(db, tenant, debt, body):
    if body.request_id is None:
        return None
    payment = (await db.execute(select(Payment).where(Payment.id == body.request_id)
        .execution_options(populate_existing=True))).scalar_one_or_none()
    if payment is None:
        table = Payment.__table__
        if (await db.execute(select(table.c.id).where(table.c.id == body.request_id))).first():
            raise ConflictException("İstek kimliği başka bir tahsilatta kullanılmış")
        return None
    same = (payment.organization_id == debt.organization_id and payment.debt_id == debt.id
        and payment.received_by == tenant.user_id and payment.amount == body.amount
        and payment.payment_method == PaymentMethod(body.payment_method))
    audits = (await db.execute(select(AuditLog.new_values).where(AuditLog.organization_id == debt.organization_id,
        AuditLog.entity_type == "payment", AuditLog.entity_id == payment.id, AuditLog.action == AuditAction.PAYMENT))).scalars().all()
    digests = {row["request_fingerprint"] for row in audits if isinstance(row, dict) and row.get("request_fingerprint")}
    # Metadata edits must not change the original idempotent request snapshot.
    same = same and (len(digests) == 1 and hmac.compare_digest(next(iter(digests)), fingerprint(debt, tenant, body))
        if digests else (payment.notes or None) == (body.notes or None))
    if not same:
        raise ConflictException("İstek kimliği farklı bir tahsilat içeriğinde kullanılmış")
    if payment.cancelled_at is not None:
        raise ConflictException("Bu isteğin tahsilatı iptal edilmiş; yeni işlem için yeni bir istek kimliği kullanın")
    receipts = (await db.execute(select(Receipt).where(Receipt.payment_id == payment.id))).scalars().all()
    if len(receipts) != 1:
        raise ConflictException("Tahsilatın makbuz kaydı incelenmeli")
    return response(payment, receipts[0])


async def collect(db, tenant, body):
    debt = await locked_debt(db, tenant, body.debt_id)
    previous = await replay(db, tenant, debt, body)
    if previous is not None:
        return previous
    if debt.status == DebtStatus.CANCELLED:
        raise ValidationException("İptal edilmiş borca ödeme alınamaz")
    amount, paid = state(debt)
    payment_amount = Decimal(str(body.amount)).quantize(Decimal("0.01"))
    try:
        new_paid = DebtCalculator.apply_payment(amount, paid, payment_amount)
    except ValueError as exc:
        raise ValidationException(str(exc)) from exc
    payment = Payment(id=body.request_id or uuid4(), organization_id=debt.organization_id,
        branch_id=debt.branch_id, student_id=debt.student_id, debt_id=debt.id, amount=payment_amount,
        payment_method=PaymentMethod(body.payment_method), notes=body.notes, received_by=tenant.user_id)
    debt.paid_amount = new_paid
    debt.status = DebtCalculator.calculate_status(amount, new_paid, debt.due_date)
    db.add(payment)
    await db.flush()
    remaining = await db.scalar(select(func.coalesce(func.sum(Debt.amount - Debt.paid_amount), 0)).where(
        Debt.organization_id == debt.organization_id, Debt.student_id == debt.student_id,
        Debt.deleted_at.is_(None), Debt.status != DebtStatus.CANCELLED))
    remaining = Decimal(str(remaining))
    if not remaining.is_finite() or not 0 <= remaining <= MAX_MONEY:
        raise ValidationException("Öğrencinin toplam borç bakiyesi incelenmeli")
    number = "RCP-" + base64.b32encode(payment.id.bytes).decode("ascii").rstrip("=")
    receipt = Receipt(organization_id=debt.organization_id, branch_id=debt.branch_id, student_id=debt.student_id,
        payment_id=payment.id, receipt_number=number, status=ReceiptStatus.ACTIVE,
        issued_by=tenant.user_id, remaining_debt=remaining)
    db.add(receipt)
    db.add(NotificationJob(organization_id=debt.organization_id, branch_id=debt.branch_id,
        channel=NotificationChannel.EMAIL, template_code="payment_received", subject="Ödeme Bildirimi",
        body=f"Ödeme alındı: {payment_amount} TL - Makbuz: {number}", reference_type="payment",
        reference_id=payment.id, created_by=tenant.user_id))
    db.add(AuditLog(organization_id=debt.organization_id, branch_id=debt.branch_id, user_id=tenant.user_id,
        action=AuditAction.PAYMENT, entity_type="payment", entity_id=payment.id,
        new_values={"amount": str(payment_amount), "debt_id": str(debt.id), "request_fingerprint": fingerprint(debt, tenant, body)}))
    await db.flush()
    return response(payment, receipt)


async def cancel(db, tenant, identifier, body):
    probe = await BaseRepository(db, tenant).get_by_id(identifier, Payment)
    debt = await locked_debt(db, tenant, probe.debt_id)
    payment = (await db.execute(select(Payment).where(Payment.id == identifier)
        .with_for_update().execution_options(populate_existing=True))).scalar_one_or_none()
    if payment is None:
        raise NotFoundException("Tahsilat bulunamadı")
    if payment.cancelled_at is not None:
        return {"payment_id": str(payment.id), "status": "CANCELLED"}
    if (await db.execute(select(PaymentCheckout.id).where(PaymentCheckout.payment_id == payment.id))).first():
        raise ConflictException("Online tahsilat için sağlayıcı iadesi ve mutabakat kaydı gerekir; nakit iptali uygulanamaz")
    if str(payment.status or "").lower() != "completed":
        raise ConflictException("Tahsilatın eski işlem durumu incelenmeli")
    _, paid = state(debt, allow_overpaid=True)
    payment_amount = Decimal(str(payment.amount))
    if not payment_amount.is_finite() or payment_amount <= 0:
        raise ValidationException("Eski tahsilat tutarı incelenmeli")
    try:
        new_paid = DebtCalculator.reverse_payment(paid, payment_amount)
    except ValueError as exc:
        raise ValidationException(str(exc)) from exc
    payment.cancelled_at, payment.cancelled_by, payment.cancel_reason = datetime.now(UTC), tenant.user_id, body.cancel_reason
    payment.status = "cancelled"
    debt.paid_amount = new_paid
    if debt.status != DebtStatus.CANCELLED:
        debt.status = DebtCalculator.calculate_status(debt.amount, new_paid, debt.due_date)
    for receipt in (await db.execute(select(Receipt).where(Receipt.payment_id == payment.id))).scalars():
        receipt.status = ReceiptStatus.CANCELLED
    db.add(AuditLog(organization_id=payment.organization_id, branch_id=payment.branch_id, user_id=tenant.user_id,
        action=AuditAction.CANCEL_PAYMENT, entity_type="payment", entity_id=payment.id))
    await db.flush()
    return {"payment_id": str(payment.id), "status": "CANCELLED"}


async def debt_options(db, tenant, page, page_size, search, selected_id):
    if tenant.organization_id is None:
        raise ForbiddenException("Önce kurum çalışma alanını seçin")
    base = select(Debt.id, Debt.amount, Debt.paid_amount, Debt.description, Student.first_name, Student.last_name).join(
        Student, Student.id == Debt.student_id).where(Debt.organization_id == tenant.organization_id,
        Student.organization_id == tenant.organization_id, Debt.deleted_at.is_(None), Student.deleted_at.is_(None),
        Debt.status != DebtStatus.CANCELLED, Debt.amount > 0, Debt.amount <= MAX_MONEY,
        Debt.paid_amount >= 0, Debt.paid_amount <= Debt.amount)
    def data(row):
        return {"id": str(row.id), "name": f"{row.first_name} {row.last_name} · {row.description or 'Borç kaydı'} · Kalan {row.amount - row.paid_amount:.2f} TL"}
    selected = (await db.execute(base.where(Debt.id == selected_id))).first() if selected_id else None
    query = base.where(Debt.amount > Debt.paid_amount)
    if search:
        query = query.where(or_(Student.first_name.icontains(search, autoescape=True),
            Student.last_name.icontains(search, autoescape=True), Debt.description.icontains(search, autoescape=True)))
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    rows = (await db.execute(query.order_by(Student.first_name, Student.last_name, Debt.due_date, Debt.id)
        .offset((page - 1) * page_size).limit(page_size))).all()
    return {**paginate([data(row) for row in rows], total, page, page_size), "selected": data(selected) if selected else None}


async def payment_data(db, items):
    identifiers = [row.id for row in items]
    students = (await db.execute(select(Student.id, Student.first_name, Student.last_name).where(
        Student.id.in_([row.student_id for row in items])))).all()
    names = {row.id: " ".join(value for value in (row.first_name, row.last_name) if value) for row in students}
    online = set((await db.execute(select(PaymentCheckout.payment_id).where(
        PaymentCheckout.payment_id.in_(identifiers)))).scalars())
    output = []
    for row in items:
        amount = Decimal(str(row.amount)) if row.amount is not None else None
        valid = amount is not None and amount.is_finite()
        cancelled = row.cancelled_at is not None or str(row.status or "").lower() == "cancelled"
        output.append({"id": str(row.id), "student_id": str(row.student_id), "student_name": names.get(row.student_id) or None,
            "amount": format(amount, ".2f") if valid else None, "payment_method": row.payment_method.value,
            "payment_date": row.payment_date.isoformat() if row.payment_date else None,
            "cancelled": cancelled, "status": "CANCELLED" if cancelled else str(row.status or "UNKNOWN").upper(),
            "requires_review": not valid or (valid and amount <= 0), "requires_provider_refund": row.id in online})
    return output
