from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.permissions import require_permission
from app.core.responses import success_response, paginate
from app.domain.entities.user import User
from app.infrastructure.models.models import Expense
from app.infrastructure.repositories.base import BaseRepository
from app.core.tenant import TenantContext
from app.core.dependencies import get_tenant_context

router = APIRouter(prefix="/api/finance/expenses", tags=["Finance Expenses"])


class ExpenseCreate(BaseModel):
    description: str
    category: str
    amount: float
    expense_date: Optional[datetime] = None
    notes: Optional[str] = None


class ExpenseUpdate(BaseModel):
    description: Optional[str] = None
    category: Optional[str] = None
    amount: Optional[float] = None
    expense_date: Optional[datetime] = None
    status: Optional[str] = None
    notes: Optional[str] = None


def expense_to_dict(expense: Expense) -> dict:
    return {
        "id": str(expense.id),
        "description": expense.description,
        "category": expense.category,
        "amount": float(expense.amount),
        "expense_date": expense.expense_date.isoformat() if expense.expense_date else None,
        "status": expense.status,
        "notes": expense.notes,
        "organization_id": str(expense.organization_id),
        "created_at": expense.created_at.isoformat() if expense.created_at else None,
    }


@router.post("")
@require_permission("finance.write")
async def create_expense(
    expense: ExpenseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = BaseRepository(db, TenantContext(organization_id=current_user.organization_id, is_super_admin=False))
    expense_data = expense.model_dump()
    expense_data["organization_id"] = current_user.organization_id
    expense_data["created_by"] = current_user.id
    expense_data["updated_by"] = current_user.id
    if not expense_data.get("expense_date"):
        expense_data["expense_date"] = datetime.utcnow()
    
    db_expense = Expense(**expense_data)
    db.add(db_expense)
    await db.flush()
    return success_response(expense_to_dict(db_expense), "Gider oluşturuldu")


@router.get("")
@require_permission("dashboard.view")
async def list_expenses(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    search: Optional[str] = None,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from sqlalchemy import select
    
    repo = BaseRepository(db, TenantContext(organization_id=current_user.organization_id, is_super_admin=False))
    query = select(Expense).where(Expense.organization_id == current_user.organization_id)
    
    if search:
        query = query.where(Expense.description.ilike(f"%{search}%"))
    if category:
        query = query.where(Expense.category == category)
    
    query = query.order_by(Expense.expense_date.desc())
    items, total = await repo.paginate(query, page, page_size)
    
    return success_response(paginate([expense_to_dict(e) for e in items], total, page, page_size))


@router.get("/{expense_id}")
@require_permission("dashboard.view")
async def get_expense(
    expense_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = BaseRepository(db, TenantContext(organization_id=current_user.organization_id, is_super_admin=False))
    expense = await repo.get_by_id(expense_id, Expense)
    
    if not expense or expense.organization_id != current_user.organization_id:
        return success_response(None, "Gider bulunamadı", success=False)
    
    return success_response(expense_to_dict(expense))


@router.put("/{expense_id}")
@require_permission("finance.write")
async def update_expense(
    expense_id: UUID,
    expense: ExpenseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = BaseRepository(db, TenantContext(organization_id=current_user.organization_id, is_super_admin=False))
    db_expense = await repo.get_by_id(expense_id, Expense)
    
    if not db_expense or db_expense.organization_id != current_user.organization_id:
        return success_response(None, "Gider bulunamadı", success=False)
    
    for key, value in expense.model_dump(exclude_unset=True).items():
        setattr(db_expense, key, value)
    db_expense.updated_by = current_user.id
    
    await db.flush()
    return success_response(expense_to_dict(db_expense), "Gider güncellendi")


@router.delete("/{expense_id}")
@require_permission("finance.write")
async def delete_expense(
    expense_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = BaseRepository(db, TenantContext(organization_id=current_user.organization_id, is_super_admin=False))
    db_expense = await repo.get_by_id(expense_id, Expense)
    
    if not db_expense or db_expense.organization_id != current_user.organization_id:
        return success_response(None, "Gider bulunamadı", success=False)
    
    await repo.soft_delete(db_expense)
    return success_response(message="Gider silindi")
