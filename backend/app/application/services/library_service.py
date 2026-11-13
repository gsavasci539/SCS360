"""Persistent library operations shared by the web operational endpoints."""
from app.core.dates import school_today
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import String, cast, func, select, update

from app.core.exceptions import ConflictException, ValidationException
from app.core.student_access import require_student_access
from app.infrastructure.models.models import LibraryBook, LibraryLoan, Student
from app.infrastructure.repositories.base import BaseRepository
from app.application.services.operations_service import identifier


def book_dict(book):
    return {key: getattr(book, key) for key in (
        "title", "author", "category", "isbn", "barcode", "total_copies", "available_copies"
    )} | {"id": str(book.id)}


def detail_dict(book):
    return book_dict(book) | {
        'organization_id': str(book.organization_id),
        **{key: getattr(book, key) for key in ('publisher', 'publication_year', 'description', 'location')},
        'created_at': book.created_at.isoformat(), 'updated_at': book.updated_at.isoformat(),
    }


async def detail(db, tenant, book_id):
    return detail_dict(await BaseRepository(db, tenant).get_by_id(identifier(book_id), LibraryBook))


async def edit(db, tenant, book_id, body):
    book = await BaseRepository(db, tenant).get_by_id(identifier(book_id), LibraryBook, for_update=True)
    values = body.model_dump(exclude_unset=True)
    expected = values.pop('expected_updated_at', None)
    def utc(value):
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
    if expected is not None and utc(expected) != utc(book.updated_at):
        raise ConflictException('Kitap kaydı değişti; güncel kaydı yeniden açın')
    for key in ('title', 'author', 'total_copies', 'available_copies'):
        if key in values and values[key] is None:
            raise ValidationException('Kitap adı, yazar ve kopya alanları boş olamaz')
    # Inventory belongs to this already-authorized book, across all student scopes.
    loans = LibraryLoan.__table__
    active = (await db.execute(select(func.count()).select_from(loans).where(
        loans.c.book_id == book.id, loans.c.return_date.is_(None)))).scalar_one()
    if book.total_copies - book.available_copies != active:
        raise ConflictException('Kopya ve ödünç kayıtları uyuşmuyor; stok incelenmeli')
    total = values.get('total_copies', book.total_copies)
    if total < active:
        raise ConflictException('Toplam kopya sayısı ödünçteki kopyalardan az olamaz')
    available = total - active
    if 'available_copies' in values and values['available_copies'] != available:
        raise ConflictException('Mevcut kopya sayısı ödünç kayıtlarından hesaplanır')
    if not values:
        return detail_dict(book)
    version, loaded_at = (await db.execute(select(cast(LibraryBook.updated_at, String), LibraryBook.updated_at)
        .where(LibraryBook.id == book.id))).one()
    if utc(loaded_at) != utc(book.updated_at):
        raise ConflictException('Kitap eşzamanlı değişti; güncel kaydı yeniden açın')
    values.update(available_copies=available, updated_at=datetime.now(UTC))
    changed = await db.execute(update(LibraryBook).where(LibraryBook.id == book.id,
        cast(LibraryBook.updated_at, String) == version, LibraryBook.available_copies == book.available_copies,
        LibraryBook.total_copies == book.total_copies).values(**values).execution_options(synchronize_session=False))
    if changed.rowcount != 1:
        raise ConflictException('Kitap eşzamanlı değişti; güncel kaydı yeniden açın')
    await db.flush(); await db.refresh(book)
    return detail_dict(book)


async def delete(db, tenant, book_id):
    book = await BaseRepository(db, tenant).get_by_id(identifier(book_id), LibraryBook, for_update=True)
    loans = LibraryLoan.__table__
    if (await db.execute(select(loans.c.id).where(loans.c.book_id == book.id).limit(1))).first():
        raise ConflictException('Ödünç geçmişi olan kitap silinemez')
    key = str(book.id)
    await db.delete(book); await db.flush()
    return {'id': key, 'message': 'Kitap silindi'}


async def books(db, tenant, search=None, category=None, *, limit=100, offset=0, page=None, page_size=None, skip=None):
    repo = BaseRepository(db, tenant)
    query = repo._org_filter(select(LibraryBook), LibraryBook)
    filters = []
    if search:
        filters.append(LibraryBook.title.ilike(f"%{search}%") | LibraryBook.author.ilike(f"%{search}%") | LibraryBook.isbn.ilike(f"%{search}%"))
    if category:
        filters.append(LibraryBook.category == category)
    if filters:
        query = query.where(*filters)
    resolved_limit = page_size or limit
    resolved_offset = skip if skip is not None else ((page - 1) * resolved_limit if page is not None else offset)
    count_query = repo._org_filter(select(func.count(LibraryBook.id)), LibraryBook)
    if filters:
        count_query = count_query.where(*filters)
    total = (await db.execute(count_query)).scalar_one()
    rows = (await db.execute(query.order_by(LibraryBook.title, LibraryBook.author).limit(resolved_limit).offset(resolved_offset))).scalars().all()
    return {
        "items": [detail_dict(book) for book in rows],
        "total": total,
        "page": page or (resolved_offset // resolved_limit) + 1,
        "page_size": resolved_limit,
        "total_pages": (total + resolved_limit - 1) // resolved_limit,
    }


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
