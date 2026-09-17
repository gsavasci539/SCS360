from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from app.application.schemas import DebtCreate, DebtUpdate, DebtResponse
from app.repositories import DebtRepository
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.permissions import require_permission
from app.core.responses import success_response
from app.domain.entities.user import User

router = APIRouter(prefix="/api/debts", tags=["Debts"])


@router.post("", response_model=DebtResponse)
@require_permission("debts.create")
async def create_debt(
    debt: DebtCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = DebtRepository()
    debt_data = debt.model_dump()
    debt_data["created_by"] = current_user.id
    debt_data["organization_id"] = current_user.organization_id
    debt_data["remaining_amount"] = debt_data["amount"]
    debt_data["paid_amount"] = 0
    
    db_debt = await repo.create(db, debt_data)
    return success_response(db_debt, "Borç oluşturuldu")


@router.get("", response_model=list[DebtResponse])
@require_permission("debts.view")
async def list_debts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    student_id: Optional[UUID] = None,
    status: Optional[str] = None,
    debt_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = DebtRepository()
    
    filters = {"organization_id": current_user.organization_id}
    if student_id:
        filters["student_id"] = student_id
    if status:
        filters["status"] = status
    if debt_type:
        filters["debt_type"] = debt_type
    
    debts = await repo.get_multi(db, skip, limit, filters)
    return success_response(debts)


@router.get("/overdue", response_model=list[DebtResponse])
@require_permission("debts.view")
async def list_overdue_debts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = DebtRepository()
    debts = await repo.get_overdue_debts(db, current_user.organization_id, skip, limit)
    return success_response(debts)


@router.get("/{debt_id}", response_model=DebtResponse)
@require_permission("debts.view")
async def get_debt(
    debt_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = DebtRepository()
    debt = await repo.get(db, debt_id)
    
    if not debt or debt.organization_id != current_user.organization_id:
        return success_response(None, "Borç bulunamadı", success=False)
    
    return success_response(debt)


@router.put("/{debt_id}", response_model=DebtResponse)
@require_permission("debts.update")
async def update_debt(
    debt_id: UUID,
    debt: DebtUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = DebtRepository()
    db_debt = await repo.get(db, debt_id)
    
    if not db_debt or db_debt.organization_id != current_user.organization_id:
        return success_response(None, "Borç bulunamadı", success=False)
    
    debt_data = debt.model_dump(exclude_unset=True)
    debt_data["updated_by"] = current_user.id
    
    updated_debt = await repo.update(db, db_debt, debt_data)
    return success_response(updated_debt, "Borç güncellendi")


@router.delete("/{debt_id}")
@require_permission("debts.delete")
async def delete_debt(
    debt_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = DebtRepository()
    db_debt = await repo.get(db, debt_id)
    
    if not db_debt or db_debt.organization_id != current_user.organization_id:
        return success_response(None, "Borç bulunamadı", success=False)
    
    await repo.soft_delete(db, debt_id)
    return success_response(message="Borç silindi")
