from fastapi import APIRouter, Depends, Query, HTTPException, Request, Form
from typing import Literal
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional
from uuid import UUID
from datetime import datetime, date
from pydantic import BaseModel, Field

from app.application.schemas import PaymentCreate, PaymentUpdate, PaymentResponse
from app.repositories import PaymentRepository
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.permissions import require_permission
from app.core.permissions import PermissionChecker
from app.core.tenant import TenantContext
from app.core.responses import success_response
from app.domain.entities.user import User
from app.core.iyzico_config import IyzicoConfig

router = APIRouter(prefix="/api/payments", tags=["Payments"])


# ==================== Finance/Invoice Endpoints ====================

class InvoicePlanCreate(BaseModel):
    student_id: UUID
    total_amount: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)
    down_payment: Optional[Decimal] = Field(None, ge=0, max_digits=12, decimal_places=2)
    installment_count: int = Field(default=1, ge=1, le=24)
    first_due_date: date
    category: Literal["EDUCATION", "FOOD", "SERVICE", "TRANSPORT", "UNIFORM", "STATIONERY", "ACTIVITY", "OTHER"]


class PaymentCollectCreate(BaseModel):
    invoice_id: UUID
    amount: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)
    payment_method: Literal["CASH", "CREDIT_CARD", "BANK_TRANSFER", "EFT", "OTHER"]
    transaction_ref: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = Field(None, max_length=500)
    request_id: Optional[UUID] = None


class ReminderSendCreate(BaseModel):
    invoice_ids: list[UUID] = Field(..., min_length=1, max_length=500)
    channel: Literal["SMS", "WHATSAPP", "EMAIL"]


# ==================== iyzico Payment Endpoints ====================

@router.get("/iyzico/debts/{debt_id}")
async def checkout_debt(debt_id: UUID, tenant: TenantContext = Depends(PermissionChecker("parent.make_payment", "finance.write")), db: AsyncSession = Depends(get_db, scope="function")):
    from app.application.services.online_payment_service import available_for
    from app.core.student_access import require_student_access, require_parent_child_access
    from app.infrastructure.models.models import Debt
    from app.infrastructure.repositories.base import BaseRepository
    debt = await BaseRepository(db, tenant).get_by_id(debt_id, Debt)
    if not tenant.has_permission("finance.write"):
        await require_parent_child_access(db, tenant.user_id, debt.student_id)
    await require_student_access(db, tenant, debt.student_id)
    return success_response({"id": str(debt.id), "description": debt.description, "amount": str(debt.amount), "remaining_amount": str(debt.remaining_amount),
        "status": debt.status, "online_payment_available": await available_for(db, debt.organization_id)})


@router.get("/iyzico/checkouts/{checkout_id}")
async def checkout_status(checkout_id: UUID, tenant: TenantContext = Depends(PermissionChecker("parent.make_payment", "finance.write", "finance.read")), db: AsyncSession = Depends(get_db, scope="function")):
    from app.application.services import school_checkout_service
    return success_response(await school_checkout_service.status(db, tenant, checkout_id))


@router.post("/iyzico/checkouts/{checkout_id}/resume")
async def resume_school_checkout(checkout_id: UUID, tenant: TenantContext = Depends(PermissionChecker("parent.make_payment", "finance.write")), db: AsyncSession = Depends(get_db, scope="function")):
    from app.application.services import school_checkout_service
    return success_response(await school_checkout_service.resume(db, tenant, checkout_id))


@router.post("/iyzico/checkouts/{checkout_id}/refresh")
async def refresh_school_checkout(checkout_id: UUID, tenant: TenantContext = Depends(PermissionChecker("parent.make_payment", "finance.write")), db: AsyncSession = Depends(get_db, scope="function")):
    from app.application.services import school_checkout_service
    return success_response(await school_checkout_service.refresh(db, tenant, checkout_id))

class IyzicoPaymentRequest(BaseModel):
    request_id: Optional[UUID] = None
    debt_id: UUID
    amount: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)
    currency: Literal["TRY"] = "TRY"
    payment_channel: str = Field(default="WEB")
    basket_items: list[dict] = Field(default_factory=list)
    buyer: Optional[dict] = None
    shipping_address: Optional[dict] = None
    billing_address: Optional[dict] = None


@router.post("/iyzico/initialize")
async def initialize_iyzico_payment(
    payment_request: IyzicoPaymentRequest,
    request: Request,
    tenant: TenantContext = Depends(PermissionChecker("parent.make_payment", "finance.write")),
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user)
):
    from app.application.services import online_payment_service
    return success_response(await online_payment_service.initialize(db, tenant, current_user, payment_request,
        request.client.host if request.client else "127.0.0.1"))


@router.post("/iyzico/callback")
async def iyzico_callback(
    request: Request,
    token: str | None = Query(None),
    form_token: str | None = Form(None, alias="token"),
    checkout_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db, scope="function")
):
    from app.application.services import online_payment_service
    supplied_token = form_token or token
    if not supplied_token:
        raise HTTPException(status_code=422, detail="Ödeme token bilgisi gerekli")
    result = await online_payment_service.reconcile(db, supplied_token, checkout_id=checkout_id)
    if checkout_id and "text/html" in request.headers.get("accept", ""):
        from app.application.services import school_checkout_service
        from app.infrastructure.models.models import PaymentCheckout
        from fastapi.responses import RedirectResponse
        row = await db.get(PaymentCheckout, checkout_id)
        if row and row.merchant_snapshot:
            target = await school_checkout_service.callback_return(db, row)
            if target: return RedirectResponse(target, status_code=303)
    return success_response(result)


@router.post("", response_model=PaymentResponse)
@require_permission("payments.create")
async def create_payment(
    payment: PaymentCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user)
):
    from app.repositories import ReceiptRepository
    from app.infrastructure.models.models import Debt
    
    repo = PaymentRepository()
    payment_data = payment.model_dump()
    payment_data["created_by"] = current_user.id
    payment_data["organization_id"] = current_user.organization_id
    
    db_payment = await repo.create(db, payment_data)
    
    # Update debt remaining amount
    if hasattr(db_payment, 'debt_id') and db_payment.debt_id:
        debt_result = await db.execute(
            select(Debt).where(Debt.id == db_payment.debt_id)
        )
        debt = debt_result.scalar_one_or_none()
        if debt:
            debt.paid_amount += db_payment.amount
            debt.remaining_amount = debt.amount - debt.paid_amount
            if debt.remaining_amount <= 0:
                debt.status = "PAID"
            else:
                debt.status = "PARTIALLY_PAID"
    
    # Create receipt
    receipt_repo = ReceiptRepository()
    try:
        receipt = await receipt_repo.create_for_payment(db, db_payment.id, current_user.id)
    except ValueError:
        # Receipt already exists or payment not found, continue
        pass
    
    return success_response(db_payment, "Ödeme oluşturuldu")


@router.get("", response_model=list[PaymentResponse])
@require_permission("payments.view")
async def list_payments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    student_id: Optional[UUID] = None,
    debt_id: Optional[UUID] = None,
    payment_method: Optional[str] = None,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user)
):
    repo = PaymentRepository()
    
    filters = {"organization_id": current_user.organization_id}
    if student_id:
        filters["student_id"] = student_id
    if debt_id:
        filters["debt_id"] = debt_id
    if payment_method:
        filters["payment_method"] = payment_method
    
    payments = await repo.get_multi(db, skip, limit, filters)
    return success_response(payments)


@router.get("/{payment_id}", response_model=PaymentResponse)
@require_permission("payments.view")
async def get_payment(
    payment_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user)
):
    repo = PaymentRepository()
    payment = await repo.get(db, payment_id)
    
    if not payment or payment.organization_id != current_user.organization_id:
        return success_response(None, "Ödeme bulunamadı", success=False)
    
    return success_response(payment)


@router.put("/{payment_id}")
async def update_payment(
    payment_id: UUID, payment: PaymentUpdate,
    tenant: TenantContext = Depends(PermissionChecker("finance.write", "payments.update")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    from app.infrastructure.models.models import Payment
    from app.infrastructure.repositories.base import BaseRepository
    from app.core.exceptions import ValidationException
    row = await BaseRepository(db, tenant).get_by_id(payment_id, Payment, for_update=True)
    changes = payment.model_dump(exclude_unset=True)
    if set(changes) - {"notes"}:
        raise ValidationException("Tahsilat tutarı ve bilgileri değiştirilemez; iptal edip yeni tahsilat oluşturun")
    if row.cancelled_at:
        raise ValidationException("İptal edilmiş tahsilat değiştirilemez")
    row.notes = changes.get("notes", row.notes)
    await db.flush()
    return success_response({"id": str(row.id), "notes": row.notes}, "Tahsilat notu güncellendi")


@router.delete("/{payment_id}")
async def delete_payment(
    payment_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("finance.write", "payments.delete")),
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db, scope="function"),
):
    from app.routers.core_modules import cancel_payment
    from app.application.schemas.common import PaymentCancel
    return await cancel_payment(payment_id, PaymentCancel(cancel_reason="API üzerinden iptal"), tenant, current_user, db)

@router.post("/finances/invoices/generate-plan")
async def generate_invoice_plan(
    plan: InvoicePlanCreate, db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("finance.write", "finance.invoices_manage")),
):
    from app.application.services import finance_compat_service
    return success_response(await finance_compat_service.plan(db, tenant, current_user, plan), "Taksit planı oluşturuldu")


@router.post("/finances/payments/collect")
async def collect_payment(
    payment_data: PaymentCollectCreate, db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("finance.write", "finance.collect_payment")),
):
    from app.routers.core_modules import take_payment
    from app.application.schemas.common import PaymentCreate as LedgerPaymentCreate
    notes = payment_data.notes or ""
    if payment_data.transaction_ref:
        notes += ("\n" if notes else "") + "İşlem referansı: " + payment_data.transaction_ref
    return await take_payment(LedgerPaymentCreate(debt_id=str(payment_data.invoice_id), amount=str(payment_data.amount),
        payment_method=payment_data.payment_method, notes=notes or None, request_id=payment_data.request_id), tenant, current_user, db)


@router.get("/finances/payments/{payment_id}/receipt-pdf")
async def get_payment_receipt_pdf(
    payment_id: UUID, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("receipt.read")),
):
    from app.infrastructure.models.models import Payment, Receipt
    from app.infrastructure.repositories.base import BaseRepository
    from app.core.exceptions import NotFoundException
    from app.routers.files_receipts import download_receipt_pdf
    await BaseRepository(db, tenant).get_by_id(payment_id, Payment)
    receipt = (await db.execute(select(Receipt).where(Receipt.payment_id == payment_id))).scalar_one_or_none()
    if receipt is None:
        raise NotFoundException("Bu tahsilata ait makbuz bulunamadı")
    return await download_receipt_pdf(receipt.id, tenant, db)


@router.post("/finances/reminders/send")
async def send_payment_reminders(
    reminder: ReminderSendCreate, db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("finance.write")),
):
    from app.application.services import finance_compat_service
    return success_response(await finance_compat_service.reminders(db, tenant, current_user, reminder),
        "Ödeme hatırlatmaları kuyruğa alındı")
