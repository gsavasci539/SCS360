"""
Library Module API
Handles book catalog, borrowing, and returns
"""
from __future__ import annotations
from app.core.dates import school_today
from datetime import datetime, date
from typing import Optional, List
from uuid import UUID
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_tenant_context
from app.core.permissions import PermissionChecker
from app.core.responses import success_response
from app.domain.entities.user import User
from app.core.tenant import TenantContext
from app.infrastructure.repositories.base import BaseRepository

router = APIRouter(prefix="/api/library", tags=["Library"])


# ==================== Schemas ====================

class BookCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    author: str = Field(..., min_length=1, max_length=255)
    isbn: Optional[str] = Field(None, max_length=20)
    category: Optional[str] = None
    publisher: Optional[str] = None
    publication_year: Optional[int] = None
    total_copies: int = Field(default=1, ge=1)
    available_copies: int = Field(default=1, ge=0)
    description: Optional[str] = None
    location: Optional[str] = Field(None, description="Shelf location")


class BookUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    author: Optional[str] = Field(None, min_length=1, max_length=255)
    isbn: Optional[str] = Field(None, max_length=20)
    category: Optional[str] = None
    publisher: Optional[str] = None
    publication_year: Optional[int] = None
    total_copies: Optional[int] = Field(None, ge=1)
    available_copies: Optional[int] = Field(None, ge=0)
    description: Optional[str] = None
    location: Optional[str] = None


class BookBorrowCreate(BaseModel):
    book_id: UUID
    student_id: UUID
    due_date: date


# ==================== Book Catalog Endpoints ====================

@router.get("/books")
async def get_books(
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    author: Optional[str] = Query(None),
    isbn: Optional[str] = Query(None),
    is_available: Optional[bool] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("library.read"))
):
    """Get books with filtering and search"""
    from app.infrastructure.models.models import Book
    
    query = select(Book)
    
    conditions = []
    if search:
        conditions.append(
            (Book.title.ilike(f"%{search}%")) | 
            (Book.author.ilike(f"%{search}%")) |
            (Book.isbn.ilike(f"%{search}%"))
        )
    if category:
        conditions.append(Book.category == category)
    if author:
        conditions.append(Book.author.ilike(f"%{author}%"))
    if isbn:
        conditions.append(Book.isbn == isbn)
    if is_available is not None:
        conditions.append(Book.available_copies > 0 if is_available else Book.available_copies == 0)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(Book.title, Book.author).limit(limit).offset(offset)
    
    result = await db.execute(query)
    books = result.scalars().all()
    
    books_data = []
    for book in books:
        books_data.append({
            "id": str(book.id),
            "title": book.title,
            "author": book.author,
            "isbn": book.isbn,
            "category": book.category,
            "publisher": book.publisher,
            "publication_year": book.publication_year,
            "total_copies": book.total_copies,
            "available_copies": book.available_copies,
            "description": book.description,
            "location": book.location,
            "created_at": book.created_at.isoformat(),
            "updated_at": book.updated_at.isoformat()
        })
    
    return success_response(books_data)


@router.post("/books")
async def create_book(
    book_data: BookCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("library.write"))
):
    """Create a new book"""
    from app.infrastructure.models.models import Book
    
    new_book = Book(
        organization_id=tenant.organization_id,
        title=book_data.title,
        author=book_data.author,
        isbn=book_data.isbn,
        category=book_data.category,
        publisher=book_data.publisher,
        publication_year=book_data.publication_year,
        total_copies=book_data.total_copies,
        available_copies=book_data.available_copies,
        description=book_data.description,
        location=book_data.location
    )
    
    db.add(new_book)
    await db.commit()
    await db.refresh(new_book)
    
    return success_response({
        "id": str(new_book.id),
        "title": new_book.title,
        "author": new_book.author,
        "total_copies": new_book.total_copies,
        "available_copies": new_book.available_copies,
        "created_at": new_book.created_at.isoformat()
    }, "Kitap eklendi")


@router.get("/books/{book_id}")
async def get_book(
    book_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("library.read"))
):
    """Get book details"""
    from app.infrastructure.models.models import Book
    
    result = await db.execute(
        select(Book).where(Book.id == book_id)
    )
    book = await BaseRepository(db, tenant).get_by_id(book_id, Book)
    
    if not book:
        raise HTTPException(status_code=404, detail="Kitap bulunamadı")
    
    return success_response({
        "id": str(book.id),
        "title": book.title,
        "author": book.author,
        "isbn": book.isbn,
        "category": book.category,
        "publisher": book.publisher,
        "publication_year": book.publication_year,
        "total_copies": book.total_copies,
        "available_copies": book.available_copies,
        "description": book.description,
        "location": book.location,
        "created_at": book.created_at.isoformat(),
        "updated_at": book.updated_at.isoformat()
    })


@router.put("/books/{book_id}")
async def update_book(
    book_id: UUID,
    book_data: BookUpdate,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("library.write"))
):
    """Update book details"""
    from app.infrastructure.models.models import Book
    
    result = await db.execute(
        select(Book).where(Book.id == book_id)
    )
    book = await BaseRepository(db, tenant).get_by_id(book_id, Book)
    
    if not book:
        raise HTTPException(status_code=404, detail="Kitap bulunamadı")
    
    for field, value in book_data.model_dump(exclude_unset=True).items():
        setattr(book, field, value)
    
    book.updated_at = datetime.utcnow()
    await db.commit()
    
    return success_response({
        "id": str(book.id),
        "updated_at": book.updated_at.isoformat()
    }, "Kitap güncellendi")


@router.delete("/books/{book_id}")
async def delete_book(
    book_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("library.write"))
):
    """Delete a book"""
    from app.infrastructure.models.models import Book
    
    result = await db.execute(
        select(Book).where(Book.id == book_id)
    )
    book = await BaseRepository(db, tenant).get_by_id(book_id, Book)
    
    if not book:
        raise HTTPException(status_code=404, detail="Kitap bulunamadı")
    
    from app.infrastructure.models.models import BookLoan
    if (await db.execute(select(BookLoan.id).where(BookLoan.book_id == book.id).limit(1))).first():
        raise HTTPException(status_code=409, detail="Ödünç geçmişi olan kitap silinemez")
    await db.delete(book)
    await db.commit()
    
    return success_response({"message": "Kitap silindi"})


# ==================== Borrowing Endpoints ====================

@router.post("/borrow")
async def borrow_book(
    borrow_data: BookBorrowCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("library.manage"))
):
    """Borrow a book to a student"""
    from app.infrastructure.models.models import Book, BookLoan, Student
    
    # Check if book exists and is available
    book_result = await db.execute(
        select(Book).where(Book.id == borrow_data.book_id)
    )
    book = book_result.scalar_one_or_none()
    
    if not book:
        raise HTTPException(status_code=404, detail="Kitap bulunamadı")
    
    if book.available_copies <= 0:
        raise HTTPException(status_code=400, detail="Bu kitap şu anda mevcut değil")
    
    # Check if student exists
    student_result = await db.execute(
        select(Student).where(Student.id == borrow_data.student_id)
    )
    student = student_result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Öğrenci bulunamadı")
    
    # Check if student has already borrowed this book and not returned
    existing_loan_result = await db.execute(
        select(BookLoan).where(
            and_(
                BookLoan.book_id == borrow_data.book_id,
                BookLoan.student_id == borrow_data.student_id,
                BookLoan.return_date.is_(None)
            )
        )
    )
    
    if existing_loan_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Öğrenci bu kitabı zaten ödünç almış")
    
    # Create loan record
    new_loan = BookLoan(
        book_id=borrow_data.book_id,
        student_id=borrow_data.student_id,
        borrow_date=school_today(),
        due_date=borrow_data.due_date,
        loaned_by=current_user.id
    )
    
    # Update available copies
    book.available_copies -= 1
    
    db.add(new_loan)
    await db.commit()
    await db.refresh(new_loan)
    
    return success_response({
        "loan_id": str(new_loan.id),
        "book_id": str(new_loan.book_id),
        "student_id": str(new_loan.student_id),
        "borrow_date": new_loan.borrow_date.isoformat(),
        "due_date": new_loan.due_date.isoformat(),
        "available_copies": book.available_copies
    }, "Kitap ödünç verildi")


@router.post("/return/{loan_id}")
async def return_book(
    loan_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("library.manage"))
):
    """Return a borrowed book"""
    from app.infrastructure.models.models import BookLoan, Book
    
    result = await db.execute(
        select(BookLoan).where(BookLoan.id == loan_id)
    )
    loan = result.scalar_one_or_none()
    
    if not loan:
        raise HTTPException(status_code=404, detail="Ödünç kaydı bulunamadı")
    
    if loan.return_date:
        raise HTTPException(status_code=400, detail="Bu kitap zaten iade edilmiş")
    
    # Update loan record
    loan.return_date = school_today()
    loan.returned_by = current_user.id
    
    # Update book available copies
    book_result = await db.execute(
        select(Book).where(Book.id == loan.book_id)
    )
    book = book_result.scalar_one_or_none()
    
    if book:
        book.available_copies += 1
    
    await db.commit()
    
    return success_response({
        "loan_id": str(loan.id),
        "return_date": loan.return_date.isoformat(),
        "available_copies": book.available_copies if book else 0
    }, "Kitap iade alındı")


@router.get("/loans")
async def get_loans(
    student_id: Optional[UUID] = Query(None),
    book_id: Optional[UUID] = Query(None),
    is_overdue: Optional[bool] = Query(None),
    is_active: Optional[bool] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("library.read"))
):
    """Get book loans with filtering"""
    from app.infrastructure.models.models import BookLoan, Book, Student
    
    query = select(BookLoan)
    
    conditions = []
    if student_id:
        conditions.append(BookLoan.student_id == student_id)
    if book_id:
        conditions.append(BookLoan.book_id == book_id)
    if is_active is not None:
        if is_active:
            conditions.append(BookLoan.return_date.is_(None))
        else:
            conditions.append(BookLoan.return_date.isnot(None))
    if is_overdue is not None and is_overdue:
        conditions.append(
            and_(
                BookLoan.return_date.is_(None),
                BookLoan.due_date < school_today()
            )
        )
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(BookLoan.borrow_date.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    loans = result.scalars().all()
    
    loans_data = []
    for loan in loans:
        # Get book details
        book_result = await db.execute(
            select(Book).where(Book.id == loan.book_id)
        )
        book = book_result.scalar_one_or_none()
        
        # Get student details
        student_result = await db.execute(
            select(Student).where(Student.id == loan.student_id)
        )
        student = student_result.scalar_one_or_none()
        
        # Calculate if overdue
        is_loan_overdue = loan.return_date is None and loan.due_date < school_today()
        days_overdue = (school_today() - loan.due_date).days if is_loan_overdue else 0
        
        loans_data.append({
            "id": str(loan.id),
            "book_id": str(loan.book_id),
            "book_title": book.title if book else None,
            "book_author": book.author if book else None,
            "student_id": str(loan.student_id),
            "student_name": f"{student.first_name} {student.last_name}" if student else None,
            "borrow_date": loan.borrow_date.isoformat(),
            "due_date": loan.due_date.isoformat(),
            "return_date": loan.return_date.isoformat() if loan.return_date else None,
            "is_overdue": is_loan_overdue,
            "days_overdue": days_overdue,
            "loaned_by": str(loan.loaned_by) if loan.loaned_by else None,
            "returned_by": str(loan.returned_by) if loan.returned_by else None,
            "created_at": loan.created_at.isoformat()
        })
    
    return success_response(loans_data)


@router.get("/loans/overdue")
async def get_overdue_loans(
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("library.read"))
):
    """Get all overdue loans"""
    from app.infrastructure.models.models import BookLoan, Book, Student
    
    result = await db.execute(
        select(BookLoan).where(
            and_(
                BookLoan.return_date.is_(None),
                BookLoan.due_date < school_today()
            )
        ).order_by(BookLoan.due_date).limit(limit)
    )
    loans = result.scalars().all()
    
    overdue_loans = []
    for loan in loans:
        # Get book details
        book_result = await db.execute(
            select(Book).where(Book.id == loan.book_id)
        )
        book = book_result.scalar_one_or_none()
        
        # Get student details
        student_result = await db.execute(
            select(Student).where(Student.id == loan.student_id)
        )
        student = student_result.scalar_one_or_none()
        
        days_overdue = (school_today() - loan.due_date).days
        
        overdue_loans.append({
            "id": str(loan.id),
            "book_id": str(loan.book_id),
            "book_title": book.title if book else None,
            "student_id": str(loan.student_id),
            "student_name": f"{student.first_name} {student.last_name}" if student else None,
            "borrow_date": loan.borrow_date.isoformat(),
            "due_date": loan.due_date.isoformat(),
            "days_overdue": days_overdue
        })
    
    return success_response({
        "total": len(overdue_loans),
        "loans": overdue_loans
    })
