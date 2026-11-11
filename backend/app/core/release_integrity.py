"""Read-only release gate. Reports contain schema names and counts, never row values.

The row budget is the sum of rows in every physical table of the selected/default
schema, counted once per table. Exceeding it fails closed before row extraction.
Only the application's known merchant/student partial indexes are supported;
other expression keys, custom comparison rules and predicates fail closed.
"""
import math
import re
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Uuid, inspect, text

from app.core.uuid_type import CustomUUID

_UUID = re.compile(r"(?:[0-9a-fA-F]{32}|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\Z")
_CHECKS = ("physical_foreign_keys", "uuid_literals", "model_columns", "canonical_keys")
_STUDENT_INDEX = "uq_students_org_student_number_live"


def _identifier(name):
    return '(?:' + re.escape(name) + '|"' + re.escape(name) + '")'


def _student_sqlite_expression(table, name, sql, parts):
    """Accept one exact known expression, never normalize arbitrary SQL/literals."""
    if table != "students" or name != _STUDENT_INDEX or len(parts) != 2:
        return False
    if parts[0][1:3] != (-2, None) or parts[1][2] != "student_number":
        return False
    if any(part[3] != 0 or part[4] != "BINARY" for part in parts):
        return False
    pattern = (r"CREATE\s+UNIQUE\s+INDEX\s+" + _identifier(_STUDENT_INDEX)
        + r"\s+ON\s+" + _identifier("students") + r"\s*\(\s*lower\s*\(\s*replace\s*\(\s*"
        + _identifier("organization_id") + r"\s*,\s*'-'\s*,\s*''\s*\)\s*\)\s*,\s*"
        + _identifier("student_number") + r"\s*\)\s+WHERE\s+" + _identifier("deleted_at") + r"\s+IS\s+NULL\s*")
    return re.fullmatch(pattern, sql or "", re.IGNORECASE) is not None


def _issue(report, check, reason, *, table=None, columns=None, count=1):
    item = {"check": check, "reason": reason, "count": count}
    if table is not None:
        item["table"] = table
    if columns is not None:
        item["columns"] = list(columns)
    report["issues"].append(item)
    if check in report["checks"]:
        report["checks"][check]["ok"] = False
        report["checks"][check]["count"] += count


def _uuid(value):
    if isinstance(value, UUID):
        return str(value)
    return str(UUID(value)) if isinstance(value, str) and _UUID.fullmatch(value) else None


def _key(value, uuid_column):
    canonical = _uuid(value) if uuid_column else None
    if canonical is not None:
        return ("uuid", canonical)
    if isinstance(value, float) and not math.isfinite(value) or isinstance(value, Decimal) and not value.is_finite():
        raise ValueError("unsupported unique value")
    if not isinstance(value, str | int | float | bool | bytes | Decimal | date | datetime):
        raise ValueError("unsupported unique type")
    return (type(value).__name__, value)


def _known_predicate(table, name, columns, predicate, dialect):
    if predicate is None:
        return None
    normalized = re.sub(r'[\s()"]', "", str(predicate)).lower()
    expected = "is_current=1" if dialect == "sqlite" else "is_currentistrue"
    if table == "school_payment_merchants" and name == "uq_school_payment_merchant_current_org" and normalized == expected:
        return "is_current", " IS TRUE" if dialect == "postgresql" else " = 1"
    if (table == "students" and name == _STUDENT_INDEX and columns == ["organization_id", "student_number"]
        and re.fullmatch(r'\s*\(?\s*"?deleted_at"?\s+IS\s+NULL\s*\)?\s*', str(predicate), re.IGNORECASE)):
        return "deleted_at", " IS NULL"
    raise ValueError("unsupported partial predicate")


async def _keys(connection, schema, tables, quote):
    records = []
    if connection.dialect.name == "sqlite":
        for table in tables:
            indexes = (await connection.exec_driver_sql("PRAGMA index_list(" + quote(table) + ")")).all()
            for index in indexes:
                if not index[2]:
                    continue
                parts = [part for part in (await connection.exec_driver_sql("PRAGMA index_xinfo(" + quote(index[1]) + ")")).all() if part[5]]
                predicate = None
                sql = None
                if index[4]:
                    sql = (await connection.execute(text("SELECT sql FROM sqlite_master WHERE type='index' AND name=:name"), {"name": index[1]})).scalar_one()
                    words = list(re.finditer(r"\bWHERE\b", sql, re.IGNORECASE))
                    predicate = sql[words[0].end():] if len(words) == 1 else "unsupported"
                student_expression = bool(index[4]) and _student_sqlite_expression(table, index[1], sql, parts)
                records.append({"table": table, "name": index[1],
                    "columns": ["organization_id", "student_number"] if student_expression else [part[2] for part in parts],
                    "student_expression": student_expression,
                    "unsupported": not student_expression and any(part[1] < 0 or part[2] is None or part[4] != "BINARY" for part in parts), "predicate": predicate})
        return records
    rows = (await connection.exec_driver_sql("""
        SELECT tab.relname AS table_name, idx.relname AS index_name,
            i.indnullsnotdistinct, i.indisvalid, i.indisready,
            pg_get_expr(i.indpred,i.indrelid) AS predicate,
            i.indexprs IS NOT NULL AS expression_key, a.attname AS column_name,
            k.ordinality, coll.collisdeterministic, opc.opcdefault,
            opcns.nspname AS opclass_schema, typens.nspname AS type_schema, coltype.typtype::text AS type_kind
        FROM pg_index i JOIN pg_class tab ON tab.oid=i.indrelid
        JOIN pg_namespace ns ON ns.oid=tab.relnamespace
        JOIN pg_class idx ON idx.oid=i.indexrelid
        CROSS JOIN LATERAL unnest(i.indkey::smallint[]) WITH ORDINALITY k(attnum,ordinality)
        LEFT JOIN pg_attribute a ON a.attrelid=tab.oid AND a.attnum=k.attnum
        LEFT JOIN pg_collation coll ON coll.oid=i.indcollation[(k.ordinality-1)::integer]
        LEFT JOIN pg_opclass opc ON opc.oid=i.indclass[(k.ordinality-1)::integer]
        LEFT JOIN pg_namespace opcns ON opcns.oid=opc.opcnamespace
        LEFT JOIN pg_type coltype ON coltype.oid=a.atttypid
        LEFT JOIN pg_namespace typens ON typens.oid=coltype.typnamespace
        WHERE ns.nspname=current_schema() AND i.indisunique AND k.ordinality<=i.indnkeyatts
        ORDER BY tab.relname,idx.relname,k.ordinality
    """)).mappings().all()
    grouped = {}
    for row in rows:
        key = (row["table_name"], row["index_name"])
        item = grouped.setdefault(key, {"table": key[0], "name": key[1], "columns": [], "predicate": row["predicate"], "unsupported": False})
        item["columns"].append(row["column_name"])
        item["unsupported"] |= bool(row["indnullsnotdistinct"] or not row["indisvalid"] or not row["indisready"] or row["expression_key"]
            or row["column_name"] is None or row["collisdeterministic"] is False or row["opcdefault"] is False
            or row["opclass_schema"] != "pg_catalog" or (row["type_schema"] != "pg_catalog" and row["type_kind"] != "e"))
    return list(grouped.values())


async def _scan(connection, metadata, report, expected_revision, max_scan_rows):
    dialect = connection.dialect.name
    quote = connection.dialect.identifier_preparer.quote
    schema = (await connection.exec_driver_sql("SELECT current_schema()")).scalar_one() if dialect == "postgresql" else None

    def table_sql(name, owner=schema):
        return (quote(owner) + "." if owner else "") + quote(name)

    def reflect(sync):
        inspector = inspect(sync)
        tables = inspector.get_table_names(schema=schema)
        options = {"postgresql_ignore_search_path": True} if dialect == "postgresql" else {}
        return tables, {name: inspector.get_columns(name, schema=schema) for name in tables}, {name: inspector.get_foreign_keys(name, schema=schema, **options) for name in tables}

    tables, columns, foreign_keys = await connection.run_sync(reflect)
    physical = {name: {column["name"] for column in values} for name, values in columns.items()}
    uuid_key_columns = {name: {column["name"] for column in values if isinstance(column["type"], Uuid)} for name, values in columns.items()}
    for table in metadata.tables.values():
        if table.schema in {None, schema} and table.name in physical:
            uuid_key_columns[table.name].update(column.name for column in table.c
                if isinstance(column.type, CustomUUID | Uuid) and column.name in physical[table.name])
    report["tables_checked"] = len(tables)
    if expected_revision is not None:
        if "alembic_version" in physical and "version_num" in physical["alembic_version"]:
            revisions = (await connection.exec_driver_sql("SELECT version_num FROM " + table_sql("alembic_version"))).scalars().all()
            report["schema_current"] = revisions == [expected_revision]
        else:
            report["schema_current"] = False
    counts = [int((await connection.exec_driver_sql("SELECT COUNT(*) FROM " + table_sql(name))).scalar_one()) for name in tables]
    report["table_rows_checked"] = sum(counts)
    if sum(counts) > max_scan_rows:
        _issue(report, "inspection", "row_budget_exceeded")
        return
    for table in metadata.tables.values():
        if table.schema not in {None, schema}:
            _issue(report, "model_columns", "unsupported_metadata_schema", table=table.name)
            continue
        missing = set(table.c.keys()) - physical.get(table.name, set())
        if missing:
            _issue(report, "model_columns", "missing_model_columns", table=table.name, columns=sorted(missing), count=len(missing))
        for column in table.c:
            if not isinstance(column.type, CustomUUID | Uuid) or not (column.primary_key or column.foreign_keys) or column.name in missing:
                continue
            values = (await connection.exec_driver_sql("SELECT " + quote(column.name) + " FROM " + table_sql(table.name)
                + " WHERE " + quote(column.name) + " IS NOT NULL")).scalars()
            invalid = sum(_uuid(value) is None for value in values)
            if invalid:
                _issue(report, "uuid_literals", "invalid_uuid_literals", table=table.name, columns=[column.name], count=invalid)
    if dialect == "sqlite":
        violations = Counter(row[0] for row in (await connection.exec_driver_sql("PRAGMA foreign_key_check")).all())
        for table, count in violations.items():
            _issue(report, "physical_foreign_keys", "foreign_key_violations", table=table, count=count)
    else:
        unvalidated = (await connection.exec_driver_sql("""
            SELECT rel.relname,COUNT(*) FROM pg_constraint con
            JOIN pg_class rel ON rel.oid=con.conrelid
            JOIN pg_namespace ns ON ns.oid=rel.relnamespace
            WHERE con.contype='f' AND NOT con.convalidated AND ns.nspname=current_schema()
            GROUP BY rel.relname
        """)).all()
        for table, count in unvalidated:
            _issue(report, "inspection", "unvalidated_foreign_key", table=table, count=int(count))
        for table, constraints in foreign_keys.items():
            for foreign in constraints:
                if str(foreign.get("options", {}).get("match", "SIMPLE")).upper() not in {"SIMPLE", "NONE"}:
                    _issue(report, "inspection", "unsupported_foreign_key_match", table=table)
                    continue
                child, parent = foreign["constrained_columns"], foreign["referred_columns"]
                conditions = " AND ".join("c." + quote(name) + " IS NOT NULL" for name in child)
                equality = " AND ".join("p." + quote(target) + "=c." + quote(source) for source, target in zip(child, parent, strict=False))
                query = "SELECT COUNT(*) FROM " + table_sql(table) + " c WHERE " + conditions + " AND NOT EXISTS (SELECT 1 FROM "
                query += table_sql(foreign["referred_table"], foreign.get("referred_schema") or schema) + " p WHERE " + equality + ")"
                count = int((await connection.exec_driver_sql(query)).scalar_one())
                if count:
                    _issue(report, "physical_foreign_keys", "foreign_key_violations", table=table, columns=child, count=count)
    for index in await _keys(connection, schema, tables, quote):
        table = index["table"]
        try:
            if index["unsupported"]:
                raise ValueError("unsupported key")
            if index.get("student_expression") and "organization_id" not in uuid_key_columns.get(table, set()):
                raise ValueError("student expression requires mapped UUID semantics")
            partial = _known_predicate(table, index["name"], index["columns"], index["predicate"], dialect)
            query = "SELECT " + ",".join(quote(column) for column in index["columns"]) + " FROM " + table_sql(table)
            if partial:
                query += " WHERE " + quote(partial[0]) + partial[1]
            groups = defaultdict(int)
            for row in (await connection.exec_driver_sql(query)).all():
                if any(value is None for value in row):
                    continue
                groups[tuple(_key(value, column in uuid_key_columns.get(table, set())) for column, value in zip(index["columns"], row, strict=False))] += 1
            duplicate_groups = sum(count > 1 for count in groups.values())
            if duplicate_groups:
                _issue(report, "canonical_keys", "canonical_key_collisions", table=table, columns=index["columns"], count=duplicate_groups)
        except (ValueError, TypeError):
            _issue(report, "canonical_keys", "unsupported_unique_comparison", table=table)


async def inspect_release_integrity(engine, metadata, *, expected_revision=None, max_scan_rows=250_000):
    """Inspect one consistent read-only snapshot; caller supplies the real metadata.

    Scope is all physical tables in SQLite main / PostgreSQL current_schema().
    Checks are incomplete and ready=False after any query/inspection failure,
    unsupported comparison or aggregate table-row budget overflow. No exception
    text, identifiers of data rows, values, credentials or SQL parameters escape.
    """
    report = {"ready": False, "schema_current": None, "snapshot_read_only": False,
        "checks": {name: {"ok": True, "count": 0} for name in _CHECKS}, "issues": [],
        "tables_checked": 0, "table_rows_checked": 0,
        "max_scan_rows": max_scan_rows if isinstance(max_scan_rows, int) and not isinstance(max_scan_rows, bool) else None,
        "complete": False, "unsupported_count": 0}
    if isinstance(max_scan_rows, bool) or not isinstance(max_scan_rows, int) or max_scan_rows < 1:
        _issue(report, "inspection", "invalid_row_budget")
        for check in report["checks"].values():
            check["ok"] = False
        return report
    try:
        async with engine.connect() as connection:
            dialect = connection.dialect.name
            if dialect not in {"sqlite", "postgresql"}:
                _issue(report, "inspection", "unsupported_dialect")
                report["unsupported_count"] = 1
                for check in report["checks"].values():
                    check["ok"] = False
                return report
            if dialect == "sqlite":
                previous = (await connection.exec_driver_sql("PRAGMA query_only")).scalar_one()
                await connection.rollback()
                try:
                    await connection.exec_driver_sql("PRAGMA query_only=ON")
                    await connection.exec_driver_sql("BEGIN")
                    report["snapshot_read_only"] = (await connection.exec_driver_sql("PRAGMA query_only")).scalar_one() == 1
                    await _scan(connection, metadata, report, expected_revision, max_scan_rows)
                finally:
                    await connection.rollback()
                    await connection.exec_driver_sql("PRAGMA query_only=" + ("ON" if previous else "OFF"))
                    await connection.rollback()
            else:
                original = connection.sync_connection.get_execution_options()
                await connection.execution_options(isolation_level="REPEATABLE READ", postgresql_readonly=True)
                try:
                    async with connection.begin():
                        report["snapshot_read_only"] = (await connection.exec_driver_sql("SHOW transaction_read_only")).scalar_one() == "on"
                        if (await connection.exec_driver_sql("SHOW transaction_isolation")).scalar_one() != "repeatable read":
                            _issue(report, "inspection", "snapshot_isolation_unavailable")
                        await _scan(connection, metadata, report, expected_revision, max_scan_rows)
                finally:
                    await connection.rollback()
                    await connection.execution_options(isolation_level=original.get("isolation_level", connection.default_isolation_level), postgresql_readonly=original.get("postgresql_readonly", False))
    except Exception:
        _issue(report, "inspection", "inspection_failed")
    report["unsupported_count"] = sum(issue["count"] for issue in report["issues"] if issue["reason"].startswith("unsupported_"))
    report["complete"] = report["snapshot_read_only"] and not report["unsupported_count"] and not any(issue["check"] == "inspection" for issue in report["issues"])
    if not report["complete"]:
        for check in report["checks"].values():
            check["ok"] = False
    report["ready"] = report["snapshot_read_only"] and not report["issues"] and (expected_revision is None or report["schema_current"] is True)
    return report
