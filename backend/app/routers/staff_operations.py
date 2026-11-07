from __future__ import annotations
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.permissions import PermissionChecker
from app.core.responses import success_response
from app.domain.entities.user import User
from app.core.tenant import TenantContext

router = APIRouter(prefix="/api/staff-operations", tags=["Staff Operations"])


# ==================== TRANSPORT (SERVİS) ENDPOINTS ====================

class TransportCheckIn(BaseModel):
    route_id: UUID
    student_id: UUID
    event: str = Field(..., description="BOARDED or DROPPED")
    timestamp: datetime


@router.get("/transport/routes")
async def get_transport_routes(
    branch_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("transport.manage"))
):
    from app.application.services import transport_service
    return success_response(await transport_service.records(db, tenant, branch_id))


@router.post("/transport/check-in")
async def create_transport_check_in(
    check_in: TransportCheckIn,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("transport.manage"))
):
    from app.application.services import transport_service
    if check_in.event not in {"BOARDED", "DROPPED"}:
        raise HTTPException(status_code=422, detail="Geçersiz servis olayı")
    return success_response(await transport_service.checkin(db, tenant, check_in.route_id,
        check_in.student_id, check_in.event == "BOARDED", True, check_in.timestamp))


# ==================== CANTEEN (KANTİN) ENDPOINTS ====================

class WalletTopUp(BaseModel):
    amount: float = Field(..., gt=0)
    payment_method: str = Field(..., description="CASH, CREDIT_CARD, etc.")


class CanteenSale(BaseModel):
    student_id: UUID
    items: List[dict] = Field(..., description="List of product_id, qty, price")


@router.get("/canteen/wallet/{student_id}")
async def get_canteen_wallet(
    student_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("canteen.manage"))
):
    from app.application.services import canteen_wallet_service as wallets
    return success_response(wallets.serialize(*(await wallets.wallet(db, tenant, student_id))))


@router.post("/canteen/wallet/{student_id}/top-up")
async def top_up_canteen_wallet(
    student_id: UUID,
    top_up: WalletTopUp,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("canteen.manage"))
):
    from app.application.services import canteen_wallet_service as wallets
    return success_response(await wallets.topup(db, tenant, student_id, top_up.amount, top_up.payment_method))


@router.post("/canteen/transactions/sale")
async def create_canteen_sale(
    sale: CanteenSale,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("canteen.manage"))
):
    from app.application.services import canteen_wallet_service as wallets
    if not sale.items:
        raise HTTPException(status_code=422, detail="Satış için ürün seçin")
    results = []
    for item in sale.items:
        if not item.get("product_id"):
            raise HTTPException(status_code=422, detail="Ürün kimliği gerekli")
        results.append(await wallets.purchase(db, tenant, sale.student_id, product_id=item["product_id"],
            quantity=int(item.get("qty", 1))))
    return success_response({"items": results, "total_amount": sum(row["amount"] for row in results),
        "remaining_balance": results[-1]["current_balance"]})


# ==================== LIBRARY (KÜTÜPHANE) ENDPOINTS ====================

class LibraryBorrow(BaseModel):
    book_id: UUID
    student_id: UUID
    due_date: datetime


@router.get("/library/books")
async def get_library_books(
    search: Optional[str] = None,
    available_only: bool = False,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("library.manage"))
):
    """Get library books"""
    from app.infrastructure.models.models import LibraryBook
    
    query = select(LibraryBook)
    
    if available_only:
        query = query.where(LibraryBook.available_copies > 0)
    
    if search:
        query = query.where(
            LibraryBook.title.ilike(f"%{search}%") | 
            LibraryBook.author.ilike(f"%{search}%") |
            LibraryBook.isbn.ilike(f"%{search}%")
        )
    
    result = await db.execute(query)
    books = result.scalars().all()
    
    books_data = []
    for book in books:
        books_data.append({
            "book_id": str(book.id),
            "title": book.title,
            "author": book.author,
            "isbn": book.isbn,
            "total_copies": book.total_copies,
            "available_copies": book.available_copies,
            "category": book.category
        })
    
    return success_response(books_data)


@router.post("/library/borrow")
async def create_library_borrow(
    borrow: LibraryBorrow,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("library.manage"))
):
    """Create a library book loan"""
    from app.infrastructure.models.models import LibraryBook, LibraryLoan, Student
    
    # Verify book availability
    book_result = await db.execute(
        select(LibraryBook).where(LibraryBook.id == borrow.book_id)
    )
    book = book_result.scalar_one_or_none()
    
    if not book:
        raise HTTPException(status_code=404, detail="Kitap bulunamadı")
    
    if book.available_copies <= 0:
        raise HTTPException(status_code=400, detail="Bu kitap için uygun kopya yok")
    
    # Verify student access
    student_result = await db.execute(
        select(Student).where(Student.id == borrow.student_id)
    )
    student = student_result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Öğrenci bulunamadı")
    
    if tenant.branch_ids and student.branch_id not in tenant.branch_ids:
        raise HTTPException(status_code=403, detail="Bu öğrenciye erişiminiz yok")
    
    # Create loan record
    new_loan = LibraryLoan(
        book_id=borrow.book_id,
        student_id=borrow.student_id,
        borrowed_date=datetime.utcnow(),
        due_date=borrow.due_date,
        loaned_by=current_user.id
    )
    
    db.add(new_loan)
    
    # Update available copies
    book.available_copies -= 1
    
    await db.commit()
    await db.refresh(new_loan)
    
    return success_response({
        "loan_id": str(new_loan.id),
        "book_id": str(new_loan.book_id),
        "student_id": str(new_loan.student_id),
        "borrowed_date": new_loan.borrowed_date.isoformat() if new_loan.borrowed_date else None,
        "due_date": new_loan.due_date.isoformat() if new_loan.due_date else None,
        "status": "BORROWED"
    }, "Kitap ödünç verildi")


@router.post("/library/return/{loan_id}")
async def return_library_book(
    loan_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("library.manage"))
):
    """Return a library book"""
    from app.infrastructure.models.models import LibraryLoan, LibraryBook
    
    # Get loan record
    loan_result = await db.execute(
        select(LibraryLoan).where(LibraryLoan.id == loan_id)
    )
    loan = loan_result.scalar_one_or_none()
    
    if not loan:
        raise HTTPException(status_code=404, detail="Ödünç kaydı bulunamadı")
    
    if loan.returned_date:
        raise HTTPException(status_code=400, detail="Bu kitap zaten iade edilmiş")
    
    # Update loan record
    loan.returned_date = datetime.utcnow()
    loan.returned_by = current_user.id
    
    # Update available copies
    book_result = await db.execute(
        select(LibraryBook).where(LibraryBook.id == loan.book_id)
    )
    book = book_result.scalar_one_or_none()
    
    if book:
        book.available_copies += 1
    
    await db.commit()
    
    return success_response({
        "loan_id": str(loan.id),
        "book_id": str(loan.book_id),
        "student_id": str(loan.student_id),
        "returned_date": loan.returned_date.isoformat() if loan.returned_date else None,
        "status": "RETURNED"
    }, "Kitap iade alındı")
