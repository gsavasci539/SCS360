"""036 adds missing timetable actor fields without rebuilding legacy tables."""
from datetime import UTC, datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from uuid import uuid4

from alembic.migration import MigrationContext
from alembic.operations import Operations
import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.uuid_type import CustomUUID
from app.domain.entities.timetable import Timetable


def migration():
    path = Path(__file__).resolve().parents[2] / "alembic/versions/036_timetable_actors.py"
    spec = importlib.util.spec_from_file_location("timetable_actor_migration_036", path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    assert module.revision == "036" and module.down_revision == "035"
    return module


@pytest.fixture(params=["sqlite", "postgresql"])
async def actor_db(tmp_path, request):
    cleanup = None
    if request.param == "postgresql":
        url = os.getenv("TEST_POSTGRES_URL")
        if not url:
            pytest.skip("TEST_POSTGRES_URL must point at a disposable acceptance database")
        if "scs360_acceptance" not in url:
            raise RuntimeError("Only a disposable scs360_acceptance database is allowed")
        schema = "acceptance_timetable_" + uuid4().hex
        cleanup = create_async_engine(url)
        async with cleanup.begin() as db:
            await db.execute(sa.text(f'CREATE SCHEMA "{schema}"'))
        engine = create_async_engine(url, connect_args={"server_settings": {"search_path": schema}})
    else:
        engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'timetable.db').as_posix()}")
        @sa.event.listens_for(engine.sync_engine, "connect")
        def enable_foreign_keys(dbapi, _):
            dbapi.execute("PRAGMA foreign_keys=ON")
    try:
        yield engine
    finally:
        await engine.dispose()
        if cleanup:
            async with cleanup.begin() as db:
                await db.execute(sa.text(f'DROP SCHEMA "{schema}" CASCADE'))
            await cleanup.dispose()


def old_schema(connection, present):
    metadata = sa.MetaData()
    users = sa.Table("users", metadata, sa.Column("id", CustomUUID(), primary_key=True),
        sa.Column("password_hash", sa.String(255), nullable=False))
    for name in ("classes", "timetable_slots", "classroom_assignments"):
        sa.Table(name, metadata, sa.Column("id", CustomUUID(), primary_key=True))
    table = sa.Table("timetables", metadata, sa.Column("id", CustomUUID(), primary_key=True),
        sa.Column("class_id", CustomUUID(), sa.ForeignKey("classes.id"), nullable=False),
        sa.Column("slot_id", CustomUUID(), sa.ForeignKey("timetable_slots.id"), nullable=False),
        sa.Column("classroom_assignment_id", CustomUUID(), sa.ForeignKey("classroom_assignments.id")),
        sa.Column("academic_year", sa.String(20), nullable=False), sa.Column("semester", sa.Integer()),
        sa.Column("is_active", sa.Boolean()), sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)))
    for name in present:
        table.append_column(sa.Column(name, CustomUUID(), sa.ForeignKey("users.id"), nullable=True))
    metadata.create_all(connection)
    actor, classroom, slot, assignment, identifier = [uuid4() for _ in range(5)]
    connection.execute(users.insert().values(id=actor, password_hash="acceptance-inert-hash"))
    for name, value in (("classes", classroom), ("timetable_slots", slot), ("classroom_assignments", assignment)):
        connection.execute(metadata.tables[name].insert().values(id=value))
    stamp = datetime(2026, 10, 1, 8, 30, tzinfo=UTC)
    connection.execute(table.insert().values(id=identifier, class_id=classroom, slot_id=slot,
        classroom_assignment_id=assignment, academic_year="2026-2027", semester=1, is_active=True,
        created_at=stamp, updated_at=stamp, **{name: actor for name in present}))
    if connection.dialect.name == "sqlite":
        # Preserve the actual spelling of an old UUID instead of silently fixing it.
        connection.execute(sa.text("UPDATE timetables SET id=:old WHERE id=:canonical"),
            {"old": identifier.hex, "canonical": str(identifier)})
    return identifier, actor


def snapshot(connection):
    inspector = sa.inspect(connection)
    columns = {name: [c["name"] for c in inspector.get_columns(name)] for name in inspector.get_table_names()}
    def values():
        result = {}
        for name, names in columns.items():
            selected = ", ".join('"' + column + '"' for column in names)
            rows = connection.execute(sa.text(f'SELECT {selected} FROM "{name}"')).all()
            encoded = sorted(json.dumps(list(row), default=str) for row in rows)
            result[name] = (len(rows), hashlib.sha256("\n".join(encoded).encode()).hexdigest())
        return result
    return columns, values, values()


@pytest.mark.parametrize("present", [(), ("created_by",), ("updated_by",), ("created_by", "updated_by")],
    ids=["neither-actor", "created-only", "updated-only", "fresh-both"])
async def test_036_preserves_old_columns_selects_real_orm_and_enforces_actor_foreign_keys(actor_db, present):
    module = migration()
    async with actor_db.begin() as db:
        identifier, actor = await db.run_sync(lambda connection: old_schema(connection, present))
    sessions = async_sessionmaker(actor_db, expire_on_commit=False)
    if len(present) < 2:
        async with sessions() as db:
            with pytest.raises((OperationalError, ProgrammingError)):
                await db.execute(sa.select(Timetable))
            await db.rollback()
    async with actor_db.begin() as db:
        def migrate(connection):
            columns, manifest, before = snapshot(connection)
            before_pk = sa.inspect(connection).get_pk_constraint("timetables")
            statements = []
            def capture(_, __, statement, ___, ____, _____): statements.append(statement)
            sa.event.listen(connection, "before_cursor_execute", capture)
            try:
                with Operations.context(MigrationContext.configure(connection)):
                    module.upgrade(); module.upgrade()
            finally:
                sa.event.remove(connection, "before_cursor_execute", capture)
            assert manifest() == before
            assert sa.inspect(connection).get_pk_constraint("timetables") == before_pk
            assert set(sa.inspect(connection).get_table_names()) == set(columns)
            assert not any(any(word in statement.upper() for word in ("DROP TABLE", "CREATE TABLE", "UPDATE ", "DELETE ", "FOREIGN_KEYS=OFF")) for statement in statements)
            additions = {c["name"]: c for c in sa.inspect(connection).get_columns("timetables")}
            foreign = sa.inspect(connection).get_foreign_keys("timetables")
            for name in ("created_by", "updated_by"):
                assert additions[name]["nullable"] is True and additions[name]["default"] is None
                assert any(fk["constrained_columns"] == [name] and fk["referred_table"] == "users" and fk["referred_columns"] == ["id"] for fk in foreign)
                value = connection.execute(sa.text(f'SELECT "{name}" FROM timetables')).scalar_one()
                assert (str(value).replace("-", "") == actor.hex) if name in present else value is None
            if connection.dialect.name == "sqlite":
                assert connection.execute(sa.text("PRAGMA foreign_keys")).scalar_one() == 1
                assert connection.execute(sa.text("SELECT id FROM timetables")).scalar_one() == identifier.hex
            else:
                assert all(str(additions[name]["type"]) == "UUID" for name in ("created_by", "updated_by"))
        await db.run_sync(migrate)
    async with sessions() as db:
        row = (await db.execute(sa.select(Timetable))).scalar_one()
        assert row.id == identifier and row.academic_year == "2026-2027"
        assert row.created_by == (actor if "created_by" in present else None)
        assert row.updated_by == (actor if "updated_by" in present else None)
        for name in ("created_by", "updated_by"):
            # Explicit Core update isolates new FK semantics from legacy ORM ID spellings.
            async with db.begin_nested():
                native_actor = actor if actor_db.dialect.name == "postgresql" else str(actor)
                await db.execute(sa.text(f'UPDATE timetables SET "{name}"=:actor'), {"actor": native_actor})
            with pytest.raises(IntegrityError):
                async with db.begin_nested():
                    invalid = uuid4() if actor_db.dialect.name == "postgresql" else str(uuid4())
                    await db.execute(sa.text(f'UPDATE timetables SET "{name}"=:actor'), {"actor": invalid})
        await db.commit()
    async with actor_db.begin() as db:
        def reject_downgrade(connection):
            _, manifest, before = snapshot(connection)
            with Operations.context(MigrationContext.configure(connection)), pytest.raises(RuntimeError, match="yede"):
                module.downgrade()
            assert manifest() == before
        await db.run_sync(reject_downgrade)


async def test_036_missing_table_fails_clearly_without_creating_a_partial_schema(actor_db):
    module = migration()
    async with actor_db.begin() as db:
        def missing(connection):
            with Operations.context(MigrationContext.configure(connection)), pytest.raises(RuntimeError, match="timetables"):
                module.upgrade()
            assert sa.inspect(connection).get_table_names() == []
        await db.run_sync(missing)
