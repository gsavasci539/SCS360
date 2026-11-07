"""Persistent library operations shared by the web operational endpoints."""
from app.core.dates import school_today
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import select, update

from app.core.exceptions import ConflictException, ValidationException
from app.core.student_access import require_student_access
from app.infrastructure.models.models import LibraryBook, LibraryLoan, Student
from app.infrastructure.repositories.base import BaseRepository
from app.application.services.operations_service import identifier


def book_dict(book):
    return {key: getattr(book, key) for key in (
        "title", "author", "category", "isbn", "barcode", "total_copies", "available_copies"
    )} | {"id": str(book.id)}


async def books(db, tenant, search=None, category=None):
    repo = BaseRepository(db, tenant)
    query = repo._org_filter(select(LibraryBook), LibraryBook)
    if search:
        query = query.where(LibraryBook.title.ilike(f"%{search}%") | LibraryBook.author.ilike(f"%{search}%"))
    if category:
        query = query.where(LibraryBook.category == category)
    return [book_dict(book) for book in (await db.execute(query.order_by(LibraryBook.title))).scalars()]


async def create_book(db, tenant, body):
    if not tenant.organization_id:
        raise ValidationException("Kitap eklemek için kurum seçin")
    if body.total_copies < 1:
        raise ValidationException("Kopya sayısı en az 1 olmalıdır")
    book = LibraryBook(**body.model_dump(), organization_id=tenant.organization_id, available_copies=body.total_copies)
    db.add(book)
    await db.flush()
    return book_dict(book)


async def loans(db, tenant, status=None):
    repo = BaseRepository(db, tenant)
    query = select(LibraryLoan, LibraryBook, Student).join(LibraryBook, LibraryBook.id == LibraryLoan.book_id).join(Student, Student.id == LibraryLoan.student_id)
    query = repo._branch_filter(repo._org_filter(query, LibraryBook), Student)
    if status == "RETURNED":
        query = query.where(LibraryLoan.return_date.is_not(None))
    elif status in {"BORROWED", "OVERDUE"}:
        query = query.where(LibraryLoan.return_date.is_(None))
        if status == "OVERDUE":
            query = query.where(LibraryLoan.due_date < school_today())
    rows = (await db.execute(query.order_by(LibraryLoan.borrow_date.desc()))).all()
    return [{
        "id": str(loan.id), "book_id": str(book.id), "book_title": book.title,
        "student_id": str(student.id), "student_name": f"{student.first_name} {student.last_name}",
        "student_number": student.student_number, "borrow_date": loan.borrow_date.isoformat(),
        "due_date": loan.due_date.isoformat(), "return_date": loan.return_date.isoformat() if loan.return_date else None,
        "status": "RETURNED" if loan.return_date else ("OVERDUE" if loan.due_date < school_today() else "BORROWED"),
        "fine_amount": 0,
    } for loan, book, student in rows]


async def borrow(db, tenant, body):
    repo = BaseRepository(db, tenant)
    book = await repo.get_by_id(identifier(body.book_id), LibraryBook, for_update=True)
    student = await repo.get_by_id(identifier(body.student_id), Student)
    await require_student_access(db, tenant, student.id)
    if not 1 <= body.duration_days <= 365:
        raise ValidationException("Ödünç süresi 1–365 gün olmalıdır")
    changed = await db.execute(update(LibraryBook).where(
        LibraryBook.id == book.id, LibraryBook.available_copies > 0
    ).values(available_copies=LibraryBook.available_copies - 1))
    if changed.rowcount != 1:
        raise ConflictException("Kitabın uygun kopyası bulunmamaktadır")
    loan = LibraryLoan(book_id=book.id, student_id=student.id, borrow_date=school_today(),
        due_date=school_today() + timedelta(days=body.duration_days), loaned_by=tenant.user_id)
    db.add(loan)
    await db.flush()
    return {"id": str(loan.id), "book_title": book.title, "due_date": loan.due_date.isoformat(), "status": "BORROWED"}


async def return_book(db, tenant, loan_id):
    from app.core.exceptions import NotFoundException
    loan = (await db.execute(select(LibraryLoan).where(LibraryLoan.id == identifier(loan_id)).with_for_update())).scalar_one_or_none()
    if not loan:
        raise NotFoundException("Ödünç kaydı bulunamadı")
    repo = BaseRepository(db, tenant)
    await repo.get_by_id(loan.book_id, LibraryBook)
    await repo.get_by_id(loan.student_id, Student)
    changed = await db.execute(update(LibraryLoan).where(
        LibraryLoan.id == loan.id, LibraryLoan.return_date.is_(None)
    ).values(return_date=school_today(), returned_by=tenant.user_id))
    if changed.rowcount != 1:
        raise ConflictException("Bu kitap zaten iade edilmiş")
    await db.execute(update(LibraryBook).where(LibraryBook.id == loan.book_id)
        .values(available_copies=LibraryBook.available_copies + 1))
    return {"id": str(loan.id), "status": "RETURNED"}
