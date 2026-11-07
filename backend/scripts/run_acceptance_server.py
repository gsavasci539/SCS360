"""Disposable browser acceptance server. Never connects to the working database."""
import asyncio
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


async def seed():
    from sqlalchemy import select, update
    from app.core.database import AsyncSessionLocal, engine
    from app.core.security import hash_password
    from app.infrastructure.models.models import (Organization, Branch, User, Role, Permission, ClassRoom,
        Student, Parent, StudentParent, Grade, GradeType, SubjectType, Announcement, AnnouncementStatus, AnnouncementAudience)
    from datetime import date
    async with AsyncSessionLocal() as db:
        for name in ("admin", "parent", "teacher"):
            await db.execute(update(User).where(User.email == f"{name}@acceptance.invalid")
                .values(email=f"{name}@acceptance.example.com"))
        await db.commit()
        if (await db.execute(select(User.id).where(User.email == "admin@acceptance.example.com"))).first():
            from sqlalchemy.orm import selectinload
            from app.infrastructure.models.models import UserRole
            role = (await db.execute(select(Role).options(selectinload(Role.permissions))
                .join(UserRole, UserRole.role_id == Role.id).join(User, User.id == UserRole.user_id)
                .where(Role.slug == "teacher", User.email == "teacher@acceptance.example.com"))).scalar_one()
            existing_codes = {permission.code for permission in role.permissions}
            for code in ("messaging.read", "messaging.send"):
                if code not in existing_codes:
                    permission = (await db.execute(select(Permission).where(Permission.code == code))).scalar_one()
                    role.permissions.append(permission)
            parent_role = (await db.execute(select(Role).options(selectinload(Role.permissions))
                .join(UserRole, UserRole.role_id == Role.id).join(User, User.id == UserRole.user_id)
                .where(Role.slug == "parent", User.email == "parent@acceptance.example.com"))).scalar_one()
            if "parent.send_excuse" not in {permission.code for permission in parent_role.permissions}:
                parent_role.permissions.append((await db.execute(select(Permission).where(Permission.code == "parent.send_excuse"))).scalar_one())
            await db.commit()
            await db.close()
            await engine.dispose()
            return
        org = Organization(name="Kabul Test Okulu")
        db.add(org); await db.flush()
        branch = Branch(organization_id=org.id, name="Test Şubesi")
        db.add(branch); await db.flush()
        codes = ("parent.view_children", "parent.give_consent", "parent.respond_survey", "parent.view_attendance", "parent.view_finance", "parent.make_payment", "parent.send_excuse",
            "parent.medicine_request", "parent.send_message", "homework.read", "homework.write", "daily_reports.read",
            "daily_reports.write", "academic.read", "academic.write", "teacher.view_classes", "teacher.view_students",
            "teacher.view_attendance", "teacher.mark_attendance", "teacher.daily_report", "teacher.send_message", "students.read",
            "messaging.read", "messaging.send", "surveys.respond", "tutoring.read", "tutoring.write")
        existing = {row.code: row for row in (await db.execute(select(Permission))).scalars()}
        permissions = {code: existing.get(code) or Permission(code=code, name=code, module=code.split('.')[0]) for code in codes}
        parent_role = Role(name="Veli", slug="parent", organization_id=org.id,
            permissions=[permission for code, permission in permissions.items() if code.startswith("parent.")])
        teacher_role = Role(name="Öğretmen", slug="teacher", organization_id=org.id,
            permissions=[permission for code, permission in permissions.items() if not code.startswith("parent.")])
        users = {}
        for name, role in (("admin", None), ("parent", parent_role), ("teacher", teacher_role)):
            users[name] = User(organization_id=org.id, email=f"{name}@acceptance.example.com", first_name=name.capitalize(),
                last_name="Kabul", password_hash=hash_password("Acceptance-Only-2026!"),
                is_super_admin=name == "admin", roles=[role] if role else [], branches=[branch])
        db.add_all(users.values()); await db.flush()
        classroom = ClassRoom(organization_id=org.id, branch_id=branch.id, name="Kabul Sınıfı", teacher_id=users["teacher"].id)
        db.add(classroom); await db.flush()
        child = Student(organization_id=org.id, branch_id=branch.id, class_id=classroom.id,
            student_number="KABUL-001", first_name="Deniz", last_name="Kabul")
        parent = Parent(organization_id=org.id, user_id=users["parent"].id, first_name="Parent", last_name="Kabul")
        db.add_all([child, parent]); await db.flush()
        db.add(StudentParent(student_id=child.id, parent_id=parent.id))
        db.add(Grade(organization_id=org.id, branch_id=branch.id, class_id=classroom.id,
            student_id=child.id, subject=SubjectType.MATHEMATICS, grade_type=GradeType.EXAM, score=87, max_score=100, exam_date=date.today()))
        db.add(Announcement(organization_id=org.id, title="Gerçek Kabul Duyurusu", content="Veritabanından gelen test duyurusu",
            audience=AnnouncementAudience.ALL_PARENTS, status=AnnouncementStatus.SENT, channels=["EMAIL"], created_by=users["admin"].id))
        finance_permissions = [existing.get(code) or Permission(code=code, name=code, module="finance")
            for code in ("finance.read", "finance.write", "dashboard.read")]
        finance_role = Role(organization_id=org.id, name="Kabul Muhasebe", slug="accountant", permissions=finance_permissions)
        db.add(User(organization_id=org.id, email="accountant@acceptance.example.com", first_name="Muhasebe", last_name="Kabul",
            password_hash=hash_password("Acceptance-Only-2026!"), roles=[finance_role], branches=[branch]))
        await db.commit()
    await engine.dispose()


@contextmanager
def acceptance_database(folder):
    configured = os.getenv("ACCEPTANCE_DATABASE_URL")
    if not configured:
        yield f"sqlite+aiosqlite:///{Path(folder).as_posix()}/acceptance.db"
        return
    from sqlalchemy import text
    from sqlalchemy.engine import make_url
    from sqlalchemy.ext.asyncio import create_async_engine
    source = make_url(configured)
    if source.drivername != "postgresql+asyncpg" or not (source.database or "").startswith("scs360_acceptance"):
        raise RuntimeError("Only a disposable scs360_acceptance PostgreSQL database is allowed")
    # Every browser run gets its own database and private volume. The configured
    # database is only a connection source; never migrate, clear or drop it here.
    name = "scs360_acceptance_browser_" + uuid4().hex
    async def command(statement):
        connection_engine = create_async_engine(source, isolation_level="AUTOCOMMIT")
        try:
            async with connection_engine.connect() as connection:
                await connection.execute(text(statement))
        finally:
            await connection_engine.dispose()
    record = Path(os.environ["SCS360_ACCEPTANCE_RECORD"]).resolve() if os.getenv("SCS360_ACCEPTANCE_RECORD") else None
    if record and (record.parent != (ROOT.parent / ".codex-build").resolve()
        or not re.fullmatch(r"acceptance-[0-9a-f-]+\.json", record.name)):
        raise RuntimeError("The acceptance record must stay inside the workspace build directory")
    asyncio.run(command(f'CREATE DATABASE "{name}"'))
    try:
        if record:
            record.parent.mkdir(parents=True, exist_ok=True)
            record.write_text(json.dumps({"database": name, "source_database": source.database,
                "host": source.host, "port": source.port, "username": source.username}), encoding="utf-8")
        yield source.set(database=name).render_as_string(hide_password=False)
    finally:
        asyncio.run(command(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        if record:
            record.unlink(missing_ok=True)


def main():
    with tempfile.TemporaryDirectory(prefix="scs360-acceptance-", ignore_cleanup_errors=True) as folder, acceptance_database(folder) as database_url:
        os.environ["APP_ENV"] = "test"
        os.environ["DATABASE_URL"] = database_url
        os.environ["JWT_SECRET_KEY"] = "AcceptanceOnlySecretForBrowserTests20261102"
        os.environ["CORS_ORIGINS"] = "http://127.0.0.1:5176"
        os.environ["CHATBOT_LLM_PROVIDER"] = "mock"
        os.environ["SEED_DEMO_DATA"] = "false"
        os.environ["NOTIFICATION_DELIVERY_ENABLED"] = "false"
        os.environ["PRIVATE_UPLOAD_DIR"] = str(Path(folder) / "private_uploads")
        subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=ROOT, check=True, env=os.environ)
        asyncio.run(seed())
        from app.main import app
        from app.core.rate_limit import limiter
        # Each browser scenario has its own login budget, like each temporary
        # API fixture. The normal 5/minute rule remains active within a test.
        # This runner only creates disposable databases and binds loopback.
        @app.post("/api/__acceptance/reset-limits", include_in_schema=False)
        async def reset_acceptance_limits():
            limiter.reset()
            return {"ok": True}
        if os.getenv("SCS360_ACCEPTANCE_SAAS_GATEWAY") == "1":
            from acceptance_saas_gateway import install
            install(app)
        if os.getenv("SCS360_ACCEPTANCE_SCHOOL_GATEWAY") == "1":
            from acceptance_school_gateway import install as install_school_gateway
            asyncio.run(install_school_gateway())
        import uvicorn
        uvicorn.run(app, host="127.0.0.1", port=5016)


if __name__ == "__main__":
    main()
