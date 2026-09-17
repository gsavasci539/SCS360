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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("transport.manage"))
):
    """Get transport routes for staff"""
    from app.infrastructure.models.models import BusRoute
    
    query = select(BusRoute)
    
    if branch_id:
        query = query.where(BusRoute.branch_id == branch_id)
    elif tenant.branch_ids:
        query = query.where(BusRoute.branch_id.in_(tenant.branch_ids))
    
    result = await db.execute(query)
    routes = result.scalars().all()
    
    routes_data = []
    for route in routes:
        routes_data.append({
            "route_id": str(route.id),
            "route_name": route.route_name,
            "vehicle_plate": route.vehicle_plate,
            "driver_name": route.driver_name,
            "driver_phone": route.driver_phone,
            "capacity": route.capacity,
            "branch_id": str(route.branch_id) if route.branch_id else None
        })
    
    return success_response(routes_data)


@router.post("/transport/check-in")
async def create_transport_check_in(
    check_in: TransportCheckIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("transport.manage"))
):
    """Create a transport check-in event (student boarded or dropped off)"""
    from app.infrastructure.models.models import BusAttendance
    
    # Verify access to this route
    from app.infrastructure.models.models import BusRoute
    route_result = await db.execute(
        select(BusRoute).where(BusRoute.id == check_in.route_id)
    )
    route = route_result.scalar_one_or_none()
    
    if not route:
        raise HTTPException(status_code=404, detail="Güzergah bulunamadı")
    
    if tenant.branch_ids and route.branch_id not in tenant.branch_ids:
        raise HTTPException(status_code=403, detail="Bu güzergaha erişiminiz yok")
    
    # Create attendance record
    new_attendance = BusAttendance(
        route_id=check_in.route_id,
        student_id=check_in.student_id,
        event=check_in.event,
        timestamp=check_in.timestamp,
        recorded_by=current_user.id
    )
    
    db.add(new_attendance)
    await db.commit()
    await db.refresh(new_attendance)
    
    return success_response({
        "attendance_id": str(new_attendance.id),
        "route_id": str(new_attendance.route_id),
        "student_id": str(new_attendance.student_id),
        "event": new_attendance.event,
        "timestamp": new_attendance.timestamp.isoformat() if new_attendance.timestamp else None
    }, f"Öğrenci {check_in.event} olarak kaydedildi")


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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("canteen.manage"))
):
    """Get canteen wallet balance for a student"""
    from app.infrastructure.models.models import Student
    
    # Verify student access
    student_result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = student_result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Öğrenci bulunamadı")
    
    if tenant.branch_ids and student.branch_id not in tenant.branch_ids:
        raise HTTPException(status_code=403, detail="Bu öğrenciye erişiminiz yok")
    
    # This would get wallet balance from database
    # For now, returning mock data
    return success_response({
        "student_id": str(student.id),
        "student_name": f"{student.first_name} {student.last_name}",
        "balance": 150.00,  # Mock balance
        "currency": "TRY",
        "last_updated": datetime.utcnow().isoformat()
    })


@router.post("/canteen/wallet/{student_id}/top-up")
async def top_up_canteen_wallet(
    student_id: UUID,
    top_up: WalletTopUp,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("canteen.manage"))
):
    """Top up canteen wallet for a student"""
    from app.infrastructure.models.models import Student
    
    # Verify student access
    student_result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = student_result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Öğrenci bulunamadı")
    
    if tenant.branch_ids and student.branch_id not in tenant.branch_ids:
        raise HTTPException(status_code=403, detail="Bu öğrenciye erişiminiz yok")
    
    # This would create a wallet top-up transaction
    # For now, returning mock response
    return success_response({
        "student_id": str(student.id),
        "amount": top_up.amount,
        "payment_method": top_up.payment_method,
        "new_balance": 150.00 + top_up.amount,  # Mock calculation
        "transaction_id": str(UUID()),
        "timestamp": datetime.utcnow().isoformat()
    }, f"Cüzdana {top_up.amount} TL yüklendi")


@router.post("/canteen/transactions/sale")
async def create_canteen_sale(
    sale: CanteenSale,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("canteen.manage"))
):
    """Create a canteen sale transaction"""
    from app.infrastructure.models.models import Student
    
    # Verify student access
    student_result = await db.execute(
        select(Student).where(Student.id == sale.student_id)
    )
    student = student_result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Öğrenci bulunamadı")
    
    if tenant.branch_ids and student.branch_id not in tenant.branch_ids:
        raise HTTPException(status_code=403, detail="Bu öğrenciye erişiminiz yok")
    
    # Calculate total
    total_amount = sum(item.get("price", 0) * item.get("qty", 1) for item in sale.items)
    
    # This would create a sale transaction and update wallet
    # For now, returning mock response
    return success_response({
        "transaction_id": str(UUID()),
        "student_id": str(sale.student_id),
        "items": sale.items,
        "total_amount": total_amount,
        "remaining_balance": 150.00 - total_amount,  # Mock calculation
        "timestamp": datetime.utcnow().isoformat()
    }, f"Satış tamamlandı: {total_amount} TL")


# ==================== LIBRARY (KÜTÜPHANE) ENDPOINTS ====================

class LibraryBorrow(BaseModel):
    book_id: UUID
    student_id: UUID
    due_date: datetime


@router.get("/library/books")
async def get_library_books(
    search: Optional[str] = None,
    available_only: bool = False,
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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