"""Scoped persistence for the operational screens shared by web and mobile."""
from app.core.dates import school_today
from datetime import UTC, date, datetime, time
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select

from app.core.exceptions import ForbiddenException, NotFoundException, ValidationException
from app.core.student_access import uses_relationship_scope
from app.infrastructure.models.models import Branch, ClassRoom, Debt, DebtStatus, Expense, OperationalRecord, Payment, User
from app.infrastructure.repositories.base import BaseRepository


def identifier(value):
    try:
        return UUID(str(value))
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValidationException("Geçerli bir kayıt seçin") from exc


def scoped(db, tenant, model):
    repo = BaseRepository(db, tenant)
    return repo._branch_filter(repo._org_filter(select(model), model), model)


async def records(db, tenant, kind, status=None, day=None):
    query = scoped(db, tenant, OperationalRecord).where(OperationalRecord.kind == kind)
    if kind == "STAFF_LEAVE" and not tenant.has_permission("users.write"):
        query = query.where(OperationalRecord.staff_id == tenant.user_id)
    if status:
        query = query.where(OperationalRecord.status == status)
    rows = (await db.execute(query.order_by(OperationalRecord.created_at.desc()))).scalars()
    data = [dict(row.data, id=str(row.id), status=row.status) for row in rows]
    return [row for row in data if not day or row.get("day_of_week") == day]


async def duty(db, tenant, body):
    repo = BaseRepository(db, tenant)
    branch = await repo.get_by_id(identifier(body.branch_id), Branch)
    teacher = await repo.get_by_id(identifier(body.teacher_id), User)
    if teacher.organization_id != branch.organization_id:
        raise ForbiddenException("Öğretmen bu kuruma ait değil")
    try:
        if time.fromisoformat(body.start_time) >= time.fromisoformat(body.end_time):
            raise ValueError()
    except ValueError as exc:
        raise ValidationException("Nöbet başlangıç ve bitiş saatleri geçersiz") from exc
    values = body.model_dump()
    values["teacher_name"] = f"{teacher.first_name} {teacher.last_name}"
    record = OperationalRecord(organization_id=branch.organization_id, branch_id=branch.id,
        staff_id=teacher.id, created_by=tenant.user_id, kind="DUTY_ROSTER", data=values)
    db.add(record); await db.flush()
    return dict(record.data, id=str(record.id), status=record.status)


async def leave(db, tenant, body):
    user = await BaseRepository(db, tenant).get_by_id(identifier(body.staff_id), User)
    if user.id != tenant.user_id and not tenant.has_permission("users.write"):
        raise ForbiddenException("Yalnızca kendi izin talebinizi oluşturabilirsiniz")
    try:
        start, end = date.fromisoformat(body.start_date), date.fromisoformat(body.end_date)
        if end < start:
            raise ValueError()
    except ValueError as exc:
        raise ValidationException("İzin tarih aralığı geçersiz") from exc
    values = body.model_dump()
    values.update(staff_name=f"{user.first_name} {user.last_name}", days_count=(end-start).days+1, admin_comment=None)
    record = OperationalRecord(organization_id=user.organization_id, staff_id=user.id, created_by=tenant.user_id,
        kind="STAFF_LEAVE", status="PENDING", data=values)
    db.add(record); await db.flush()
    return dict(record.data, id=str(record.id), status=record.status)


async def review_leave(db, tenant, record_id, body):
    record = await BaseRepository(db, tenant).get_by_id(identifier(record_id), OperationalRecord)
    if record.kind != "STAFF_LEAVE":
        raise NotFoundException()
    if body.status not in {"APPROVED", "REJECTED"}:
        raise ValidationException("Geçersiz izin değerlendirmesi")
    record.status = body.status
    record.data = dict(record.data, admin_comment=body.admin_comment)
    return dict(record.data, id=str(record.id), status=record.status)


async def class_schedule(db, tenant, class_id, data=None):
    from app.application.services.homework_service import class_scope
    classroom = await BaseRepository(db, tenant).get_by_id(identifier(class_id), ClassRoom, for_update=data is not None)
    if uses_relationship_scope(tenant):
        allowed = (await db.execute(class_scope(tenant).where(ClassRoom.id == classroom.id))).scalar_one_or_none()
        if allowed is None:
            raise ForbiddenException("Bu sınıfın programına erişiminiz yok")
    record = (await db.execute(select(OperationalRecord).where(OperationalRecord.kind == "CLASS_SCHEDULE",
        OperationalRecord.class_id == classroom.id))).scalar_one_or_none()
    if data is not None:
        if len(data) > 7 or any(not isinstance(day, dict) or not isinstance(day.get("periods", []), list) for day in data):
            raise ValidationException("Ders programı gün ve ders listelerinden oluşmalı")
        if record is None:
            record = OperationalRecord(organization_id=classroom.organization_id, branch_id=classroom.branch_id,
                class_id=classroom.id, kind="CLASS_SCHEDULE", reference_key=str(classroom.id), created_by=tenant.user_id, data={})
            db.add(record)
        record.data = {"schedule": data}
        await db.flush()
    return record.data.get("schedule", []) if record else []


async def teacher_schedule(db, tenant, teacher_id):
    from app.infrastructure.models.models import ClassTeacher
    teacher = await BaseRepository(db, tenant).get_by_id(identifier(teacher_id), User)
    if uses_relationship_scope(tenant) and "teacher" in tenant.role_slugs and teacher.id != tenant.user_id:
        raise ForbiddenException()
    classes = (await db.execute(scoped(db, tenant, ClassRoom).where((ClassRoom.teacher_id == teacher.id) |
        ClassRoom.id.in_(select(ClassTeacher.class_id).where(ClassTeacher.user_id == teacher.id))))).scalars().all()
    result = []
    for classroom in classes:
        for day in await class_schedule(db, tenant, classroom.id):
            result.append(dict(day, class_id=str(classroom.id), class_name=classroom.name))
    return result


async def expenses(db, tenant, category=None):
    query = scoped(db, tenant, Expense).where(Expense.deleted_at.is_(None))
    if category:
        query = query.where(Expense.category == category)
    rows = (await db.execute(query.order_by(Expense.expense_date.desc()))).scalars()
    return [{"id": str(row.id), "title": row.description, "description": row.description, "category": row.category,
        "amount": str(row.amount), "date": row.expense_date.date().isoformat(), "status": row.status,
        "branch_id": str(row.branch_id) if row.branch_id else None} for row in rows]


async def create_expense(db, tenant, body):
    branch = await BaseRepository(db, tenant).get_by_id(identifier(body.branch_id), Branch) if body.branch_id else None
    org = branch.organization_id if branch else tenant.organization_id
    if not org:
        raise ValidationException("Gider için kurum veya şube seçin")
    try:
        amount, when = Decimal(body.amount), date.fromisoformat(body.date)
        if amount <= 0:
            raise ValueError()
    except (ValueError, ArithmeticError) as exc:
        raise ValidationException("Gider tutarı veya tarihi geçersiz") from exc
    record = Expense(organization_id=org, branch_id=branch.id if branch else None, description=body.title,
        amount=amount, category=body.category, expense_date=datetime.combine(when, time.min, tzinfo=UTC),
        notes=body.receipt_url, created_by=tenant.user_id)
    db.add(record); await db.flush()
    return {"id": str(record.id), "title": record.description, "amount": str(record.amount), "date": when.isoformat()}


async def finance_analytics(db, tenant):
    since = school_today().replace(day=1)
    until = since.replace(year=since.year + (since.month == 12), month=since.month % 12 + 1)
    debts = (await db.execute(scoped(db, tenant, Debt).where(Debt.deleted_at.is_(None), Debt.status != DebtStatus.CANCELLED)
        .with_only_columns(Debt.amount, Debt.paid_amount, Debt.due_date, Debt.debt_type,
            (Debt.amount - Debt.paid_amount).label("remaining_amount")))).all()
    payments = (await db.execute(scoped(db, tenant, Payment).where(Payment.cancelled_at.is_(None), Payment.payment_date >= since, Payment.payment_date < until)
        .with_only_columns(Payment.amount))).all()
    expenses = (await db.execute(scoped(db, tenant, Expense).where(Expense.deleted_at.is_(None), Expense.expense_date >= since, Expense.expense_date < until)
        .with_only_columns(Expense.amount, Expense.category))).all()
    accrued = sum((debt.amount for debt in debts if since <= debt.due_date < until), Decimal(0))
    collected = sum((row.amount for row in payments), Decimal(0))
    spent = sum((row.amount for row in expenses), Decimal(0))
    breakdown, expense_breakdown = {}, {}
    for row in debts:
        key = row.debt_type.value
        breakdown[key] = breakdown.get(key, 0) + float(row.amount)
    for row in expenses:
        expense_breakdown[row.category] = expense_breakdown.get(row.category, 0) + float(row.amount)
    return {"monthly_accrued": float(accrued), "monthly_collected": float(collected),
        "collection_rate_percent": round(float(collected / accrued * 100), 2) if accrued else 0,
        "total_remaining_receivable": float(sum((row.remaining_amount for row in debts), Decimal(0))),
        "monthly_expenses": float(spent), "net_operating_margin": float(collected-spent),
        "breakdown": breakdown, "expense_breakdown": expense_breakdown}
