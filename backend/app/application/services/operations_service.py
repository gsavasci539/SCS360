"""Scoped persistence for the operational screens shared by web and mobile."""
from app.core.dates import school_today
from datetime import UTC, date, datetime, time
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select

from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException, ValidationException
from app.core.student_access import uses_relationship_scope
from app.infrastructure.models.models import Branch, ClassRoom, Debt, DebtStatus, Expense, OperationalRecord, Payment, Role, User, UserStatus
from app.infrastructure.repositories.base import BaseRepository


def identifier(value):
    try:
        return UUID(str(value))
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValidationException("Geçerli bir kayıt seçin") from exc


def scoped(db, tenant, model):
    repo = BaseRepository(db, tenant)
    return repo._branch_filter(repo._org_filter(select(model), model), model)


async def records(db, tenant, kind, status=None, day=None, branch_id=None):
    query = scoped(db, tenant, OperationalRecord).where(OperationalRecord.kind == kind)
    if kind == "STAFF_LEAVE":
        if not tenant.has_permission("users.write"):
            query = query.where(OperationalRecord.staff_id == tenant.user_id)
        elif limits_leave_staff(tenant):
            query = query.where(OperationalRecord.staff_id.in_(leave_staff_query(tenant)))
    if status:
        query = query.where(OperationalRecord.status == status)
    if branch_id is not None:
        await BaseRepository(db, tenant).require_related(branch_id, Branch)
        query = query.where(OperationalRecord.branch_id == branch_id)
    rows = (await db.execute(query.order_by(OperationalRecord.created_at.desc()))).scalars()
    data = [dict(row.data, id=str(row.id), status=row.status) for row in rows]
    return [row for row in data if not day or row.get("day_of_week") == day]


def duty_teacher_query(branch):
    valid_branch = Branch.deleted_at.is_(None) & (Branch.organization_id == branch.organization_id)
    return select(User).where(
        User.organization_id == branch.organization_id,
        User.deleted_at.is_(None),
        User.is_super_admin.is_(False),
        User.status == UserStatus.ACTIVE,
        User.roles.any((Role.slug == "teacher") & Role.deleted_at.is_(None)
            & ((Role.organization_id == branch.organization_id) | Role.organization_id.is_(None))),
        ~User.branches.any(valid_branch) | User.branches.any(valid_branch & (Branch.id == branch.id)),
    )


async def duty_options(db, tenant, branch_id, page, page_size):
    from app.core.responses import paginate

    repo = BaseRepository(db, tenant)
    if branch_id is None:
        query = scoped(db, tenant, Branch).where(Branch.deleted_at.is_(None)).order_by(Branch.name, Branch.id)
        rows, total = await repo.paginate(query, page, page_size)
        items = [{"id": str(row.id), "name": row.name} for row in rows]
    else:
        branch = await repo.require_related(branch_id, Branch)
        query = duty_teacher_query(branch).order_by(User.first_name, User.last_name, User.id)
        rows, total = await repo.paginate(query, page, page_size)
        items = [{"id": str(row.id), "name": f"{row.first_name} {row.last_name}".strip()} for row in rows]
    return paginate(items, total, page, page_size)


async def duty(db, tenant, body):
    repo = BaseRepository(db, tenant)
    branch = await repo.require_related(identifier(body.branch_id), Branch)
    teacher_id = identifier(body.teacher_id)
    try:
        start, end = time.fromisoformat(body.start_time), time.fromisoformat(body.end_time)
        if start.tzinfo or end.tzinfo or start >= end:
            raise ValueError()
    except ValueError as exc:
        raise ValidationException("Nöbet başlangıç ve bitiş saatleri geçersiz") from exc
    values = body.model_dump(exclude={"request_id", "teacher_name"})
    values.update(branch_id=str(branch.id), teacher_id=str(teacher_id))
    if body.request_id is not None:
        existing = (await db.execute(scoped(db, tenant, OperationalRecord).where(
            OperationalRecord.id == body.request_id,
        ))).scalar_one_or_none()
        if existing is not None:
            if (existing.kind != "DUTY_ROSTER" or existing.created_by != tenant.user_id
                    or any(existing.data.get(key) != value for key, value in values.items())):
                raise ConflictException("Nöbet istek kimliği başka bir kayıtla çakışıyor")
            return dict(existing.data, id=str(existing.id), status=existing.status)
    teacher = (await db.execute(duty_teacher_query(branch).where(User.id == teacher_id))).scalar_one_or_none()
    if teacher is None:
        raise ValidationException("Seçilen öğretmen bu şubede nöbet için uygun değil")
    values["teacher_name"] = f"{teacher.first_name} {teacher.last_name}".strip()
    record = OperationalRecord(organization_id=branch.organization_id, branch_id=branch.id,
        staff_id=teacher.id, created_by=tenant.user_id, kind="DUTY_ROSTER", data=values)
    if body.request_id is not None:
        record.id = body.request_id
    db.add(record); await db.flush()
    return dict(record.data, id=str(record.id), status=record.status)


async def leave(db, tenant, body):
    user = await BaseRepository(db, tenant).get_by_id(identifier(body.staff_id), User)
    if user.id != tenant.user_id and not tenant.has_permission("users.write"):
        raise ForbiddenException("Yalnızca kendi izin talebinizi oluşturabilirsiniz")
    if user.id != tenant.user_id:
        await require_leave_staff_scope(db, tenant, user.id)
    try:
        start, end = date.fromisoformat(body.start_date), date.fromisoformat(body.end_date)
        if end < start:
            raise ValueError()
    except ValueError as exc:
        raise ValidationException("İzin tarih aralığı geçersiz") from exc
    values = body.model_dump(exclude={"request_id", "staff_name", "days_count"})
    values.update(staff_id=str(user.id), days_count=(end - start).days + 1)
    if body.request_id is not None:
        existing = (await db.execute(scoped(db, tenant, OperationalRecord).where(
            OperationalRecord.id == body.request_id,
        ))).scalar_one_or_none()
        if existing is not None:
            if (existing.kind != "STAFF_LEAVE" or existing.created_by != tenant.user_id
                    or any(existing.data.get(key) != value for key, value in values.items())):
                raise ConflictException("İzin talebi kimliği başka bir kayıtla çakışıyor")
            return dict(existing.data, id=str(existing.id), status=existing.status)
    values.update(staff_name=f"{user.first_name} {user.last_name}", admin_comment=None)
    record = OperationalRecord(organization_id=user.organization_id, staff_id=user.id, created_by=tenant.user_id,
        kind="STAFF_LEAVE", status="PENDING", data=values)
    if body.request_id is not None:
        record.id = body.request_id
    db.add(record); await db.flush()
    return dict(record.data, id=str(record.id), status=record.status)


async def review_leave(db, tenant, record_id, body):
    record = await BaseRepository(db, tenant).get_by_id(identifier(record_id), OperationalRecord)
    if record.kind != "STAFF_LEAVE":
        raise NotFoundException()
    await require_leave_staff_scope(db, tenant, record.staff_id)
    if body.status not in {"APPROVED", "REJECTED"}:
        raise ValidationException("Geçersiz izin değerlendirmesi")
    record.status = body.status
    record.data = dict(record.data, admin_comment=body.admin_comment)
    return dict(record.data, id=str(record.id), status=record.status)


def limits_leave_staff(tenant):
    return bool(tenant.branch_ids and not tenant.is_super_admin and not tenant.is_organization_owner)


def leave_staff_query(tenant):
    valid_branch = Branch.deleted_at.is_(None) & (Branch.organization_id == tenant.organization_id)
    return select(User.id).where(
        User.organization_id == tenant.organization_id,
        User.deleted_at.is_(None),
        ~User.branches.any(valid_branch) | User.branches.any(valid_branch & Branch.id.in_(tenant.branch_ids)),
    )


async def require_leave_staff_scope(db, tenant, staff_id):
    if limits_leave_staff(tenant):
        staff = await db.scalar(leave_staff_query(tenant).where(User.id == staff_id))
        if staff is None:
            raise NotFoundException("İzin talebi bulunamadı")


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


async def expenses(db, tenant, category=None, branch_id=None, page=None, page_size=100):
    from app.application.services import expense_service
    from app.core.responses import paginate
    query = await expense_service.query(db, tenant, branch_id, category)
    if page is not None:
        rows, total = await BaseRepository(db, tenant).paginate(query, page, page_size)
        return paginate([expense_service.row(row) for row in rows], total, page, page_size)
    return [expense_service.row(row) for row in (await db.execute(query)).scalars()]


async def create_expense(db, tenant, body):
    from app.application.services import expense_service
    from app.core.dates import school_day_bounds
    return await expense_service.create(db, tenant, branch_id=body.branch_id, title=body.title, category=body.category,
        amount=body.amount, when=school_day_bounds(date.fromisoformat(body.date))[0],
        notes=body.receipt_url, request_id=body.request_id)


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
