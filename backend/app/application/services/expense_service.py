"""One expense ledger and representation for the web and native API aliases."""
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ConflictException, ValidationException
from app.core.dates import school_datetime
from app.infrastructure.models.models import Branch, Expense
from app.infrastructure.repositories.base import BaseRepository


def row(expense):
    return {"id": str(expense.id), "organization_id": str(expense.organization_id),
        "branch_id": str(expense.branch_id) if expense.branch_id else None,
        "title": expense.description, "description": expense.description, "category": expense.category,
        "amount": str(expense.amount), "date": school_datetime(expense.expense_date).date().isoformat(),
        "expense_date": expense.expense_date.isoformat(), "status": expense.status, "notes": expense.notes,
        "created_by": str(expense.created_by) if expense.created_by else None,
        "created_at": expense.created_at.isoformat() if expense.created_at else None}


async def query(db, tenant, branch_id=None, category=None, search=None):
    repo = BaseRepository(db, tenant)
    result = repo._branch_filter(repo._org_filter(select(Expense), Expense), Expense).where(Expense.deleted_at.is_(None))
    if branch_id is not None:
        await repo.get_by_id(UUID(str(branch_id)), Branch)
        result = result.where(Expense.branch_id == branch_id)
    if category:
        result = result.where(Expense.category == category)
    if search:
        result = result.where(Expense.description.ilike(f"%{search}%"))
    return result.order_by(Expense.expense_date.desc(), Expense.id)


async def create(db, tenant, *, branch_id, title, category, amount, when, notes=None, request_id=None):
    repo = BaseRepository(db, tenant)
    branch = await repo.get_by_id(UUID(str(branch_id)), Branch) if branch_id else None
    organization = branch.organization_id if branch else tenant.organization_id
    if organization is None:
        raise ValidationException("Gider için kurum seçin")
    when = when.replace(tzinfo=UTC) if when.tzinfo is None else when.astimezone(UTC)
    amount = Decimal(amount)
    if request_id is not None:
        from app.application.services.platform_service import lock_organization
        await lock_organization(db, organization)
        table = Expense.__table__
        previous = (await db.execute(select(table).where(table.c.id == request_id))).mappings().one_or_none()
        if previous is not None:
            old_when = previous["expense_date"]
            old_when = old_when.replace(tzinfo=UTC) if old_when.tzinfo is None else old_when.astimezone(UTC)
            same = (previous["organization_id"] == organization and previous["branch_id"] == (branch.id if branch else None)
                and previous["created_by"] == tenant.user_id and previous["deleted_at"] is None
                and previous["description"] == title and previous["category"] == category and previous["amount"] == amount
                and previous["notes"] == notes and old_when == when)
            if not same:
                raise ConflictException("İstek kimliği başka bir giderde kullanılmış veya içerik değişmiş")
            existing = await repo.get_by_id(request_id, Expense)
            return {**row(existing), "replayed": True}
    expense = Expense(**({"id": request_id} if request_id is not None else {}), organization_id=organization,
        branch_id=branch.id if branch else None, description=title, category=category, amount=amount,
        expense_date=when, notes=notes, created_by=tenant.user_id, updated_by=tenant.user_id)
    db.add(expense)
    try:
        await db.flush()
    except IntegrityError:
        if request_id is not None:
            raise ConflictException("İstek kimliği başka bir giderde kullanılmış") from None
        raise
    return row(expense)
