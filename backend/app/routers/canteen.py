"""
Canteen POS & Dietary Restrictions Module API
Handles POS checkout, dietary restrictions, and canteen management
"""
from datetime import UTC, datetime, date, time
from decimal import Decimal
from typing import Optional, List
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, validator
from sqlalchemy import select, and_, func, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.responses import success_response
from app.core.permissions import PermissionChecker
from app.core.tenant import TenantContext
from app.infrastructure.repositories.base import BaseRepository
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
    price: Decimal = Field(..., gt=0, le=Decimal("99999999.99"), decimal_places=2)
    image_url: Optional[str] = None
    allergens: Optional[List[str]] = Field(None, description="PEANUT, DAIRY, GLUTEN, EGG, SOY, FISH, SHELLFISH, TREE_NUT, SESAME, OTHER")
    nutritional_info: Optional[dict] = None
    is_available: Optional[bool] = None
    request_id: Optional[UUID] = None
    expected_updated_at: Optional[datetime] = None

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
    request_id: UUID = Field(default_factory=uuid4)
    expected_unit_price: Optional[Decimal] = Field(None, gt=0, le=Decimal("99999999.99"), decimal_places=2)

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


class POSCartItem(BaseModel):
    product_id: UUID
    quantity: int = Field(ge=1, le=2147483647)
    expected_unit_price: Decimal = Field(gt=0, le=Decimal("99999999.99"), decimal_places=2)


class POSCartRequest(BaseModel):
    student_id: UUID
    branch_id: UUID
    request_id: UUID
    items: list[POSCartItem] = Field(min_length=1, max_length=100)

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
    amount: Decimal = Field(..., gt=0, le=Decimal("99999999.99"), decimal_places=2)
    payment_method: str = Field(..., description="CASH, CARD, BANK_TRANSFER")
    reference_number: Optional[str] = Field(None, max_length=100)
    request_id: UUID = Field(default_factory=uuid4)


# ==================== Canteen Products Endpoints ====================

@router.get("/products")
async def get_canteen_products(
    branch_id: Optional[UUID] = Query(None),
    record_id: Optional[UUID] = None,
    category: Optional[str] = Query(None),
    is_available: Optional[bool] = Query(True),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("canteen.read"))
):
    """Get canteen products with filtering"""
    query = select(CanteenProduct)
    
    conditions = []
    if branch_id:
        conditions.append(CanteenProduct.branch_id == branch_id)
    if record_id:
        conditions.append(CanteenProduct.id == record_id)
    if category:
        conditions.append(CanteenProduct.category == category)
    if is_available is not None and record_id is None:
        conditions.append(CanteenProduct.is_available == is_available)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(CanteenProduct.category, CanteenProduct.name, CanteenProduct.id).limit(limit).offset(offset)
    
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
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("canteen.write"))
):
    """Create a new canteen product"""
    branch = await BaseRepository(db, tenant).get_by_id(product.branch_id, Branch)
    await db.execute(update(Branch).where(Branch.id == branch.id).values(updated_at=Branch.updated_at))
    values = dict(
        branch_id=product.branch_id,
        name=product.name.strip(),
        description=product.description,
        category=product.category,
        price=product.price,
        image_url=product.image_url,
        is_available=product.is_available if product.is_available is not None else True,
        allergens=product.allergens or [],
        nutritional_info=product.nutritional_info
    )
    if not values["name"]:
        raise HTTPException(422, "Ürün adı boş olamaz")
    if product.request_id:
        previous = (await db.execute(select(CanteenProduct).where(CanteenProduct.id == product.request_id))).scalar_one_or_none()
        if previous is not None:
            if previous.created_by != tenant.user_id or any(getattr(previous, key) != value for key, value in values.items()):
                raise HTTPException(409, "İstek kimliği farklı ürüne ait")
            return success_response({"id": str(previous.id), "name": previous.name, "price": float(previous.price),
                "category": previous.category, "created_at": previous.created_at.isoformat()})
    new_product = CanteenProduct(id=product.request_id or uuid4(), created_by=tenant.user_id, **values)
    db.add(new_product)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(409, "Ürün kaydı kimliği kullanılamıyor") from exc
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
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("canteen.write"))
):
    """Update a canteen product"""
    await db.execute(update(CanteenProduct).where(CanteenProduct.id == product_id).values(updated_at=CanteenProduct.updated_at))
    result = await db.execute(
        select(CanteenProduct).where(CanteenProduct.id == product_id).with_for_update()
    )
    existing_product = result.scalar_one_or_none()
    
    if not existing_product:
        raise HTTPException(status_code=404, detail="Product not found")
    await BaseRepository(db, tenant).get_by_id(product.branch_id, Branch)
    if not product.name.strip():
        raise HTTPException(422, "Ürün adı boş olamaz")
    values = {
        "branch_id": product.branch_id, "name": product.name.strip(), "description": product.description,
        "category": product.category, "price": product.price, "image_url": product.image_url, "allergens": product.allergens or [],
        "nutritional_info": product.nutritional_info, "is_available": product.is_available if product.is_available is not None else existing_product.is_available,
    }
    same = all(getattr(existing_product, key) == value for key, value in values.items())
    if product.expected_updated_at is not None:
        def utc(value):
            return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
        if utc(product.expected_updated_at) != utc(existing_product.updated_at) and not (same and existing_product.updated_by == tenant.user_id):
            raise HTTPException(409, "Ürün değişti; güncel ürünü yükleyin")
    if existing_product.branch_id != product.branch_id and (await db.execute(
        select(CanteenOrder.id).where(CanteenOrder.product_id == existing_product.id).limit(1)
    )).first():
        raise HTTPException(409, "Satış kaydı olan ürün başka şubeye taşınamaz")
    if not same:
        for field, value in values.items():
            setattr(existing_product, field, value)
        existing_product.updated_by = tenant.user_id
        existing_product.updated_at = datetime.now(UTC)
    
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
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("canteen.write"))
):
    """Delete a canteen product"""
    result = await db.execute(
        select(CanteenProduct).where(CanteenProduct.id == product_id)
    )
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if (await db.execute(select(CanteenOrder.id).where(CanteenOrder.product_id == product.id).limit(1))).first():
        raise HTTPException(409, "Satış kaydı olan ürünü katalogdan satışa kapatın")
    
    await db.delete(product)
    await db.commit()
    
    return success_response({"id": str(product_id), "message": "Ürün silindi"})


# ==================== Dietary Restrictions Endpoints ====================

@router.get("/dietary-restrictions")
async def get_dietary_restrictions(
    student_id: Optional[UUID] = Query(None),
    is_active: Optional[bool] = Query(True),
    db: AsyncSession = Depends(get_db, scope="function"),
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
    db: AsyncSession = Depends(get_db, scope="function"),
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
    db: AsyncSession = Depends(get_db, scope="function"),
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

@router.get("/options")
async def canteen_options(branch_id: Optional[UUID] = None, search: str = Query("", max_length=100),
    db: AsyncSession = Depends(get_db, scope="function"), tenant: TenantContext = Depends(PermissionChecker("canteen.read"))):
    from app.application.services.student_choices import options
    if branch_id:
        await BaseRepository(db, tenant).get_by_id(branch_id, Branch)
    branches = select(Branch).where(Branch.deleted_at.is_(None))
    if branch_id:
        branches = branches.where(Branch.id == branch_id)
    rows = (await db.execute(branches.order_by(Branch.name, Branch.id).limit(1000))).scalars().all()
    return success_response({**await options(db, search=search.strip(), branch_id=branch_id),
        "branches": [{"id": str(row.id), "name": row.name} for row in rows]})


@router.post("/pos/checkout")
async def pos_checkout(
    request: POSCheckoutRequest,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("canteen.write"))
):
    from app.application.services import canteen_wallet_service as wallets
    method = (request.payment_method or "WALLET").upper()
    async def record():
        return await wallets.purchase(db, tenant, request.student_id, product_id=request.product_id,
            quantity=request.quantity, payment_method=method, expected_unit_price=request.expected_unit_price)
    return success_response(await wallets.record_command(db, tenant, request.student_id, request.branch_id, request.request_id,
        "CANTEEN_POS_RECORDED", {"product_id": str(request.product_id), "quantity": request.quantity, "payment_method": method,
            "expected_unit_price": str(request.expected_unit_price.quantize(Decimal("0.01"))) if request.expected_unit_price is not None else None}, record))


@router.get("/student/{student_id}/wallet")
async def get_student_wallet_info(
    student_id: UUID,
    branch_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("canteen.read"))
):
    from app.application.services import canteen_wallet_service as wallets
    return success_response(wallets.serialize(*(await wallets.wallet(db, tenant, student_id, read_only=True, branch_id=branch_id))))


@router.post("/pos/cart-checkout")
async def pos_cart_checkout(request: POSCartRequest, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("canteen.write"))):
    from app.application.services import canteen_wallet_service as wallets
    if len({item.product_id for item in request.items}) != len(request.items):
        raise HTTPException(422, "Aynı ürün sepette tek satır olmalı")

    async def record():
        details = []
        balance = None
        for item in request.items:
            balance = await wallets.purchase(db, tenant, request.student_id, product_id=item.product_id, quantity=item.quantity,
                payment_method="WALLET", expected_unit_price=item.expected_unit_price)
            details.append({"order_id": balance["order_id"], "transaction_id": balance["transaction_id"],
                "product_id": str(item.product_id), "quantity": item.quantity, "total": balance["total_price"]})
        return {"student_id": str(request.student_id), "branch_id": str(request.branch_id), "authorized": True,
            "balance": balance["balance"], "items": details}

    fields = {"items": [{"product_id": str(item.product_id), "quantity": item.quantity,
        "expected_unit_price": str(item.expected_unit_price.quantize(Decimal("0.01")))} for item in request.items]}
    return success_response(await wallets.record_command(db, tenant, request.student_id, request.branch_id, request.request_id,
        "CANTEEN_CART_RECORDED", fields, record))


@router.get("/student/{student_id}/wallet/transactions")
async def get_student_wallet_transactions(student_id: UUID, branch_id: Optional[UUID] = None,
    record_id: Optional[UUID] = None, limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db, scope="function"), tenant: TenantContext = Depends(PermissionChecker("canteen.read"))):
    from app.application.services import canteen_wallet_service as wallets
    return success_response(await wallets.transactions(db, tenant, student_id, branch_id=branch_id,
        record_id=record_id, limit=limit, offset=offset))


@router.post("/student/{student_id}/wallet/top-up")
async def wallet_top_up(
    student_id: UUID,
    top_up: WalletTopUpCreate,
    branch_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("canteen.write"))
):
    from app.application.services import canteen_wallet_service as wallets
    if student_id != top_up.student_id:
        raise HTTPException(422, "Cüzdan öğrencisi işlemle eşleşmiyor")
    method = top_up.payment_method.strip().upper()
    if method not in {"CASH", "CARD", "CREDIT_CARD", "BANK_TRANSFER"}:
        raise HTTPException(422, "Geçersiz bakiye kayıt yöntemi")
    async def record():
        return await wallets.topup(db, tenant, student_id, top_up.amount, method, top_up.reference_number)
    return success_response(await wallets.record_command(db, tenant, student_id, branch_id, top_up.request_id,
        "CANTEEN_TOPUP_RECORDED", {"amount": str(top_up.amount.quantize(Decimal("0.01"))), "payment_method": method,
        "reference_number": top_up.reference_number}, record))


# ==================== Canteen Orders Endpoints ====================

@router.get("/orders")
async def get_canteen_orders(
    student_id: Optional[UUID] = Query(None),
    record_id: Optional[UUID] = None,
    branch_id: Optional[UUID] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("canteen.read"))
):
    """Get canteen orders with filtering"""
    query = select(CanteenOrder)
    
    conditions = []
    if student_id:
        conditions.append(CanteenOrder.student_id == student_id)
    if record_id:
        conditions.append(CanteenOrder.id == record_id)
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
