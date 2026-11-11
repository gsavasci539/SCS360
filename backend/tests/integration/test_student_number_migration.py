"""037 must preserve children and fail atomically on uncertainty."""
# ruff: noqa: F811 -- imported pytest fixture injection.
import hashlib
import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker
from test_timetable_actor_migration import actor_db  # noqa: F401

from alembic.migration import MigrationContext
from alembic.operations import Operations
from app.core.database import Base
from app.infrastructure.models.models import (
    Branch,
    Debt,
    DebtType,
    Organization,
    Parent,
    Student,
    StudentParent,
    User,
)


def migration():
    root = Path(__file__).resolve().parents[3]
    path = root / "backend/alembic/versions/037_live_student_numbers.py"
    spec = importlib.util.spec_from_file_location("student_number_migration_037", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.revision == "037" and module.down_revision == "036"
    return module


@pytest.fixture
async def number_db(actor_db):
    async with actor_db.begin() as db:
        if actor_db.dialect.name == "sqlite":
            old = (Path(__file__).resolve().parents[1] / "fixtures/student_036.sqlite.sql").read_text(encoding="utf-8")
            assert hashlib.sha256(old.encode()).hexdigest() == "53a3fc7e2feaa3256dbdf358b230bfe033283b623b4fd188d49bb519551e5ee3"
            await db.exec_driver_sql(old)
        await db.run_sync(Base.metadata.create_all)
        if actor_db.dialect.name == "postgresql":
            await db.exec_driver_sql("DROP INDEX IF EXISTS uq_students_org_student_number_live")
            def old_constraint(connection):
                return [c for c in sa.inspect(connection).get_unique_constraints("students")
                    if c["column_names"] == ["organization_id", "student_number"]]
            if not await db.run_sync(old_constraint):
                await db.exec_driver_sql("ALTER TABLE students ADD CONSTRAINT uq_students_legacy_number UNIQUE(organization_id, student_number)")
        else:
            await db.exec_driver_sql("CREATE INDEX student_preserved_name ON students(last_name)")
            await db.exec_driver_sql("CREATE TABLE student_probe_audit(note TEXT)")
            await db.exec_driver_sql("CREATE TRIGGER student_preserved_trigger AFTER UPDATE ON students BEGIN INSERT INTO student_probe_audit VALUES ('changed'); END")
    sessions = async_sessionmaker(actor_db, expire_on_commit=False)
    async with sessions() as db:
        org = Organization(name="Disposable number policy")
        db.add(org)
        await db.flush()
        branch = Branch(name="School", organization_id=org.id)
        user = User(organization_id=org.id, email="number@test.invalid", password_hash="acceptance-inert-hash", first_name="Test", last_name="User")
        db.add_all([branch, user])
        await db.flush()
        archived = Student(organization_id=org.id, branch_id=branch.id, student_number="REUSE", first_name="Archive", last_name="History", deleted_at=datetime(2025, 1, 1, tzinfo=UTC))
        live = Student(organization_id=org.id, branch_id=branch.id, student_number="OTHER", first_name="Live", last_name="Record")
        parent = Parent(organization_id=org.id, user_id=user.id, first_name="Test", last_name="Parent")
        db.add_all([archived, live, parent])
        await db.flush()
        db.add_all([StudentParent(student_id=archived.id, parent_id=parent.id), StudentParent(student_id=live.id, parent_id=parent.id),
            Debt(organization_id=org.id, branch_id=branch.id, student_id=archived.id, debt_type=DebtType.EDUCATION, amount=10, paid_amount=0, due_date=datetime(2026, 1, 1).date())])
        await db.commit()
    return actor_db, {"archived": archived, "live": live, "org": org}


def snapshot(connection):
    result = {}
    for table in sa.inspect(connection).get_table_names():
        rows = connection.exec_driver_sql('SELECT * FROM "' + table + '"').all()
        result[table] = sorted(json.dumps(list(row), default=str, ensure_ascii=True) for row in rows)
    return result


async def run_upgrade(engine, module):
    async with engine.connect() as db:
        def migrate(connection):
            context = MigrationContext.configure(connection)
            with context.begin_transaction(_per_migration=True), Operations.context(context):
                module.upgrade()
        await db.run_sync(migrate)
        await db.commit()
        if engine.dialect.name == "sqlite":
            assert (await db.exec_driver_sql("PRAGMA foreign_keys")).scalar_one() == 1


async def test_upgrade_preserves_all_rows_relations_indexes_triggers_and_is_idempotent(number_db):
    engine, data = number_db
    module = migration()
    async with engine.connect() as db:
        before = await db.run_sync(snapshot)
    await run_upgrade(engine, module)
    await run_upgrade(engine, module)
    async with engine.connect() as db:
        assert await db.run_sync(snapshot) == before
        if engine.dialect.name == "sqlite":
            names = (await db.exec_driver_sql("SELECT name FROM sqlite_master WHERE name LIKE 'student_preserved_%'")).scalars().all()
            assert set(names) == {"student_preserved_name", "student_preserved_trigger"}
    async with engine.begin() as db:
        await db.execute(sa.text("UPDATE students SET student_number='REUSE' WHERE id=:id"), {"id": str(data["live"].id) if engine.dialect.name == "sqlite" else data["live"].id})
    with pytest.raises(IntegrityError):
        async with engine.begin() as db:
            await db.execute(sa.text("UPDATE students SET deleted_at=NULL WHERE id=:id"), {"id": str(data["archived"].id) if engine.dialect.name == "sqlite" else data["archived"].id})
    async with engine.connect() as db:
        assert (await db.exec_driver_sql("SELECT count(*) FROM student_parents")).scalar_one() == 2
        assert (await db.exec_driver_sql("SELECT count(*) FROM debts")).scalar_one() == 1


@pytest.mark.parametrize("actor_db", ["sqlite"], indirect=True)
async def test_unknown_sqlite_schema_fails_without_changes_and_restores_fk_mode(number_db):
    engine, _ = number_db
    module = migration()
    async with engine.begin() as db:
        await db.exec_driver_sql("ALTER TABLE students ADD COLUMN unreviewed TEXT")
    async with engine.connect() as db:
        before = await db.run_sync(snapshot)
        schema = await db.run_sync(module.objects)
    with pytest.raises(RuntimeError, match="unknown"):
        await run_upgrade(engine, module)
    async with engine.connect() as db:
        assert await db.run_sync(snapshot) == before
        assert await db.run_sync(module.objects) == schema
        assert (await db.exec_driver_sql("PRAGMA foreign_keys")).scalar_one() == 1


@pytest.mark.parametrize("actor_db", ["sqlite"], indirect=True)
async def test_failure_after_rebuild_rolls_back_every_row_schema_and_fk_mode(number_db, monkeypatch):
    engine, _ = number_db
    module = migration()
    original = module.manifest
    calls = []
    def changed(connection):
        value = original(connection)
        calls.append(True)
        return value if len(calls) == 1 else {"injected_preservation_failure": True}
    async with engine.connect() as db:
        before = await db.run_sync(snapshot)
        schema = await db.run_sync(module.objects)
    monkeypatch.setattr(module, "manifest", changed)
    with pytest.raises(RuntimeError, match="preservation"):
        await run_upgrade(engine, module)
    async with engine.connect() as db:
        assert await db.run_sync(snapshot) == before
        assert await db.run_sync(module.objects) == schema
        assert (await db.exec_driver_sql("PRAGMA foreign_keys")).scalar_one() == 1


@pytest.mark.parametrize("actor_db", ["sqlite"], indirect=True)
async def test_legacy_uuid_alias_live_conflict_is_rejected_before_schema_changes(number_db):
    engine, data = number_db
    module = migration()
    async with engine.connect() as db:
        await db.exec_driver_sql("PRAGMA foreign_keys=OFF")
        await db.commit()
        await db.execute(sa.text("UPDATE students SET student_number='COLLIDE',deleted_at=NULL WHERE id=:id"), {"id": str(data["archived"].id)})
        await db.execute(sa.text("UPDATE students SET student_number='COLLIDE',organization_id=:alias WHERE id=:id"),
            {"id": str(data["live"].id), "alias": data["org"].id.hex})
        await db.commit()
        await db.exec_driver_sql("PRAGMA foreign_keys=ON")
        await db.commit()
        before = await db.run_sync(snapshot)
        schema = await db.run_sync(module.objects)
    with pytest.raises(RuntimeError, match="conflicting"):
        await run_upgrade(engine, module)
    async with engine.connect() as db:
        assert await db.run_sync(snapshot) == before
        assert await db.run_sync(module.objects) == schema
        assert (await db.exec_driver_sql("PRAGMA foreign_keys")).scalar_one() == 1


async def test_downgrade_never_erases_the_archive_to_restore_global_uniqueness(number_db):
    engine, _ = number_db
    module = migration()
    await run_upgrade(engine, module)
    async with engine.connect() as db:
        before = await db.run_sync(snapshot)
    async with engine.connect() as db:
        def reject(connection):
            context = MigrationContext.configure(connection)
            with context.begin_transaction(_per_migration=True), Operations.context(context):
                module.downgrade()
        with pytest.raises(RuntimeError, match="yede"):
            await db.run_sync(reject)
    async with engine.connect() as db:
        assert await db.run_sync(snapshot) == before
