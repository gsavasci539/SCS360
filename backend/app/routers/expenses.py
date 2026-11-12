from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from datetime import UTC, datetime
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.permissions import PermissionChecker, require_permission
from app.core.responses import success_response, paginate
from app.domain.entities.user import User
from app.infrastructure.models.models import Expense
from app.infrastructure.repositories.base import BaseRepository
from app.core.tenant import TenantContext
from app.core.dependencies import get_tenant_context

router = APIRouter(prefix="/api/finance/expenses", tags=["Finance Expenses"])


class ExpenseCreate(BaseModel):
    request_id: UUID | None = None
    branch_id: UUID | None = None
    description: str = Field(min_length=1, max_length=500)
    category: str = Field(min_length=1, max_length=100)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2, allow_inf_nan=False)
    expense_date: Optional[datetime] = None
    notes: Optional[str] = None

    @field_validator("description", "category")
    @classmethod
    def nonblank_text(cls, value):
        if not value.strip():
            raise ValueError("Açıklama ve kategori boş olamaz")
        return value.strip()

    @model_validator(mode="after")
    def stable_retry_date(self):
        if self.request_id is not None and self.expense_date is None:
            raise ValueError("İşlem kimliği kullanıldığında gider tarihi gereklidir")
        return self

    @field_validator("expense_date", mode="before")
    @classmethod
    def empty_date(cls, value):
        return value or None


class ExpenseUpdate(BaseModel):
    description: Optional[str] = Field(default=None, min_length=1, max_length=500)
    category: Optional[str] = Field(default=None, min_length=1, max_length=100)
    amount: Optional[Decimal] = Field(default=None, gt=0, max_digits=12, decimal_places=2, allow_inf_nan=False)
    expense_date: Optional[datetime] = None
    status: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("description", "category", "amount", "expense_date", "status")
    @classmethod
    def nonnull_update(cls, value):
        if value is None or isinstance(value, str) and not value.strip():
            raise ValueError("Gider alanı boş olamaz")
        return value.strip() if isinstance(value, str) else value


def expense_to_dict(expense: Expense) -> dict:
    from app.application.services.expense_service import row
    return row(expense)


@router.post("")
@require_permission("finance.write")
async def create_expense(
    expense: ExpenseCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("finance.write")),
    current_user: User = Depends(get_current_user)
):
    from app.application.services import expense_service
    result = await expense_service.create(db, tenant, branch_id=expense.branch_id, title=expense.description,
        category=expense.category, amount=expense.amount, when=expense.expense_date or datetime.now(UTC),
        notes=expense.notes, request_id=expense.request_id)
    return success_response(result, "Gider oluşturuldu")


@router.get("")
@require_permission("finance.read")
async def list_expenses(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    search: Optional[str] = None,
    category: Optional[str] = None,
    branch_id: UUID | None = None,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("finance.read")),
    current_user: User = Depends(get_current_user)
):
    from app.application.services import expense_service
    repo = BaseRepository(db, tenant)
    query = await expense_service.query(db, tenant, branch_id, category, search)
    items, total = await repo.paginate(query, page, page_size)
    return success_response(paginate([expense_to_dict(e) for e in items], total, page, page_size))


@router.get("/{expense_id}")
@require_permission("finance.read")
async def get_expense(
    expense_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("finance.read")),
    current_user: User = Depends(get_current_user)
):
    repo = BaseRepository(db, tenant)
    expense = await repo.get_by_id(expense_id, Expense)
    
    
    return success_response(expense_to_dict(expense))


@router.put("/{expense_id}")
@require_permission("finance.write")
async def update_expense(
    expense_id: UUID,
    expense: ExpenseUpdate,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("finance.write")),
    current_user: User = Depends(get_current_user)
):
    repo = BaseRepository(db, tenant)
    db_expense = await repo.get_by_id(expense_id, Expense)
    
    
    for key, value in expense.model_dump(exclude_unset=True).items():
        setattr(db_expense, key, value)
    db_expense.updated_by = current_user.id
    
    await db.flush()
    return success_response(expense_to_dict(db_expense), "Gider güncellendi")


@router.delete("/{expense_id}")
@require_permission("finance.write")
async def delete_expense(
    expense_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("finance.write")),
    current_user: User = Depends(get_current_user)
):
    repo = BaseRepository(db, tenant)
    db_expense = await repo.get_by_id(expense_id, Expense)
    
    
    await repo.soft_delete(db_expense)
    return success_response(message="Gider silindi")
