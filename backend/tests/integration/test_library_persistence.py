"""Run library lifecycle only on a disposable copy of the local test database."""
from contextlib import closing
from pathlib import Path
import sqlite3
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.application.schemas.common import LibraryBookCreate, LibraryBorrowRequest
from app.application.services import library_service
from app.core.exceptions import ConflictException
from app.core.tenant import TenantContext
from app.infrastructure.models.models import LibraryBook, LibraryLoan, Student, User


@pytest.mark.asyncio
async def test_library_create_borrow_return_is_persistent_and_return_is_not_repeated(tmp_path, monkeypatch):
    from datetime import date
    day = date(2027, 1, 4)
    monkeypatch.setattr(library_service, "school_today", lambda: day)
    source = Path(__file__).resolve().parents[2] / "school_management.db"
    if not source.exists():
        pytest.skip("Local fixture database is not available")
    snapshot = tmp_path / "library.db"
    with closing(sqlite3.connect(f"file:{source}?mode=ro", uri=True)) as original:
        with closing(sqlite3.connect(snapshot)) as target:
            original.backup(target)
    engine = create_async_engine(f"sqlite+aiosqlite:///{snapshot.as_posix()}")
    async with engine.begin() as connection:
        await connection.run_sync(lambda conn: LibraryBook.__table__.create(conn, checkfirst=True))
        await connection.run_sync(lambda conn: LibraryLoan.__table__.create(conn, checkfirst=True))
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as db:
            student = (await db.execute(select(Student).where(Student.deleted_at.is_(None)).limit(1))).scalars().first()
            user = (await db.execute(select(User).limit(1))).scalars().first()
            if student is None or user is None:
                pytest.skip("Student/user fixture is not available")
            tenant = TenantContext(user_id=user.id, organization_id=student.organization_id, is_super_admin=True)
            created = await library_service.create_book(db, tenant, LibraryBookCreate(
                title=f"Lifecycle {uuid4()}", author="Test", category="Test", total_copies=1,
            ))
            body = LibraryBorrowRequest(book_id=created["id"], student_id=str(student.id),
                student_name="untrusted", student_number="untrusted", class_name="untrusted", duration_days=14)
            loan = await library_service.borrow(db, tenant, body)
            await db.commit()
        async with sessions() as db:
            rows = await library_service.loans(db, tenant)
            saved = next(row for row in rows if row["id"] == loan["id"])
            assert saved["student_name"] != "untrusted"
            assert saved["status"] == "BORROWED"
            assert saved["borrow_date"] == day.isoformat() and saved["due_date"] == "2027-01-18"
            await library_service.return_book(db, tenant, loan["id"])
            await db.commit()
        async with sessions() as db:
            with pytest.raises(ConflictException):
                await library_service.return_book(db, tenant, loan["id"])
            await db.rollback()
            book = await db.get(LibraryBook, created["id"])
            assert book.available_copies == 1
            returned = await db.get(LibraryLoan, loan["id"])
            assert returned.return_date == day
    finally:
        await engine.dispose()
