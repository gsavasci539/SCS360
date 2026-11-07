from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_tenant_context
from app.core.permissions import require_permission, PermissionChecker
from app.core.responses import success_response, paginate
from app.domain.entities.user import User
from app.core.tenant import TenantContext
from app.infrastructure.models.models import Debt, Student, Parent, StudentParent, ClassRoom
from sqlalchemy import and_, func

router = APIRouter(prefix="/api/debts", tags=["Debts"])


class DebtCreate(BaseModel):
    student_id: UUID
    debt_type: str
    amount: float
    due_date: datetime
    description: Optional[str] = None
    academic_year: Optional[str] = None


class DebtUpdate(BaseModel):
    debt_type: Optional[str] = None
    amount: Optional[float] = None
    due_date: Optional[datetime] = None
    description: Optional[str] = None
    status: Optional[str] = None


@router.get("")
@require_permission("finance.read")
async def list_debts(
    page: int = 1,
    page_size: int = 20,
    student_id: Optional[UUID] = None,
    status: Optional[str] = None,
    debt_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("finance.read"))
):
    query = select(Debt).where(Debt.organization_id == tenant.organization_id)
    if student_id:
        query = query.where(Debt.student_id == student_id)
    if status:
        query = query.where(Debt.status == status)
    if debt_type:
        query = query.where(Debt.debt_type == debt_type)
    query = query.order_by(Debt.due_date.desc())
    
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    debts = result.scalars().all()
    
    if not debts:
        return success_response(paginate([], total, page, page_size))
    
    student_ids = set(debt.student_id for debt in debts if debt.student_id)
    print(f"DEBUG: Found {len(student_ids)} unique student IDs")
    print(f"DEBUG: Student IDs: {student_ids}")
    
    students_result = await db.execute(
        select(Student).where(
            and_(
                Student.id.in_(list(student_ids)),
                Student.deleted_at.is_(None)
            )
        )
    )
    students = {str(s.id): s for s in students_result.scalars().all()}
    print(f"DEBUG: Loaded {len(students)} students from database")
    
    class_ids = set(s.class_id for s in students.values() if s.class_id)
    classes_result = await db.execute(
        select(ClassRoom).where(ClassRoom.id.in_(list(class_ids)))
    )
    classes = {str(c.id): c for c in classes_result.scalars().all()}
    
    student_parents_result = await db.execute(
        select(StudentParent).where(StudentParent.student_id.in_(list(student_ids)))
    )
    student_parents = student_parents_result.scalars().all()
    parent_ids = set(sp.parent_id for sp in student_parents)
    
    parents_result = await db.execute(
        select(Parent).where(Parent.id.in_(list(parent_ids)))
    )
    parents = {str(p.id): p for p in parents_result.scalars().all()}
    
    student_to_parent = {}
    for sp in student_parents:
        if sp.student_id not in student_to_parent or sp.is_primary:
            student_to_parent[str(sp.student_id)] = str(sp.parent_id)
    
    result = []
    for debt in debts:
        debt_dict = {
            "id": str(debt.id),
            "student_id": str(debt.student_id),
            "debt_type": debt.debt_type,
            "amount": float(debt.amount),
            "remaining_amount": float(debt.remaining_amount),
            "due_date": debt.due_date.isoformat() if debt.due_date else None,
            "status": debt.status,
            "description": debt.description,
        }
        
        student = students.get(str(debt.student_id))
        if student:
            debt_dict['student_name'] = f"{student.first_name} {student.last_name}"
            debt_dict['student_class'] = str(student.class_id) if student.class_id else None
            if student.class_id:
                class_room = classes.get(str(student.class_id))
                debt_dict['class_name'] = class_room.name if class_room else None
        
        parent_id = student_to_parent.get(str(debt.student_id))
        if parent_id:
            parent = parents.get(parent_id)
            if parent:
                debt_dict['parent_name'] = f"{parent.first_name} {parent.last_name}"
                debt_dict['parent_phone'] = parent.phone
        
        result.append(debt_dict)
    
    return success_response(paginate(result, total, page, page_size))


@router.get("/{debt_id}")
@require_permission("finance.read")
async def get_debt(
    debt_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("finance.read"))
):
    query = select(Debt).where(Debt.id == debt_id, Debt.organization_id == tenant.organization_id)
    result = await db.execute(query)
    debt = result.scalar_one_or_none()
    
    if not debt:
        return success_response(None, "Borç bulunamadı", success=False)
    
    return success_response({"id": str(debt.id), "amount": float(debt.amount), "status": debt.status})


@router.post("")
@require_permission("finance.write")
async def create_debt(
    debt: DebtCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("finance.write")),
    current_user: User = Depends(get_current_user)
):
    debt_data = debt.model_dump()
    debt_data["created_by"] = current_user.id
    debt_data["organization_id"] = current_user.organization_id
    debt_data["remaining_amount"] = debt_data["amount"]
    debt_data["paid_amount"] = 0
    debt_data["status"] = "UNPAID"
    
    db_debt = Debt(**debt_data)
    db.add(db_debt)
    await db.flush()
    
    return success_response({"id": str(db_debt.id)}, "Borç oluşturuldu")


@router.put("/{debt_id}")
@require_permission("finance.write")
async def update_debt(
    debt_id: UUID,
    debt: DebtUpdate,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("finance.write"))
):
    query = select(Debt).where(Debt.id == debt_id, Debt.organization_id == tenant.organization_id)
    result = await db.execute(query)
    db_debt = result.scalar_one_or_none()
    
    if not db_debt:
        return success_response(None, "Borç bulunamadı", success=False)
    
    for key, value in debt.model_dump(exclude_unset=True).items():
        setattr(db_debt, key, value)
    
    await db.flush()
    return success_response({"id": str(db_debt.id)}, "Borç güncellendi")


@router.delete("/{debt_id}")
@require_permission("finance.write")
async def delete_debt(
    debt_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("finance.write"))
):
    query = select(Debt).where(Debt.id == debt_id, Debt.organization_id == tenant.organization_id)
    result = await db.execute(query)
    db_debt = result.scalar_one_or_none()
    
    if not db_debt:
        return success_response(None, "Borç bulunamadı", success=False)
    
    db_debt.deleted_at = datetime.utcnow()
    await db.flush()
    return success_response(message="Borç silindi")
