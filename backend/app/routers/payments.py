from fastapi import APIRouter, Depends, Query, HTTPException
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
from app.core.responses import success_response
from app.domain.entities.user import User
from app.core.iyzico_config import IyzicoConfig

router = APIRouter(prefix="/api/payments", tags=["Payments"])


# ==================== Finance/Invoice Endpoints ====================

class InvoicePlanCreate(BaseModel):
    student_id: UUID
    total_amount: float = Field(..., gt=0)
    down_payment: Optional[float] = Field(None, ge=0)
    installment_count: int = Field(default=1, ge=1, le=24)
    first_due_date: date
    category: str = Field(..., description="EDUCATION, FOOD, SERVICE, TRANSPORT, UNIFORM, OTHER")


class PaymentCollectCreate(BaseModel):
    invoice_id: UUID
    amount: float = Field(..., gt=0)
    payment_method: str = Field(..., description="CASH, CREDIT_CARD, BANK_TRANSFER")
    transaction_ref: Optional[str] = None
    notes: Optional[str] = None


class ReminderSendCreate(BaseModel):
    invoice_ids: list[UUID]
    channel: str = Field(..., description="SMS, PUSH, EMAIL")


# ==================== iyzico Payment Endpoints ====================

class IyzicoPaymentRequest(BaseModel):
    debt_id: UUID
    amount: float = Field(..., gt=0)
    currency: str = Field(default="TRY")
    payment_channel: str = Field(default="WEB")
    basket_items: list[dict] = Field(default_factory=list)
    buyer: Optional[dict] = None
    shipping_address: Optional[dict] = None
    billing_address: Optional[dict] = None


@router.post("/iyzico/initialize")
async def initialize_iyzico_payment(
    payment_request: IyzicoPaymentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Initialize payment with iyzico"""
    import iyzipay
    from app.infrastructure.models.models import Debt, Student
    
    # Get debt
    debt_result = await db.execute(
        select(Debt).where(Debt.id == payment_request.debt_id)
    )
    debt = debt_result.scalar_one_or_none()
    
    if not debt:
        raise HTTPException(status_code=404, detail="Fatura bulunamadı")
    
    if payment_request.amount > debt.remaining_amount:
        raise HTTPException(status_code=400, detail="Ödeme tutarı kalan borçtan fazla olamaz")
    
    # Get student info
    student_result = await db.execute(
        select(Student).where(Student.id == debt.student_id)
    )
    student = student_result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Öğrenci bulunamadı")
    
    # Create iyzico request
    request = {
        'locale': 'tr',
        'conversationId': str(debt.id),
        'price': str(payment_request.amount),
        'paidPrice': str(payment_request.amount),
        'currency': payment_request.currency,
        'installment': 1,
        'basketId': str(debt.id),
        'paymentChannel': payment_request.payment_channel,
        'paymentGroup': 'PRODUCT',
        'callbackUrl': 'http://localhost:5006/api/payments/iyzico/callback',
        'buyer': {
            'id': str(student.id),
            'name': student.first_name,
            'surname': student.last_name,
            'gsmNumber': '',
            'email': 'test@example.com',
            'identityNumber': '12345678901',
            'lastLoginDate': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'registrationDate': student.created_at.strftime("%Y-%m-%d %H:%M:%S") if student.created_at else datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'registrationAddress': 'Test Address',
            'ip': '127.0.0.1',
            'city': 'Istanbul',
            'country': 'Turkey',
            'zipCode': '34000'
        },
        'shippingAddress': {
            'contactName': f"{student.first_name} {student.last_name}",
            'city': 'Istanbul',
            'country': 'Turkey',
            'address': 'Test Address',
            'zipCode': '34000'
        },
        'billingAddress': {
            'contactName': f"{student.first_name} {student.last_name}",
            'city': 'Istanbul',
            'country': 'Turkey',
            'address': 'Test Address',
            'zipCode': '34000'
        },
        'basketItems': []
    }
    
    # Add basket items
    if payment_request.basket_items:
        for i, item in enumerate(payment_request.basket_items):
            request['basketItems'].append({
                'id': str(i + 1),
                'name': item.get("name", "Eğitim Ödemesi"),
                'category1': item.get("category", "Eğitim"),
                'category2': item.get("subcategory", "Okul"),
                'itemType': "PHYSICAL",
                'price': str(item.get("price", payment_request.amount))
            })
    else:
        request['basketItems'].append({
            'id': "1",
            'name': f"{debt.debt_type} Ödemesi",
            'category1': "Eğitim",
            'category2': "Okul",
            'itemType': "PHYSICAL",
            'price': str(payment_request.amount)
        })
    
    try:
        checkout_form_initialize = iyzipay.CheckoutFormInitialize()
        result = checkout_form_initialize.create(request, IyzicoConfig.get_options())
        
        # Parse response
        response_data = result.read().decode('utf-8')
        import json
        result_json = json.loads(response_data)
        
        if result_json.get('status') == 'success':
            return success_response({
                "checkout_form_content": result_json.get('checkoutFormContent'),
                "token": result_json.get('token'),
                "payment_page_url": result_json.get('paymentPageUrl'),
                "conversation_id": result_json.get('conversationId')
            }, "Ödeme başlatıldı")
        else:
            raise HTTPException(status_code=500, detail=f"Ödeme başlatılamadı: {result_json.get('errorMessage', 'Bilinmeyen hata')}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ödeme başlatılamadı: {str(e)}")


@router.post("/iyzico/callback")
async def iyzico_callback(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """Handle iyzico payment callback"""
    import iyzipay
    from app.infrastructure.models.models import Debt, Payment, Branch
    from app.repositories import ReceiptRepository
    
    # Verify payment with iyzico
    request = {
        'locale': 'tr',
        'token': token
    }
    
    checkout_form_retrieve = iyzipay.CheckoutFormRetrieve()
    
    try:
        result = checkout_form_retrieve.retrieve(request, IyzicoConfig.get_options())
        
        # Parse response
        response_data = result.read().decode('utf-8')
        import json
        result_json = json.loads(response_data)
        
        if result_json.get('status') != 'success':
            return success_response({
                "status": "FAILED",
                "error_message": result_json.get('errorMessage', 'Ödeme başarısız')
            }, "Ödeme başarısız", success=False)
        
        # Get debt from conversation_id
        conversation_id = result_json.get('conversationId')
        if not conversation_id:
            raise HTTPException(status_code=400, detail="Conversation ID bulunamadı")
        
        debt_result = await db.execute(
            select(Debt).where(Debt.id == UUID(conversation_id))
        )
        debt = debt_result.scalar_one_or_none()
        
        if not debt:
            raise HTTPException(status_code=404, detail="Fatura bulunamadı")
        
        # Get branch for payment
        branch_result = await db.execute(
            select(Branch).where(Branch.id == debt.branch_id)
        )
        branch = branch_result.scalar_one_or_none()
        
        # Create payment record
        payment_amount = float(result_json.get('paidPrice', 0))
        new_payment = Payment(
            debt_id=debt.id,
            student_id=debt.student_id,
            organization_id=debt.organization_id,
            branch_id=debt.branch_id,
            amount=payment_amount,
            payment_method="CREDIT_CARD",
            transaction_reference=token,
            status="COMPLETED",
            payment_date=datetime.utcnow(),
            notes=f"iyzico ödeme - {result_json.get('paymentId', token)}"
        )
        db.add(new_payment)
        await db.flush()
        
        # Update debt status
        debt.paid_amount += payment_amount
        debt.remaining_amount = debt.amount - debt.paid_amount
        if debt.remaining_amount <= 0:
            debt.status = "PAID"
        else:
            debt.status = "PARTIALLY_PAID"
        
        # Create receipt
        receipt_repo = ReceiptRepository()
        try:
            receipt = await receipt_repo.create_for_payment(db, new_payment.id, new_payment.created_by)
        except ValueError:
            # Receipt already exists or payment not found, continue
            pass
        
        await db.commit()
        
        return success_response({
            "status": "SUCCESS",
            "payment_id": str(new_payment.id),
            "debt_id": str(debt.id),
            "amount": payment_amount,
            "remaining_amount": float(debt.remaining_amount)
        }, "Ödeme başarılı")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ödeme doğrulama hatası: {str(e)}")


@router.post("", response_model=PaymentResponse)
@require_permission("payments.create")
async def create_payment(
    payment: PaymentCreate,
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = PaymentRepository()
    payment = await repo.get(db, payment_id)
    
    if not payment or payment.organization_id != current_user.organization_id:
        return success_response(None, "Ödeme bulunamadı", success=False)
    
    return success_response(payment)


@router.put("/{payment_id}", response_model=PaymentResponse)
@require_permission("payments.update")
async def update_payment(
    payment_id: UUID,
    payment: PaymentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = PaymentRepository()
    db_payment = await repo.get(db, payment_id)
    
    if not db_payment or db_payment.organization_id != current_user.organization_id:
        return success_response(None, "Ödeme bulunamadı", success=False)
    
    payment_data = payment.model_dump(exclude_unset=True)
    payment_data["updated_by"] = current_user.id
    
    updated_payment = await repo.update(db, db_payment, payment_data)
    return success_response(updated_payment, "Ödeme güncellendi")


@router.delete("/{payment_id}")
@require_permission("payments.delete")
async def delete_payment(
    payment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = PaymentRepository()
    db_payment = await repo.get(db, payment_id)
    
    if not db_payment or db_payment.organization_id != current_user.organization_id:
        return success_response(None, "Ödeme bulunamadı", success=False)
    
    # TODO: Reverse payment, update debt, delete receipt
    
    await repo.soft_delete(db, payment_id)
    return success_response(message="Ödeme silindi")


# ==================== Finance Invoice Endpoints ====================

@router.post("/finances/invoices/generate-plan")
@require_permission("finance.invoices_manage")
async def generate_invoice_plan(
    plan: InvoicePlanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate installment plan for a student"""
    from app.repositories import DebtRepository
    from app.infrastructure.models.models import Student
    
    # Verify student exists
    student_result = await db.execute(
        select(Student).where(Student.id == plan.student_id)
    )
    student = student_result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Öğrenci bulunamadı")
    
    debt_repo = DebtRepository()
    
    # Calculate installment amounts
    if plan.down_payment:
        remaining_amount = plan.total_amount - plan.down_payment
        installment_amount = remaining_amount / plan.installment_count
    else:
        installment_amount = plan.total_amount / plan.installment_count
    
    # Create installment debts
    from datetime import timedelta
    from app.infrastructure.models.models import Debt
    
    created_invoices = []
    
    # Create down payment invoice if specified
    if plan.down_payment and plan.down_payment > 0:
        down_payment_debt = Debt(
            student_id=plan.student_id,
            organization_id=current_user.organization_id,
            debt_type=plan.category,
            description=f"{plan.category} - Peşin Ödeme",
            amount=plan.down_payment,
            paid_amount=0,
            due_date=plan.first_due_date,
            status="UNPAID",
            created_by=current_user.id
        )
        db.add(down_payment_debt)
        await db.flush()
        created_invoices.append({
            "id": str(down_payment_debt.id),
            "type": "DOWN_PAYMENT",
            "amount": float(down_payment_debt.amount),
            "due_date": down_payment_debt.due_date.isoformat()
        })
    
    # Create installment invoices
    for i in range(plan.installment_count):
        due_date = plan.first_due_date + timedelta(days=30 * (i + 1))  # Monthly installments
        
        installment_debt = Debt(
            student_id=plan.student_id,
            organization_id=current_user.organization_id,
            debt_type=plan.category,
            description=f"{plan.category} - {i + 1}. Taksit",
            amount=installment_amount,
            paid_amount=0,
            due_date=due_date,
            status="UNPAID",
            created_by=current_user.id
        )
        db.add(installment_debt)
        await db.flush()
        created_invoices.append({
            "id": str(installment_debt.id),
            "type": f"INSTALLMENT_{i + 1}",
            "amount": float(installment_debt.amount),
            "due_date": installment_debt.due_date.isoformat()
        })
    
    await db.commit()
    
    return success_response({
        "student_id": str(plan.student_id),
        "total_amount": plan.total_amount,
        "down_payment": plan.down_payment,
        "installment_count": plan.installment_count,
        "installment_amount": float(installment_amount),
        "invoices": created_invoices
    }, "Taksit planı oluşturuldu")


@router.post("/finances/payments/collect")
@require_permission("finance.collect_payment")
async def collect_payment(
    payment_data: PaymentCollectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Collect payment for an invoice"""
    from app.repositories import ReceiptRepository
    from app.infrastructure.models.models import Debt, Payment, Branch
    
    # Get debt/invoice
    debt_result = await db.execute(
        select(Debt).where(Debt.id == payment_data.invoice_id)
    )
    debt = debt_result.scalar_one_or_none()
    
    if not debt:
        raise HTTPException(status_code=404, detail="Fatura bulunamadı")
    
    if payment_data.amount > debt.remaining_amount:
        raise HTTPException(status_code=400, detail="Ödeme tutarı kalan borçtan fazla olamaz")
    
    # Get branch for payment
    branch_result = await db.execute(
        select(Branch).where(Branch.id == debt.branch_id)
    )
    branch = branch_result.scalar_one_or_none()
    
    # Create payment record
    new_payment = Payment(
        debt_id=debt.id,
        student_id=debt.student_id,
        organization_id=debt.organization_id,
        branch_id=debt.branch_id,
        amount=payment_data.amount,
        payment_method=payment_data.payment_method.upper(),
        transaction_reference=payment_data.transaction_ref,
        notes=payment_data.notes,
        status="COMPLETED",
        payment_date=datetime.utcnow(),
        created_by=current_user.id
    )
    
    db.add(new_payment)
    await db.flush()
    
    # Update debt
    debt.paid_amount += payment_data.amount
    debt.remaining_amount -= payment_data.amount
    
    if debt.remaining_amount <= 0:
        debt.status = "PAID"
        debt.remaining_amount = 0
    
    # Create receipt
    receipt_repo = ReceiptRepository()
    try:
        receipt = await receipt_repo.create_for_payment(db, new_payment.id, current_user.id)
    except ValueError:
        # Receipt already exists or payment not found, continue
        pass
    
    await db.commit()
    await db.refresh(new_payment)
    
    return success_response({
        "payment_id": str(new_payment.id),
        "invoice_id": str(debt.id),
        "amount": float(new_payment.amount),
        "payment_method": new_payment.payment_method,
        "remaining_debt": float(debt.remaining_amount),
        "debt_status": debt.status,
        "payment_date": new_payment.payment_date.isoformat()
    }, "Ödeme alındı")


@router.get("/finances/payments/{payment_id}/receipt-pdf")
@require_permission("finance.view")
async def get_payment_receipt_pdf(
    payment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get PDF receipt for a payment"""
    from app.infrastructure.models.models import Payment
    
    result = await db.execute(
        select(Payment).where(Payment.id == payment_id)
    )
    payment = result.scalar_one_or_none()
    
    if not payment:
        raise HTTPException(status_code=404, detail="Ödeme bulunamadı")
    
    # In a real implementation, this would generate and return a PDF
    # For now, return a placeholder response
    return success_response({
        "payment_id": str(payment.id),
        "receipt_url": f"/receipts/{payment_id}.pdf",
        "amount": float(payment.amount),
        "payment_date": payment.payment_date.isoformat(),
        "payment_method": payment.payment_method,
        "transaction_reference": payment.transaction_reference
    })


@router.post("/finances/reminders/send")
@require_permission("finance.view")
async def send_payment_reminders(
    reminder: ReminderSendCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send payment reminders via SMS/PUSH"""
    from app.infrastructure.models.models import Debt, Student
    
    sent_reminders = []
    
    for invoice_id in reminder.invoice_ids:
        debt_result = await db.execute(
            select(Debt).where(Debt.id == invoice_id)
        )
        debt = debt_result.scalar_one_or_none()
        
        if not debt:
            continue
        
        # Get student info
        student_result = await db.execute(
            select(Student).where(Student.id == debt.student_id)
        )
        student = student_result.scalar_one_or_none()
        
        if student:
            # In a real implementation, this would send SMS/PUSH notification
            sent_reminders.append({
                "invoice_id": str(debt.id),
                "student_id": str(student.id),
                "student_name": f"{student.first_name} {student.last_name}",
                "amount": float(debt.remaining_amount),
                "due_date": debt.due_date.isoformat(),
                "channel": reminder.channel,
                "status": "SENT"
            })
    
    return success_response({
        "total_sent": len(sent_reminders),
        "reminders": sent_reminders
    }, f"{len(sent_reminders)} adet hatırlatma gönderildi")
