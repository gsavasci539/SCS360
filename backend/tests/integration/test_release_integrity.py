"""Release integrity uses raw, read-only snapshots on disposable SQLite/PostgreSQL."""
import json
import os
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Column, ForeignKey, MetaData, String, Table, Uuid, event, text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.release_integrity import inspect_release_integrity
from app.core.uuid_type import CustomUUID


@pytest.fixture(params=["sqlite", "postgresql"])
async def integrity_db(tmp_path, request):
    cleanup, schema = None, None
    if request.param == "postgresql":
        url = os.getenv("TEST_POSTGRES_URL")
        if not url:
            pytest.skip("Disposable TEST_POSTGRES_URL required")
        if "scs360_acceptance" not in url:
            raise RuntimeError("Disposable acceptance database required")
        schema = "release_gate_" + uuid4().hex
        cleanup = create_async_engine(url)
        async with cleanup.begin() as connection:
            await connection.exec_driver_sql('CREATE SCHEMA "' + schema + '"')
        engine = create_async_engine(url, connect_args={"server_settings": {"search_path": schema}})
    else:
        engine = create_async_engine("sqlite+aiosqlite:///" + (tmp_path / "integrity.db").as_posix())
    metadata = MetaData()
    Table("parent_records", metadata, Column("id", CustomUUID(), primary_key=True))
    Table("child_records", metadata, Column("id", CustomUUID(), primary_key=True), Column("parent_id", CustomUUID(), ForeignKey("parent_records.id")))
    Table("business_records", metadata, Column("id", CustomUUID(), primary_key=True), Column("organization_id", CustomUUID()), Column("code", String))
    Table("native_records", metadata, Column("id", Uuid(), primary_key=True))
    Table("school_payment_merchants", metadata, Column("id", CustomUUID(), primary_key=True), Column("organization_id", CustomUUID()), Column("is_current", String))
    async with engine.begin() as connection:
        await connection.exec_driver_sql("CREATE TABLE alembic_version(version_num VARCHAR(32) PRIMARY KEY)")
        await connection.exec_driver_sql("INSERT INTO alembic_version VALUES ('testhead')")
        await connection.exec_driver_sql("CREATE TABLE parent_records(id VARCHAR(36) PRIMARY KEY)")
        await connection.exec_driver_sql("CREATE TABLE child_records(id VARCHAR(36) PRIMARY KEY,parent_id VARCHAR(36),CONSTRAINT fk_parent FOREIGN KEY(parent_id) REFERENCES parent_records(id))")
        await connection.exec_driver_sql("CREATE TABLE business_records(id VARCHAR(36) PRIMARY KEY,organization_id VARCHAR(36),code VARCHAR(100),UNIQUE(organization_id,code))")
        await connection.exec_driver_sql("CREATE TABLE native_records(id " + ("UUID" if request.param == "postgresql" else "VARCHAR(36)") + " PRIMARY KEY)")
        await connection.exec_driver_sql("CREATE TABLE school_payment_merchants(id VARCHAR(36) PRIMARY KEY,organization_id VARCHAR(36),is_current BOOLEAN NOT NULL)")
        predicate = "is_current IS TRUE" if request.param == "postgresql" else "is_current = 1"
        await connection.exec_driver_sql("CREATE UNIQUE INDEX uq_school_payment_merchant_current_org ON school_payment_merchants(organization_id) WHERE " + predicate)
        await connection.execute(text("INSERT INTO native_records VALUES (:id)"), {"id": UUID(int=123) if request.param == "postgresql" else str(UUID(int=123))})
    try:
        yield engine, metadata
    finally:
        await engine.dispose()
        if cleanup:
            async with cleanup.begin() as connection:
                await connection.exec_driver_sql('DROP SCHEMA "' + schema + '" CASCADE')
            await cleanup.dispose()


async def test_clean_snapshot_schema_gate_privacy_readonly_and_pool_state_restore(integrity_db):
    engine, metadata = integrity_db
    statements = []

    def record(_conn, _cursor, statement, _parameters, _context, _many):
        statements.append(statement.lstrip().split()[0].upper())

    event.listen(engine.sync_engine, "before_cursor_execute", record)
    try:
        report = await inspect_release_integrity(engine, metadata, expected_revision="testhead")
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", record)
    assert report["ready"] is True and report["schema_current"] is True and report["snapshot_read_only"] is True, report
    assert all(item == {"ok": True, "count": 0} for item in report["checks"].values())
    assert not {"INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP"} & set(statements)
    async with engine.begin() as connection:
        # A new pooled use still permits its own writes after the gate restores options.
        await connection.execute(text("INSERT INTO parent_records VALUES (:id)"), {"id": str(UUID(int=1))})
    wrong = await inspect_release_integrity(engine, metadata, expected_revision="otherhead")
    assert wrong["ready"] is False and wrong["schema_current"] is False


async def test_raw_foreign_keys_do_not_hide_uuid_spelling_mismatch(integrity_db):
    engine, metadata = integrity_db
    parent = UUID(int=10)
    async with engine.begin() as connection:
        if engine.dialect.name == "postgresql":
            await connection.exec_driver_sql("ALTER TABLE child_records DROP CONSTRAINT fk_parent")
        await connection.execute(text("INSERT INTO parent_records VALUES (:id)"), {"id": str(parent)})
        await connection.execute(text("INSERT INTO child_records VALUES (:id,:parent)"), {"id": str(UUID(int=11)), "parent": parent.hex})
        if engine.dialect.name == "postgresql":
            await connection.exec_driver_sql("ALTER TABLE child_records ADD CONSTRAINT fk_parent FOREIGN KEY(parent_id) REFERENCES parent_records(id) NOT VALID")
    report = await inspect_release_integrity(engine, metadata)
    assert report["ready"] is False and report["checks"]["physical_foreign_keys"]["count"] == 1, report
    assert report["checks"]["uuid_literals"]["count"] == 0
    assert str(parent) not in json.dumps(report) and parent.hex not in json.dumps(report)


async def test_invalid_uuid_and_normalized_primary_natural_key_collisions_fail_without_values(integrity_db):
    engine, metadata = integrity_db
    identifier = UUID(int=20)
    async with engine.begin() as connection:
        for value in (str(identifier), identifier.hex, "PRIVATE_INVALID_IDENTIFIER"):
            await connection.execute(text("INSERT INTO parent_records VALUES (:id)"), {"id": value})
        for index, organization in enumerate((str(identifier), identifier.hex)):
            await connection.execute(text("INSERT INTO business_records VALUES (:id,:org,:code)"),
                {"id": str(UUID(int=30 + index)), "org": organization, "code": "PRIVATE_NATURAL_KEY"})
    report = await inspect_release_integrity(engine, metadata)
    assert report["ready"] is False and report["checks"]["uuid_literals"]["count"] == 1, report
    assert report["checks"]["canonical_keys"]["count"] == 2, report
    encoded = json.dumps(report)
    for private in (str(identifier), identifier.hex, "PRIVATE_INVALID_IDENTIFIER", "PRIVATE_NATURAL_KEY"):
        assert private not in encoded


async def test_missing_metadata_column_fails_without_changing_caller_metadata(integrity_db):
    engine, metadata = integrity_db
    metadata.tables["parent_records"].append_column(Column("missing_model_field", String))
    before = tuple(metadata.tables["parent_records"].c.keys())
    report = await inspect_release_integrity(engine, metadata)
    assert report["ready"] is False and report["checks"]["model_columns"]["count"] == 1, report
    assert tuple(metadata.tables["parent_records"].c.keys()) == before


async def test_uuid_looking_business_codes_are_distinct_literals_not_identifiers(integrity_db):
    engine, metadata = integrity_db
    organization, code = UUID(int=100), UUID(int=101)
    async with engine.begin() as connection:
        for index, literal in enumerate((code.hex, str(code))):
            await connection.execute(text("INSERT INTO business_records VALUES (:id,:org,:code)"),
                {"id": str(UUID(int=110 + index)), "org": str(organization), "code": literal})
    report = await inspect_release_integrity(engine, metadata)
    assert report["ready"] is True and report["checks"]["canonical_keys"]["count"] == 0, report


async def test_null_unique_keys_and_exact_merchant_partial_scope(integrity_db):
    engine, metadata = integrity_db
    organization = UUID(int=40)
    async with engine.begin() as connection:
        for index, value in enumerate((str(organization), organization.hex)):
            await connection.execute(text("INSERT INTO business_records VALUES (:id,:org,NULL)"), {"id": str(UUID(int=50 + index)), "org": value})
            await connection.execute(text("INSERT INTO school_payment_merchants VALUES (:id,:org,:active)"),
                {"id": str(UUID(int=60 + index)), "org": value, "active": False})
        await connection.execute(text("INSERT INTO school_payment_merchants VALUES (:id,:org,:active)"),
            {"id": str(UUID(int=70)), "org": str(organization), "active": True})
    clean = await inspect_release_integrity(engine, metadata)
    assert clean["ready"] is True, clean
    async with engine.begin() as connection:
        await connection.execute(text("INSERT INTO school_payment_merchants VALUES (:id,:org,:active)"),
            {"id": str(UUID(int=71)), "org": organization.hex, "active": True})
    broken = await inspect_release_integrity(engine, metadata)
    assert broken["ready"] is False and broken["checks"]["canonical_keys"]["count"] == 1, broken


async def test_unknown_expression_comparisons_and_aggregate_row_budget_fail_closed(integrity_db):
    engine, metadata = integrity_db
    limited = await inspect_release_integrity(engine, metadata, max_scan_rows=1)
    assert limited["ready"] is False and any(row["reason"] == "row_budget_exceeded" for row in limited["issues"])
    async with engine.begin() as connection:
        await connection.exec_driver_sql("CREATE UNIQUE INDEX unsupported_expression ON business_records(lower(code))")
    report = await inspect_release_integrity(engine, metadata)
    assert report["ready"] is False and any(row["reason"] == "unsupported_unique_comparison" for row in report["issues"]), report


async def test_inspection_exception_is_sanitized_and_readonly_state_is_restored(integrity_db, monkeypatch):
    engine, metadata = integrity_db
    from app.core import release_integrity

    invalid = await inspect_release_integrity(engine, metadata, max_scan_rows="PRIVATE_ARGUMENT_VALUE")
    assert invalid["ready"] is False and invalid["max_scan_rows"] is None
    assert "PRIVATE" not in json.dumps(invalid)

    async def fail(*_args, **_kwargs):
        raise RuntimeError("PRIVATE_SQL_PASSWORD_AND_ROW_VALUES")

    monkeypatch.setattr(release_integrity, "_scan", fail)
    report = await inspect_release_integrity(engine, metadata)
    assert report["ready"] is False and report["issues"][-1]["reason"] == "inspection_failed"
    assert "PRIVATE" not in json.dumps(report)
    async with engine.begin() as connection:
        await connection.execute(text("INSERT INTO parent_records VALUES (:id)"), {"id": str(UUID(int=80))})


async def test_unknown_merchant_predicate_fails_closed_instead_of_changing_its_truth_semantics(integrity_db):
    engine, metadata = integrity_db
    async with engine.begin() as connection:
        await connection.exec_driver_sql("DROP INDEX uq_school_payment_merchant_current_org")
        predicate = "is_current IS FALSE" if engine.dialect.name == "postgresql" else "is_current IS TRUE"
        await connection.exec_driver_sql("CREATE UNIQUE INDEX uq_school_payment_merchant_current_org ON school_payment_merchants(organization_id) WHERE " + predicate)
        if engine.dialect.name == "sqlite":
            for index, organization in enumerate((UUID(int=200).hex, str(UUID(int=200)))):
                await connection.execute(text("INSERT INTO school_payment_merchants VALUES (:id,:org,2)"),
                    {"id": str(UUID(int=210 + index)), "org": organization})
    report = await inspect_release_integrity(engine, metadata)
    assert report["ready"] is False and report["unsupported_count"] >= 1, report


@pytest.mark.parametrize("integrity_db", ["postgresql"], indirect=True)
async def test_clean_not_valid_fk_is_not_certified_as_validated(integrity_db):
    engine, metadata = integrity_db
    async with engine.begin() as connection:
        await connection.exec_driver_sql("ALTER TABLE child_records DROP CONSTRAINT fk_parent")
        await connection.exec_driver_sql("ALTER TABLE child_records ADD CONSTRAINT fk_parent FOREIGN KEY(parent_id) REFERENCES parent_records(id) NOT VALID")
    report = await inspect_release_integrity(engine, metadata)
    assert report["ready"] is False and report["complete"] is False
    assert report["checks"]["physical_foreign_keys"]["count"] == 0
    assert any(issue["reason"] == "unvalidated_foreign_key" for issue in report["issues"])


@pytest.mark.parametrize("integrity_db", ["postgresql"], indirect=True)
async def test_match_full_partial_null_is_unsupported_and_never_accepted(integrity_db):
    engine, metadata = integrity_db
    async with engine.begin() as connection:
        await connection.exec_driver_sql("CREATE TABLE composite_parent(a VARCHAR(36),b VARCHAR(36),PRIMARY KEY(a,b))")
        await connection.exec_driver_sql("CREATE TABLE composite_child(a VARCHAR(36),b VARCHAR(36))")
        await connection.exec_driver_sql("INSERT INTO composite_child VALUES (NULL,'partial-null')")
        await connection.exec_driver_sql("ALTER TABLE composite_child ADD CONSTRAINT full_fk FOREIGN KEY(a,b) REFERENCES composite_parent(a,b) MATCH FULL NOT VALID")
    report = await inspect_release_integrity(engine, metadata)
    assert report["ready"] is False and report["complete"] is False
    assert any(issue["reason"] == "unsupported_foreign_key_match" for issue in report["issues"])


@pytest.mark.parametrize("integrity_db", ["postgresql"], indirect=True)
async def test_extension_default_casefold_opclass_is_not_treated_as_literal_equality(integrity_db):
    engine, metadata = integrity_db
    async with engine.begin() as connection:
        schema = (await connection.exec_driver_sql("SELECT current_schema()")).scalar_one()
        extension = (await connection.exec_driver_sql("SELECT n.nspname FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace WHERE e.extname='citext'")).scalar_one_or_none()
        if extension is None:
            await connection.exec_driver_sql('CREATE EXTENSION citext WITH SCHEMA "' + schema + '"')
            extension = schema
        await connection.exec_driver_sql('ALTER TABLE business_records ALTER COLUMN code TYPE "' + extension + '".citext')
        for index, organization in enumerate((str(UUID(int=220)), UUID(int=220).hex)):
            await connection.execute(text("INSERT INTO business_records VALUES (:id,:org,:code)"),
                {"id": str(UUID(int=230 + index)), "org": organization, "code": "CaseFold" if index == 0 else "casefold"})
    report = await inspect_release_integrity(engine, metadata)
    assert report["ready"] is False and report["unsupported_count"] >= 1, report


@pytest.mark.parametrize("integrity_db", ["postgresql"], indirect=True)
async def test_native_enum_labels_remain_supported_with_the_builtin_enum_opclass(integrity_db):
    engine, metadata = integrity_db
    async with engine.begin() as connection:
        await connection.exec_driver_sql("CREATE TYPE integrity_phase AS ENUM ('First','first')")
        await connection.exec_driver_sql("ALTER TABLE business_records ALTER COLUMN code TYPE integrity_phase USING code::integrity_phase")
        for index, label in enumerate(("First", "first")):
            await connection.execute(text("INSERT INTO business_records VALUES (:id,:org,:code)"),
                {"id": str(UUID(int=260 + index)), "org": str(UUID(int=270)), "code": label})
    report = await inspect_release_integrity(engine, metadata)
    assert report["ready"] is True, report


@pytest.mark.parametrize("integrity_db", ["postgresql"], indirect=True)
async def test_fk_true_parent_schema_is_preserved_when_both_schemas_are_in_search_path(integrity_db):
    engine, metadata = integrity_db
    other = "release_parent_" + uuid4().hex
    gate_engine = None
    async with engine.begin() as connection:
        own = (await connection.exec_driver_sql("SELECT current_schema()")).scalar_one()
        await connection.exec_driver_sql('CREATE SCHEMA "' + other + '"')
    try:
        async with engine.begin() as connection:
            await connection.exec_driver_sql('CREATE TABLE "' + other + '".parent_records(id VARCHAR(36) PRIMARY KEY)')
            await connection.exec_driver_sql("ALTER TABLE child_records DROP CONSTRAINT fk_parent")
            await connection.execute(text("INSERT INTO parent_records VALUES (:id)"), {"id": str(UUID(int=240))})
            await connection.execute(text("INSERT INTO child_records VALUES (:id,:parent)"), {"id": str(UUID(int=241)), "parent": str(UUID(int=240))})
            await connection.exec_driver_sql('ALTER TABLE child_records ADD CONSTRAINT fk_parent FOREIGN KEY(parent_id) REFERENCES "' + other + '".parent_records(id) NOT VALID')
        gate_engine = create_async_engine(engine.url, connect_args={"server_settings": {"search_path": own + "," + other}})
        report = await inspect_release_integrity(gate_engine, metadata)
        assert report["ready"] is False and report["checks"]["physical_foreign_keys"]["count"] == 1, report
    finally:
        if gate_engine:
            await gate_engine.dispose()
        async with engine.begin() as connection:
            await connection.exec_driver_sql('DROP SCHEMA "' + other + '" CASCADE')
