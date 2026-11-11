"""Known archive-aware student index support, with hostile lookalikes rejected."""
# ruff: noqa: F811 -- pytest fixture imports intentionally match test parameters.
import json
from uuid import UUID

import pytest
from sqlalchemy import Column, DateTime, String, Table, text
from sqlalchemy.exc import IntegrityError
from test_release_integrity import integrity_db  # noqa: F401

from app.core.release_integrity import inspect_release_integrity
from app.core.uuid_type import CustomUUID

INDEX = "uq_students_org_student_number_live"


async def prepare(engine, metadata, *, expression=None, predicate="deleted_at IS NULL", name=INDEX):
    Table("students", metadata, Column("id", CustomUUID(), primary_key=True),
        Column("organization_id", CustomUUID()), Column("student_number", String(50)),
        Column("status", String(20)), Column("deleted_at", DateTime()))
    sqlite = engine.dialect.name == "sqlite"
    keys = expression or ("lower(replace(organization_id, '-', '')), student_number" if sqlite else "organization_id, student_number")
    async with engine.begin() as connection:
        await connection.exec_driver_sql("CREATE TABLE students(id VARCHAR(36) PRIMARY KEY,organization_id "
            + ("VARCHAR(36)" if sqlite else "UUID") + ",student_number VARCHAR(50),status VARCHAR(20),deleted_at TIMESTAMP)")
        await connection.exec_driver_sql(f'CREATE UNIQUE INDEX "{name}" ON "students" ({keys}) WHERE {predicate}')


async def add(connection, engine, number, *, archived=False, organization=UUID(int=900), status="INACTIVE", ident=1):
    await connection.execute(text("INSERT INTO students(id,organization_id,student_number,status,deleted_at) "
        "VALUES (:id,:org,:number,:status," + ("'2026-01-01'" if archived else "NULL") + ")"),
        {"id": str(UUID(int=1000 + ident)), "org": str(organization) if engine.dialect.name == "sqlite" else UUID(str(organization)),
            "number": number, "status": status})


async def test_known_student_index_preserves_archives_nulls_literal_numbers_and_school_scope(integrity_db):
    engine, metadata = integrity_db
    await prepare(engine, metadata)
    async with engine.begin() as connection:
        for ident in range(1, 4):
            await add(connection, engine, "REUSED", archived=True, ident=ident)
        await add(connection, engine, "REUSED", ident=4)
        await add(connection, engine, "REUSED", organization=UUID(int=901), ident=5)
        await add(connection, engine, None, ident=6)
        await add(connection, engine, None, ident=7)
        await add(connection, engine, UUID(int=902).hex, ident=8)
        await add(connection, engine, str(UUID(int=902)), ident=9)
    report = await inspect_release_integrity(engine, metadata)
    assert report["ready"] is True and report["complete"] is True and report["unsupported_count"] == 0, report
    assert report["checks"]["canonical_keys"]["count"] == 0 and "REUSED" not in json.dumps(report)
    # An unarchived INACTIVE student still reserves its number; failed restore
    # leaves the archive and every student identity intact.
    with pytest.raises(IntegrityError):
        async with engine.begin() as connection:
            await connection.exec_driver_sql("UPDATE students SET deleted_at=NULL WHERE deleted_at IS NOT NULL")
    again = await inspect_release_integrity(engine, metadata)
    assert again == report


@pytest.mark.parametrize("variant", ["status_predicate", "extra_predicate", "wrong_name", "wrong_expression", "wrong_columns"])
async def test_student_index_lookalikes_fail_closed(integrity_db, variant):
    engine, metadata = integrity_db
    sqlite = engine.dialect.name == "sqlite"
    options = {
        "status_predicate": {"predicate": "status = 'ACTIVE'"},
        "extra_predicate": {"predicate": "deleted_at IS NULL OR status = 'ACTIVE'"},
        "wrong_name": {"name": "student_index_lookalike"},
        "wrong_expression": {"expression": "lower(replace(organization_id, ' -', '')), student_number" if sqlite else "organization_id, lower(student_number)"},
        "wrong_columns": {"expression": "lower(replace(organization_id, '-', '')), status" if sqlite else "organization_id, status"},
    }
    await prepare(engine, metadata, **options[variant])
    report = await inspect_release_integrity(engine, metadata)
    assert report["ready"] is False and report["unsupported_count"] >= 1, (variant, report)


@pytest.mark.parametrize("integrity_db", ["sqlite"], indirect=True)
async def test_exact_sqlite_student_index_guards_canonical_uuid_alias_and_mapped_semantics(integrity_db):
    engine, metadata = integrity_db
    await prepare(engine, metadata)
    async with engine.begin() as connection:
        await add(connection, engine, "PRIVATE_NUMBER")
    with pytest.raises(IntegrityError):
        async with engine.begin() as connection:
            await add(connection, engine, "PRIVATE_NUMBER", organization=UUID(int=900).hex, ident=2)
    clean = await inspect_release_integrity(engine, metadata)
    assert clean["ready"] is True, clean
    metadata.tables["students"].c.organization_id.type = String(36)
    unknown = await inspect_release_integrity(engine, metadata)
    assert unknown["ready"] is False and unknown["unsupported_count"] >= 1, unknown
    assert "PRIVATE_NUMBER" not in json.dumps(unknown)


@pytest.mark.parametrize("integrity_db", ["sqlite"], indirect=True)
@pytest.mark.parametrize("expression", [
    "lower(replace(organization_id, '-', '')), student_number COLLATE NOCASE",
    "lower(replace(organization_id, '-', '')) DESC, student_number",
    "lower(replace(organization_id, '-', '')), lower(student_number)",
    "lower(replace(organization_id, '-', '')) /* comment */, student_number",
])
async def test_sqlite_student_expression_collation_order_and_sql_variations_are_not_generalized(integrity_db, expression):
    engine, metadata = integrity_db
    await prepare(engine, metadata, expression=expression)
    report = await inspect_release_integrity(engine, metadata)
    assert report["ready"] is False and report["unsupported_count"] >= 1, report
