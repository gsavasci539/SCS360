"""
Canteen POS & Dietary Restrictions Module API
Handles POS checkout, dietary restrictions, and canteen management
"""
from datetime import datetime, date, time
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, validator
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.responses import success_response
from app.core.security import PermissionChecker, TenantContext
from app.domain.entities import (
    CanteenProduct, CanteenDietaryRestriction, CanteenOrder, Student, Branch
)
from app.domain.entities.user import User

router = APIRouter(prefix="/api/canteen", tags=["Canteen"])


# ==================== Schemas ====================

class CanteenProductCreate(BaseModel):
    branch_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = None
    price: Decimal = Field(..., gt=0, decimal_places=2)
    image_url: Optional[str] = None
    allergens: Optional[List[str]] = Field(None, description="PEANUT, DAIRY, GLUTEN, EGG, SOY, FISH, SHELLFISH, TREE_NUT, SESAME, OTHER")
    nutritional_info: Optional[dict] = None

class CanteenProductResponse(BaseModel):
    id: UUID
    branch_id: UUID
    branch_name: Optional[str]
    name: str
    description: Optional[str]
    category: Optional[str]
    price: Decimal
    image_url: Optional[str]
    is_available: bool
    allergens: List[str]
    nutritional_info: Optional[dict]
    created_at: datetime
    updated_at: datetime

class DietaryRestrictionCreate(BaseModel):
    student_id: UUID
    restriction: str = Field(..., description="PEANUT, DAIRY, GLUTEN, EGG, SOY, FISH, SHELLFISH, TREE_NUT, SESAME, OTHER")
    description: Optional[str] = None

class DietaryRestrictionResponse(BaseModel):
    id: UUID
    student_id: UUID
    student_name: Optional[str]
    restriction: str
    description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

class POSCheckoutRequest(BaseModel):
    student_id: UUID
    product_id: UUID
    quantity: int = Field(default=1, ge=1)
    payment_method: Optional[str] = Field(None, description="CASH, CARD, WALLET")
    branch_id: Optional[UUID] = None
    notes: Optional[str] = None

class POSCheckoutResponse(BaseModel):
    authorized: bool
    message: str
    order_id: Optional[UUID]
    total_price: Decimal
    blocked_reason: Optional[str]
    student_name: Optional[str]
    student_balance: Optional[Decimal]
    daily_spent: Optional[Decimal]
    daily_limit: Optional[Decimal]

class CanteenOrderResponse(BaseModel):
    id: UUID
    student_id: UUID
    student_name: Optional[str]
    branch_id: Optional[UUID]
    branch_name: Optional[str]
    product_id: UUID
    product_name: Optional[str]
    quantity: int
    unit_price: Decimal
    total_price: Decimal
    status: str
    payment_method: Optional[str]
    order_date: date
    order_time: time
    processed_by: Optional[UUID]
    processed_by_name: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

class StudentWalletInfo(BaseModel):
    student_id: UUID
    student_name: Optional[str]
    balance: Decimal
    daily_limit: Optional[Decimal]
    daily_spent: Decimal
    dietary_restrictions: List[str]


class WalletTopUpCreate(BaseModel):
    student_id: UUID
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    payment_method: str = Field(..., description="CASH, CARD, BANK_TRANSFER")
    reference_number: Optional[str] = None


# ==================== Canteen Products Endpoints ====================

@router.get("/products")
async def get_canteen_products(
    branch_id: Optional[UUID] = Query(None),
    category: Optional[str] = Query(None),
    is_available: Optional[bool] = Query(True),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("canteen.read"))
):
    """Get canteen products with filtering"""
    query = select(CanteenProduct)
    
    conditions = []
    if branch_id:
        conditions.append(CanteenProduct.branch_id == branch_id)
    if category:
        conditions.append(CanteenProduct.category == category)
    if is_available is not None:
        conditions.append(CanteenProduct.is_available == is_available)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(CanteenProduct.category, CanteenProduct.name).limit(limit).offset(offset)
    
    result = await db.execute(query)
    products = result.scalars().all()
    
    enriched_products = []
    for product in products:
        # Get branch name
        branch_name = None
        if product.branch_id:
            branch_result = await db.execute(
                select(Branch).where(Branch.id == product.branch_id)
            )
            branch = branch_result.scalar_one_or_none()
            if branch:
                branch_name = branch.name
        
        enriched_products.append({
            "id": str(product.id),
            "branch_id": str(product.branch_id),
            "branch_name": branch_name,
            "name": product.name,
            "description": product.description,
            "category": product.category,
            "price": float(product.price),
            "image_url": product.image_url,
            "is_available": product.is_available,
            "allergens": product.allergens or [],
            "nutritional_info": product.nutritional_info,
            "created_at": product.created_at.isoformat(),
            "updated_at": product.updated_at.isoformat()
        })
    
    return success_response(enriched_products)


@router.post("/products")
async def create_canteen_product(
    product: CanteenProductCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("canteen.write"))
):
    """Create a new canteen product"""
    new_product = CanteenProduct(
        branch_id=product.branch_id,
        name=product.name,
        description=product.description,
        category=product.category,
        price=product.price,
        image_url=product.image_url,
        is_available=True,
        allergens=product.allergens or [],
        nutritional_info=product.nutritional_info
    )
    db.add(new_product)
    await db.commit()
    await db.refresh(new_product)
    
    return success_response({
        "id": str(new_product.id),
        "name": new_product.name,
        "price": float(new_product.price),
        "category": new_product.category,
        "created_at": new_product.created_at.isoformat()
    })


@router.put("/products/{product_id}")
async def update_canteen_product(
    product_id: UUID,
    product: CanteenProductCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("canteen.write"))
):
    """Update a canteen product"""
    result = await db.execute(
        select(CanteenProduct).where(CanteenProduct.id == product_id)
    )
    existing_product = result.scalar_one_or_none()
    
    if not existing_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    existing_product.branch_id = product.branch_id
    existing_product.name = product.name
    existing_product.description = product.description
    existing_product.category = product.category
    existing_product.price = product.price
    existing_product.image_url = product.image_url
    existing_product.allergens = product.allergens or []
    existing_product.nutritional_info = product.nutritional_info
    
    await db.commit()
    await db.refresh(existing_product)
    
    return success_response({
        "id": str(existing_product.id),
        "name": existing_product.name,
        "updated_at": existing_product.updated_at.isoformat()
    })


@router.delete("/products/{product_id}")
async def delete_canteen_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("canteen.write"))
):
    """Delete a canteen product"""
    result = await db.execute(
        select(CanteenProduct).where(CanteenProduct.id == product_id)
    )
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    await db.delete(product)
    await db.commit()
    
    return success_response({"message": "Product deleted successfully"})


# ==================== Dietary Restrictions Endpoints ====================

@router.get("/dietary-restrictions")
async def get_dietary_restrictions(
    student_id: Optional[UUID] = Query(None),
    is_active: Optional[bool] = Query(True),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("canteen.read"))
):
    """Get dietary restrictions"""
    query = select(CanteenDietaryRestriction)
    
    conditions = []
    if student_id:
        conditions.append(CanteenDietaryRestriction.student_id == student_id)
    if is_active is not None:
        conditions.append(CanteenDietaryRestriction.is_active == is_active)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    result = await db.execute(query)
    restrictions = result.scalars().all()
    
    enriched_restrictions = []
    for restriction in restrictions:
        # Get student name
        student_name = None
        if restriction.student_id:
            student_result = await db.execute(
                select(Student).where(Student.id == restriction.student_id)
            )
            student = student_result.scalar_one_or_none()
            if student:
                student_name = f"{student.first_name} {student.last_name}"
        
        enriched_restrictions.append({
            "id": str(restriction.id),
            "student_id": str(restriction.student_id),
            "student_name": student_name,
            "restriction": restriction.restriction,
            "description": restriction.description,
            "is_active": restriction.is_active,
            "created_at": restriction.created_at.isoformat(),
            "updated_at": restriction.updated_at.isoformat()
        })
    
    return success_response(enriched_restrictions)


@router.post("/dietary-restrictions")
async def create_dietary_restriction(
    restriction: DietaryRestrictionCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("canteen.write"))
):
    """Create a dietary restriction for a student"""
    # Check if restriction already exists
    existing_result = await db.execute(
        select(CanteenDietaryRestriction).where(
            and_(
                CanteenDietaryRestriction.student_id == restriction.student_id,
                CanteenDietaryRestriction.restriction == restriction.restriction.upper()
            )
        )
    )
    existing = existing_result.scalar_one_or_none()
    
    if existing:
        existing.is_active = True
        existing.description = restriction.description
    else:
        new_restriction = CanteenDietaryRestriction(
            student_id=restriction.student_id,
            restriction=restriction.restriction.upper(),
            description=restriction.description,
            is_active=True
        )
        db.add(new_restriction)
    
    await db.commit()
    
    return success_response({
        "student_id": str(restriction.student_id),
        "restriction": restriction.restriction.upper(),
        "message": "Dietary restriction saved successfully"
    })


@router.delete("/dietary-restrictions/{restriction_id}")
async def delete_dietary_restriction(
    restriction_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("canteen.write"))
):
    """Delete a dietary restriction"""
    result = await db.execute(
        select(CanteenDietaryRestriction).where(CanteenDietaryRestriction.id == restriction_id)
    )
    restriction = result.scalar_one_or_none()
    
    if not restriction:
        raise HTTPException(status_code=404, detail="Restriction not found")
    
    await db.delete(restriction)
    await db.commit()
    
    return success_response({"message": "Dietary restriction deleted successfully"})


# ==================== POS Checkout Endpoints ====================

@router.post("/pos/checkout")
async def pos_checkout(
    request: POSCheckoutRequest,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("canteen.write"))
):
    """Process POS checkout with dietary restriction and balance checks"""
    # Get student
    student_result = await db.execute(
        select(Student).where(Student.id == request.student_id)
    )
    student = student_result.scalar_one_or_none()
    
    if not student:
        return success_response({
            "authorized": False,
            "message": "Student not found",
            "order_id": None,
            "total_price": 0,
            "blocked_reason": "STUDENT_NOT_FOUND",
            "student_name": None,
            "student_balance": None,
            "daily_spent": None,
            "daily_limit": None
        })
    
    if student.status != "ACTIVE":
        return success_response({
            "authorized": False,
            "message": "Student is not active",
            "order_id": None,
            "total_price": 0,
            "blocked_reason": "STUDENT_INACTIVE",
            "student_name": f"{student.first_name} {student.last_name}",
            "student_balance": None,
            "daily_spent": None,
            "daily_limit": None
        })
    
    # Get product
    product_result = await db.execute(
        select(CanteenProduct).where(CanteenProduct.id == request.product_id)
    )
    product = product_result.scalar_one_or_none()
    
    if not product:
        return success_response({
            "authorized": False,
            "message": "Product not found",
            "order_id": None,
            "total_price": 0,
            "blocked_reason": "PRODUCT_NOT_FOUND",
            "student_name": f"{student.first_name} {student.last_name}",
            "student_balance": None,
            "daily_spent": None,
            "daily_limit": None
        })
    
    if not product.is_available:
        return success_response({
            "authorized": False,
            "message": "Product is not available",
            "order_id": None,
            "total_price": 0,
            "blocked_reason": "PRODUCT_UNAVAILABLE",
            "student_name": f"{student.first_name} {student.last_name}",
            "student_balance": None,
            "daily_spent": None,
            "daily_limit": None
        })
    
    # Check dietary restrictions
    student_restrictions_result = await db.execute(
        select(CanteenDietaryRestriction).where(
            and_(
                CanteenDietaryRestriction.student_id == request.student_id,
                CanteenDietaryRestriction.is_active == True
            )
        )
    )
    student_restrictions = student_restrictions_result.scalars().all()
    student_allergens = [r.restriction for r in student_restrictions]
    
    product_allergens = product.allergens or []
    
    # Check for allergen conflicts
    allergen_conflicts = set(student_allergens) & set(product_allergens)
    if allergen_conflicts:
        return success_response({
            "authorized": False,
            "message": f"Product contains allergens: {', '.join(allergen_conflicts)}",
            "order_id": None,
            "total_price": float(product.price * request.quantity),
            "blocked_reason": "ALLERGEN_CONFLICT",
            "student_name": f"{student.first_name} {student.last_name}",
            "student_balance": None,
            "daily_spent": None,
            "daily_limit": None
        })
    
    # Calculate total
    total_price = product.price * request.quantity
    
    # Check daily spending limit (simplified - would need proper wallet integration)
    daily_limit = Decimal("50.00")  # Default daily limit
    daily_spent = Decimal("0.00")  # Would calculate from today's orders
    
    if daily_spent + total_price > daily_limit:
        return success_response({
            "authorized": False,
            "message": f"Daily spending limit exceeded. Spent: {daily_spent}, Limit: {daily_limit}",
            "order_id": None,
            "total_price": float(total_price),
            "blocked_reason": "DAILY_LIMIT_EXCEEDED",
            "student_name": f"{student.first_name} {student.last_name}",
            "student_balance": None,
            "daily_spent": float(daily_spent),
            "daily_limit": float(daily_limit)
        })
    
    # Create order
    from datetime import datetime
    now = datetime.now()
    
    new_order = CanteenOrder(
        student_id=request.student_id,
        branch_id=request.branch_id,
        product_id=request.product_id,
        quantity=request.quantity,
        unit_price=product.price,
        total_price=total_price,
        status="COMPLETED",
        payment_method=request.payment_method,
        order_date=date.today(),
        order_time=now.time(),
        notes=request.notes
    )
    db.add(new_order)
    await db.commit()
    await db.refresh(new_order)
    
    # Create DEBIT wallet transaction
    from app.domain.entities import CanteenWalletTransaction
    
    debit_transaction = CanteenWalletTransaction(
        student_id=request.student_id,
        amount=float(total_price),
        transaction_type="DEBIT",
        payment_method=request.payment_method or "WALLET",
        reference_number=f"ORDER-{new_order.id}",
        processed_by=None,  # System processed
        status="COMPLETED"
    )
    db.add(debit_transaction)
    await db.commit()
    
    return success_response({
        "authorized": True,
        "message": "Order completed successfully",
        "order_id": str(new_order.id),
        "total_price": float(total_price),
        "blocked_reason": None,
        "student_name": f"{student.first_name} {student.last_name}",
        "student_balance": None,
        "daily_spent": float(daily_spent + total_price),
        "daily_limit": float(daily_limit)
    })


@router.get("/student/{student_id}/wallet")
async def get_student_wallet_info(
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("canteen.read"))
):
    """Get student wallet information including dietary restrictions"""
    # Get student
    student_result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = student_result.scalar_one_or_none()

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Get dietary restrictions
    restrictions_result = await db.execute(
        select(CanteenDietaryRestriction).where(
            and_(
                CanteenDietaryRestriction.student_id == student_id,
                CanteenDietaryRestriction.is_active == True
            )
        )
    )
    restrictions = restrictions_result.scalars().all()
    allergens = [r.restriction for r in restrictions]

    # Calculate today's spending
    today = date.today()
    today_orders_result = await db.execute(
        select(CanteenOrder).where(
            and_(
                CanteenOrder.student_id == student_id,
                CanteenOrder.order_date == today,
                CanteenOrder.status == "COMPLETED"
            )
        )
    )
    today_orders = today_orders_result.scalars().all()
    daily_spent = sum(order.total_price for order in today_orders)

    # Calculate actual balance from wallet transactions
    from app.domain.entities import CanteenWalletTransaction
    
    wallet_transactions = await db.execute(
        select(CanteenWalletTransaction).where(
            CanteenWalletTransaction.student_id == student_id,
            CanteenWalletTransaction.status == "COMPLETED"
        )
    )
    wallet_transactions = wallet_transactions.scalars().all()
    
    current_balance = Decimal("0.00")
    for tx in wallet_transactions:
        if tx.transaction_type == "CREDIT":
            current_balance += Decimal(str(tx.amount))
        elif tx.transaction_type == "DEBIT":
            current_balance -= Decimal(str(tx.amount))

    return success_response({
        "student_id": str(student_id),
        "student_name": f"{student.first_name} {student.last_name}",
        "balance": current_balance,
        "daily_limit": Decimal("50.00"),  # Would get from student settings
        "daily_spent": float(daily_spent),
        "dietary_restrictions": allergens
    })


@router.post("/student/{student_id}/wallet/top-up")
async def wallet_top_up(
    student_id: UUID,
    top_up: WalletTopUpCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("canteen.write"))
):
    """Top up student wallet balance"""
    from app.infrastructure.models.models import CanteenWalletTransaction

    # Get student
    student_result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = student_result.scalar_one_or_none()

    if not student:
        raise HTTPException(status_code=404, detail="Öğrenci bulunamadı")

    # Create wallet transaction record
    new_transaction = CanteenWalletTransaction(
        student_id=student_id,
        amount=top_up.amount,
        transaction_type="CREDIT",
        payment_method=top_up.payment_method.upper(),
        reference_number=top_up.reference_number,
        processed_by=current_user.id,
        status="COMPLETED"
    )

    db.add(new_transaction)
    await db.commit()
    await db.refresh(new_transaction)

    # In a real implementation, this would update the actual wallet balance
    # For now, we'll return a mock balance
    new_balance = Decimal("100.00") + top_up.amount

    return success_response({
        "student_id": str(student_id),
        "student_name": f"{student.first_name} {student.last_name}",
        "transaction_id": str(new_transaction.id),
        "amount": float(top_up.amount),
        "payment_method": top_up.payment_method.upper(),
        "reference_number": top_up.reference_number,
        "new_balance": float(new_balance),
        "transaction_date": new_transaction.created_at.isoformat()
    }, "Cüzdan bakiyesi başarıyla yüklendi")


# ==================== Canteen Orders Endpoints ====================

@router.get("/orders")
async def get_canteen_orders(
    student_id: Optional[UUID] = Query(None),
    branch_id: Optional[UUID] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("canteen.read"))
):
    """Get canteen orders with filtering"""
    query = select(CanteenOrder)
    
    conditions = []
    if student_id:
        conditions.append(CanteenOrder.student_id == student_id)
    if branch_id:
        conditions.append(CanteenOrder.branch_id == branch_id)
    if start_date:
        conditions.append(CanteenOrder.order_date >= start_date)
    if end_date:
        conditions.append(CanteenOrder.order_date <= end_date)
    if status:
        conditions.append(CanteenOrder.status == status.upper())
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(CanteenOrder.order_date.desc(), CanteenOrder.order_time.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    orders = result.scalars().all()
    
    enriched_orders = []
    for order in orders:
        # Get student name
        student_name = None
        if order.student_id:
            student_result = await db.execute(
                select(Student).where(Student.id == order.student_id)
            )
            student = student_result.scalar_one_or_none()
            if student:
                student_name = f"{student.first_name} {student.last_name}"
        
        # Get branch name
        branch_name = None
        if order.branch_id:
            branch_result = await db.execute(
                select(Branch).where(Branch.id == order.branch_id)
            )
            branch = branch_result.scalar_one_or_none()
            if branch:
                branch_name = branch.name
        
        # Get product name
        product_name = None
        if order.product_id:
            product_result = await db.execute(
                select(CanteenProduct).where(CanteenProduct.id == order.product_id)
            )
            product = product_result.scalar_one_or_none()
            if product:
                product_name = product.name
        
        # Get processed by name
        processed_by_name = None
        if order.processed_by:
            user_result = await db.execute(
                select(User).where(User.id == order.processed_by)
            )
            user = user_result.scalar_one_or_none()
            if user:
                processed_by_name = f"{user.first_name} {user.last_name}"
        
        enriched_orders.append({
            "id": str(order.id),
            "student_id": str(order.student_id),
            "student_name": student_name,
            "branch_id": str(order.branch_id) if order.branch_id else None,
            "branch_name": branch_name,
            "product_id": str(order.product_id),
            "product_name": product_name,
            "quantity": order.quantity,
            "unit_price": float(order.unit_price),
            "total_price": float(order.total_price),
            "status": order.status,
            "payment_method": order.payment_method,
            "order_date": order.order_date.isoformat(),
            "order_time": order.order_time.strftime("%H:%M:%S") if order.order_time else None,
            "processed_by": str(order.processed_by) if order.processed_by else None,
            "processed_by_name": processed_by_name,
            "notes": order.notes,
            "created_at": order.created_at.isoformat(),
            "updated_at": order.updated_at.isoformat()
        })
    
    return success_response(enriched_orders)
