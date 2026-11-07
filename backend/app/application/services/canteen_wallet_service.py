from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import case, func, or_, select, update

from app.application.services.operations_service import identifier
from app.core.exceptions import ConflictException, ForbiddenException, ValidationException
from app.core.student_access import require_student_access
from app.core.dates import school_datetime, school_today
from app.domain.entities.canteen import CanteenDietaryRestriction, CanteenOrder, CanteenProduct, CanteenWalletTransaction
from app.infrastructure.models.models import Student, StudentStatus, StudentWallet
from app.infrastructure.repositories.base import BaseRepository


async def wallet(db, tenant, student_id):
    student = await BaseRepository(db, tenant).get_by_id(identifier(student_id), Student, for_update=True)
    await require_student_access(db, tenant, student.id)
    row = await db.get(StudentWallet, student.id)
    if row is None:
        ledger = (await db.execute(select(CanteenWalletTransaction).where(
            CanteenWalletTransaction.student_id == student.id, CanteenWalletTransaction.status == "COMPLETED"))).scalars().all()
        balance = sum((row.amount if row.transaction_type == "CREDIT" else -row.amount if row.transaction_type == "DEBIT" else Decimal(0) for row in ledger), Decimal(0))
        spent = sum((row.amount for row in ledger if row.transaction_type in {"DEBIT", "SALE"} and school_datetime(row.created_at).date() == school_today()), Decimal(0))
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        insert = sqlite_insert if db.bind.dialect.name == "sqlite" else pg_insert
        await db.execute(insert(StudentWallet).values(student_id=student.id, balance=balance,
            today_spent=spent, spent_date=school_today(), restricted_categories=[], restricted_allergens=[]).on_conflict_do_nothing(index_elements=["student_id"]))
        row = await db.get(StudentWallet, student.id)
    return student, row


def serialize(student, row):
    return {"student_id": str(student.id), "student_name": f"{student.first_name} {student.last_name}",
        "current_balance": float(row.balance), "balance": float(row.balance), "new_balance": float(row.balance),
        "daily_limit": float(row.daily_limit) if row.daily_limit is not None else None,
        "today_spent": float(row.today_spent) if row.spent_date == school_today() else 0,
        "daily_spent": float(row.today_spent) if row.spent_date == school_today() else 0,
        "restricted_categories": row.restricted_categories, "restricted_allergens": row.restricted_allergens,
        "dietary_restrictions": row.restricted_allergens}


async def topup(db, tenant, student_id, amount, payment_method, reference=None):
    student, row = await wallet(db, tenant, student_id)
    try:
        value = Decimal(str(amount))
        if not value.is_finite() or not 0 < value <= Decimal("99999999.99"):
            raise ValueError()
        value = value.quantize(Decimal("0.01"))
    except (ValueError, ArithmeticError) as exc:
        raise ValidationException("Yükleme tutarı geçersiz") from exc
    if value <= 0:
        raise ValidationException("Yükleme tutarı pozitif olmalı")
    await db.execute(update(StudentWallet).where(StudentWallet.student_id == student.id).values(balance=StudentWallet.balance + value))
    transaction = CanteenWalletTransaction(student_id=student.id, amount=value, transaction_type="CREDIT",
        payment_method=payment_method, reference_number=reference, processed_by=tenant.user_id, status="COMPLETED")
    db.add(transaction); await db.flush(); await db.refresh(row)
    return dict(serialize(student, row), transaction_id=str(transaction.id), amount=float(value))


async def restrictions(db, tenant, body):
    student, row = await wallet(db, tenant, body.student_id)
    if body.daily_limit is not None and Decimal(str(body.daily_limit)) < 0:
        raise ValidationException("Günlük limit negatif olamaz")
    row.daily_limit = body.daily_limit
    row.restricted_categories, row.restricted_allergens = body.restricted_categories, body.restricted_allergens
    await db.flush()
    return serialize(student, row)


async def purchase(db, tenant, student_id, *, product_id=None, price=None, quantity=1, name=None, category=None, payment_method="WALLET"):
    student, row = await wallet(db, tenant, student_id)
    if student.status != StudentStatus.ACTIVE:
        raise ValidationException("Öğrenci aktif değil")
    if quantity < 1:
        raise ValidationException("Adet en az 1 olmalı")
    product = None
    if product_id:
        product = (await db.execute(select(CanteenProduct).where(CanteenProduct.id == identifier(product_id),
            CanteenProduct.branch_id == student.branch_id, CanteenProduct.is_available.is_(True)))).scalar_one_or_none()
        if product is None:
            raise ValidationException("Ürün öğrencinin şubesinde satışa açık değil")
        price, name, category = product.price, product.name, product.category
    dietary = set((await db.execute(select(CanteenDietaryRestriction.restriction).where(
        CanteenDietaryRestriction.student_id == student.id, CanteenDietaryRestriction.is_active.is_(True)))).scalars())
    restricted = dietary | set(row.restricted_allergens or [])
    if category in (row.restricted_categories or []):
        raise ValidationException("Bu ürün kategorisi öğrenci için kısıtlanmış")
    if restricted and (product is None or restricted.intersection(product.allergens or [])):
        raise ValidationException("Öğrencinin beslenme kısıtları bu satışa izin vermiyor")
    try:
        total = (Decimal(str(price)) * quantity).quantize(Decimal("0.01"))
        if not total.is_finite() or not 0 < total <= Decimal("99999999.99"):
            raise ValueError()
    except (ValueError, ArithmeticError) as exc:
        raise ValidationException("Satış tutarı pozitif olmalı") from exc
    spent = case((StudentWallet.spent_date == school_today(), StudentWallet.today_spent), else_=0)
    method = (payment_method or "WALLET").upper()
    if method not in {"WALLET", "CASH", "CARD", "CREDIT_CARD"}:
        raise ValidationException("Geçersiz ödeme yöntemi")
    from_wallet = method == "WALLET"
    applied = await db.execute(update(StudentWallet).where(StudentWallet.student_id == student.id,
        StudentWallet.balance >= total if from_wallet else True,
        or_(StudentWallet.daily_limit.is_(None), spent + total <= StudentWallet.daily_limit))
        .values(balance=StudentWallet.balance-total if from_wallet else StudentWallet.balance,
            today_spent=spent+total, spent_date=school_today()))
    if applied.rowcount != 1:
        raise ConflictException("Bakiye yetersiz veya günlük harcama limiti aşıldı")
    transaction = CanteenWalletTransaction(student_id=student.id, amount=total, transaction_type="DEBIT" if from_wallet else "SALE",
        payment_method=payment_method or "WALLET", processed_by=tenant.user_id, status="COMPLETED", notes=f"{quantity}x {name or 'Kantin satışı'}")
    db.add(transaction)
    order = None
    if product:
        now = school_datetime(datetime.now(UTC))
        order = CanteenOrder(student_id=student.id, branch_id=student.branch_id, product_id=product.id,
            quantity=quantity, unit_price=product.price, total_price=total, payment_method=payment_method or "WALLET",
            order_date=now.date(), order_time=now.time(), processed_by=tenant.user_id, status="COMPLETED")
        db.add(order)
    await db.flush(); await db.refresh(row)
    return dict(serialize(student, row), id=str(transaction.id), transaction_id=str(transaction.id),
        order_id=str(order.id) if order else None, authorized=True, total_price=float(total), amount=float(total),
        student_balance=float(row.balance), item_name=name, message="Satış tamamlandı", blocked_reason=None)


async def transactions(db, tenant, student_id=None):
    query = select(CanteenWalletTransaction, Student).join(Student, Student.id == CanteenWalletTransaction.student_id)
    repo = BaseRepository(db, tenant)
    query = repo._branch_filter(repo._org_filter(query, Student), Student)
    if student_id:
        await wallet(db, tenant, student_id)
        query = query.where(Student.id == identifier(student_id))
    from app.core.student_access import accessible_student_ids
    ids = await accessible_student_ids(db, tenant)
    if ids is not None:
        query = query.where(Student.id.in_(ids))
    rows = (await db.execute(query.order_by(CanteenWalletTransaction.created_at.desc()))).all()
    return [{"id": str(row.id), "student_id": str(student.id), "student_name": f"{student.first_name} {student.last_name}",
        "amount": float(row.amount), "type": "TOPUP" if row.transaction_type == "CREDIT" else "PURCHASE",
        "transaction_type": row.transaction_type, "item_name": row.notes or row.payment_method,
        "date": row.created_at.isoformat(), "status": row.status} for row, student in rows]
