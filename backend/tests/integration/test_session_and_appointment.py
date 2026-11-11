from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
import sqlite3
import os
import subprocess
import sys
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.application.services.auth_service import AuthService
from app.application.schemas.common import AppointmentCreate, AppointmentStatusUpdate
from app.application.services import appointment_service
from app.core.exceptions import ConflictException
from app.core.security import hash_token, verify_access_token
from app.core.tenant import TenantContext
from app.infrastructure.models.models import Appointment, Student, User, UserStatus, RefreshToken


@pytest.fixture
async def isolated_sessions(tmp_path):
    source = Path(__file__).resolve().parents[2] / "school_management.db"
    if not source.exists():
        pytest.skip("Local fixture database not available")
    snapshot = tmp_path / "business.db"
    with closing(sqlite3.connect(f"file:{source}?mode=ro", uri=True)) as original:
        with closing(sqlite3.connect(snapshot)) as target:
            original.backup(target)
    # A copied developer database may be one release behind. Exercise the real
    # migration on the temporary clone, never on the user's working database.
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=source.parent,
        env={**os.environ, "DATABASE_URL": f"sqlite+aiosqlite:///{snapshot.as_posix()}", "SEED_DEMO_DATA": "false",
            "NOTIFICATION_DELIVERY_ENABLED": "false"}, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    engine = create_async_engine(f"sqlite+aiosqlite:///{snapshot.as_posix()}")
    async with engine.begin() as connection:
        await connection.run_sync(lambda conn: Appointment.__table__.create(conn, checkfirst=True))
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_refresh_after_sqlite_reload_rotates_token(isolated_sessions):
    value = str(uuid4())
    async with isolated_sessions() as db:
        user = (await db.execute(select(User).where(User.status == UserStatus.ACTIVE, User.deleted_at.is_(None)))).scalars().first()
        if user is None:
            pytest.skip("Active user fixture not available")
        user_id = user.id
        db.add(RefreshToken(user_id=user_id, token_hash=hash_token(value), family_id=uuid4(),
            expires_at=datetime.now(UTC) + timedelta(hours=1)))
        await db.commit()
    async with isolated_sessions() as db:
        refreshed = await AuthService(db).refresh(value, None, None)
        assert verify_access_token(refreshed["access_token"])["sub"] == str(user_id)
        assert refreshed["refresh_token"] != value
        await db.commit()
    async with isolated_sessions() as db:
        token = (await db.execute(select(RefreshToken).where(RefreshToken.token_hash == hash_token(value)))).scalar_one()
        assert token.revoked_at is not None


@pytest.mark.asyncio
async def test_appointment_persists_conflict_is_rejected_and_status_updates(isolated_sessions):
    async with isolated_sessions() as db:
        student = (await db.execute(select(Student).where(Student.deleted_at.is_(None)))).scalars().first()
        user = (await db.execute(select(User).where(User.deleted_at.is_(None)))).scalars().first()
        if student is None or user is None:
            pytest.skip("Fixture student/user unavailable")
        tenant = TenantContext(user_id=user.id, organization_id=student.organization_id, is_super_admin=True)
        body = AppointmentCreate(teacher_id=str(user.id), student_id=str(student.id),
            slot_datetime=datetime.now(UTC) + timedelta(days=30), duration_minutes=30)
        created = await appointment_service.create(db, tenant, body)
        await db.commit()
    async with isolated_sessions() as db:
        rows = await appointment_service.records(db, tenant)
        assert any(row["id"] == created["id"] for row in rows)
        with pytest.raises(ConflictException):
            await appointment_service.create(db, tenant, body)
        await db.rollback()
        await appointment_service.update_status(db, tenant, created["id"], AppointmentStatusUpdate(status="COMPLETED"))
        await db.commit()


@pytest.mark.asyncio
async def test_authorized_student_debt_payment_and_cancellation_http_lifecycle(isolated_sessions):
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.core.database import get_db
    from app.core.security import create_access_token
    from app.infrastructure.models.models import Branch, Organization

    async with isolated_sessions() as db:
        user = (await db.execute(select(User).where(User.is_super_admin.is_(True), User.deleted_at.is_(None)))).scalars().first()
        if user is None:
            pytest.skip("Admin fixture unavailable")
        organization = Organization(name="Lifecycle acceptance " + uuid4().hex)
        db.add(organization)
        await db.flush()
        branch = Branch(organization_id=organization.id, name="Lifecycle acceptance branch")
        db.add(branch)
        await db.commit()
        token = create_access_token(user.id)
        organization_id, branch_id = str(branch.organization_id), str(branch.id)

    async def copied_database():
        async with isolated_sessions() as db:
            try:
                yield db
                await db.commit()
            except Exception:
                await db.rollback()
                raise

    overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = copied_database
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test",
                               headers={"Authorization": f"Bearer {token}",
                                   "X-SCS360-Organization-Id": organization_id}) as client:
            async def request(method, path, payload=None):
                response = await client.request(method, path, json=payload)
                assert response.status_code < 400, f"{method} {path}: {response.status_code} {response.text[:500]}"
                return response.json().get("data")

            tag = uuid4().hex[:8]
            classroom = await request("POST", "/api/classes", {"organization_id": organization_id,
                "branch_id": branch_id, "name": f"Test {tag}", "code": tag, "capacity": 10})
            student = await request("POST", "/api/students", {"organization_id": organization_id,
                "branch_id": branch_id, "class_id": classroom["id"], "student_number": tag,
                "first_name": "Test", "last_name": "Student", "gender": "MALE", "date_of_birth": "2020-01-01"})
            await request("GET", f"/api/students/{student['id']}")
            parent = await request("POST", "/api/parents", {"organization_id": organization_id, "first_name": "Test", "last_name": "Parent", "phone": "05000000000"})
            await request("POST", f"/api/students/{student['id']}/parents", {"parent_id": parent["id"], "is_primary": True})
            debt = await request("POST", "/api/debts", {"student_id": student["id"], "debt_type": "EDUCATION",
                "amount": "500.00", "due_date": "2027-01-01"})
            payment = await request("POST", "/api/payments", {"debt_id": debt["id"], "amount": "100.00", "payment_method": "CASH"})
            await request("GET", f"/api/payments/{payment['payment_id']}")
            await request("GET", f"/api/receipts/{payment['receipt_id']}")
            await request("POST", f"/api/payments/{payment['payment_id']}/cancel", {"cancel_reason": "Test rollback"})
            remaining = await request("GET", f"/api/debts/{debt['id']}")
            assert float(remaining["paid_amount"]) == 0
            expense = await request("POST", "/api/finance/expenses", {
                "description": "Lifecycle expense", "category": "OTHER", "amount": 10, "expense_date": "",
            })
            await request("GET", f"/api/finance/expenses/{expense['id']}")
            await request("PUT", f"/api/finance/expenses/{expense['id']}", {"amount": 15})
            await request("DELETE", f"/api/finance/expenses/{expense['id']}")
            for report in ("monthly-payments", "debts", "overdue-debts", "attendance", "class-occupancy", "branch-performance"):
                exported = await request("GET", f"/api/reports/export/csv?report_type={report}&year=2026&month=11")
                assert exported["filename"] == f"{report}.csv"
            await request("DELETE", f"/api/students/{student['id']}")
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides)
