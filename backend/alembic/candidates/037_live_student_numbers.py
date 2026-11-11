"""Candidate 037: archive-aware numbers; not an installed Alembic revision yet."""
import hashlib
import json
import re

import sqlalchemy as sa

from alembic import op

revision = "037"
down_revision = "036"
branch_labels = depends_on = None
INDEX = "uq_students_org_student_number_live"
INDEX_SQL = ("CREATE UNIQUE INDEX " + INDEX + " ON students "
    "(lower(replace(organization_id, '-', '')), student_number) WHERE deleted_at IS NULL")
KNOWN_SQLITE_DDL = {
    "ea0a7b14028613757a07caeed4e76da480980f9276d0060706e99224697886f3",  # preserved legacy 036
    "53a3fc7e2feaa3256dbdf358b230bfe033283b623b4fd188d49bb519551e5ee3",  # fresh pre-037 model
}
UNIQUE = "\tUNIQUE (organization_id, student_number), \n"


def quote(name):
    return '"' + name.replace('"', '""') + '"'


def typed(value):
    if isinstance(value, bytes):
        return ["bytes", value.hex()]
    if isinstance(value, float):
        return ["float", value.hex()]
    if value is None or isinstance(value, str | int):
        return [type(value).__name__, value]
    raise RuntimeError("037 encountered an unsupported SQLite storage value")


def manifest(connection):
    result, total = {}, 0
    for table in sa.inspect(connection).get_table_names():
        columns = connection.exec_driver_sql("PRAGMA table_xinfo(" + quote(table) + ")").all()
        if any(column[1].lower() in {"rowid", "_rowid_", "oid"} or column[6] for column in columns):
            raise RuntimeError("037 requires review of hidden/generated columns")
        count = connection.exec_driver_sql("SELECT count(*) FROM " + quote(table)).scalar_one()
        total += count
        if total > 250_000:
            raise RuntimeError("037 preservation scan exceeds its bounded row budget")
        digest = hashlib.sha256()
        for row in connection.exec_driver_sql("SELECT rowid,* FROM " + quote(table) + " ORDER BY rowid"):
            digest.update(json.dumps([typed(value) for value in row], ensure_ascii=True, separators=(",", ":")).encode())
            digest.update(b"\n")
        result[table] = (count, digest.hexdigest())
    return result


def objects(connection):
    return [tuple(row) for row in connection.exec_driver_sql("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name")]


def collisions(connection, sqlite):
    organization = "lower(replace(organization_id,'-',''))" if sqlite else "organization_id"
    return connection.exec_driver_sql("SELECT count(*) FROM (SELECT " + organization + ",student_number FROM students "
        "WHERE deleted_at IS NULL AND student_number IS NOT NULL GROUP BY " + organization
        + ",student_number HAVING count(*)>1) AS duplicate_numbers").scalar_one()


def sqlite_upgrade():
    context = op.get_context()
    # Alembic owns the per-migration transaction. FK mode cannot be changed
    # inside SQLite's transaction; enter autocommit before disabling it.
    with context.autocommit_block():
        connection = op.get_bind()
        old_fk = connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one()
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        try:
            if connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() != 0:
                raise RuntimeError("037 could not safely disable SQLite FK actions")
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            try:
                ddl = connection.execute(sa.text("SELECT sql FROM sqlite_master WHERE type='table' AND name='students'")).scalar_one_or_none()
                if ddl is None:
                    raise RuntimeError("037 requires the existing students table")
                existing = connection.execute(sa.text("SELECT sql FROM sqlite_master WHERE type='index' AND name=:name"), {"name": INDEX}).scalar_one_or_none()
                if existing is not None:
                    if existing != INDEX_SQL or UNIQUE in ddl:
                        raise RuntimeError("037 found an unexpected pre-existing student index")
                    connection.exec_driver_sql("COMMIT")
                    return
                if hashlib.sha256(ddl.encode()).hexdigest() not in KNOWN_SQLITE_DDL or ddl.count(UNIQUE) != 1:
                    raise RuntimeError("037 students DDL is unknown; reviewed backup/upgrade required")
                if collisions(connection, True):
                    raise RuntimeError("037 found conflicting unarchived student numbers; no rows were changed")
                if connection.execute(sa.text("SELECT count(*) FROM sqlite_master WHERE name='_students_037'")).scalar_one():
                    raise RuntimeError("037 temporary table name already exists")
                before = manifest(connection)
                schema = objects(connection)
                before_fk = sorted(tuple(row) for row in connection.exec_driver_sql("PRAGMA foreign_key_check"))
                indexes = connection.exec_driver_sql("PRAGMA index_list(students)").all()
                target = []
                for index in indexes:
                    names = [row[2] for row in connection.exec_driver_sql("PRAGMA index_info(" + quote(index[1]) + ")")]
                    if index[3] == "u" and names == ["organization_id", "student_number"]:
                        target.append(index[1])
                if len(target) != 1:
                    raise RuntimeError("037 could not identify exactly one old number constraint")
                connection.exec_driver_sql(ddl.replace("CREATE TABLE students (", 'CREATE TABLE "_students_037" (', 1).replace(UNIQUE, "", 1))
                names = ",".join(quote(row[1]) for row in connection.exec_driver_sql("PRAGMA table_info(students)"))
                connection.exec_driver_sql('INSERT INTO "_students_037" (rowid,' + names + ') SELECT rowid,' + names + ' FROM students')
                connection.exec_driver_sql("DROP TABLE students")
                connection.exec_driver_sql('ALTER TABLE "_students_037" RENAME TO "students"')
                for kind, _, table, sql in schema:
                    if table == "students" and kind in {"index", "trigger"} and sql is not None:
                        connection.exec_driver_sql(sql)
                connection.exec_driver_sql(INDEX_SQL)
                ignored = {("table", "students"), ("index", target[0]), ("index", INDEX)}
                def stable(values):
                    return [row for row in values if row[:2] not in ignored]
                if manifest(connection) != before or stable(objects(connection)) != stable(schema):
                    raise RuntimeError("037 preservation comparison failed; transaction rolled back")
                if sorted(tuple(row) for row in connection.exec_driver_sql("PRAGMA foreign_key_check")) != before_fk:
                    raise RuntimeError("037 changed the existing FK manifest; transaction rolled back")
                if connection.exec_driver_sql("PRAGMA integrity_check").scalars().all() != ["ok"]:
                    raise RuntimeError("037 SQLite integrity check failed")
                connection.exec_driver_sql("COMMIT")
            except BaseException:
                connection.exec_driver_sql("ROLLBACK")
                raise
        finally:
            connection.exec_driver_sql("PRAGMA foreign_keys=" + str(old_fk))
            if connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() != old_fk:
                raise RuntimeError("037 could not restore the connection FK mode")


def upgrade():
    if op.get_context().as_sql:
        raise RuntimeError("037 requires an online preservation inspection")
    connection = op.get_bind()
    if connection.dialect.name == "sqlite":
        return sqlite_upgrade()
    if connection.dialect.name != "postgresql":
        raise RuntimeError("037 supports only SQLite and PostgreSQL")
    inspector = sa.inspect(connection)
    columns = {item["name"]: item["type"] for item in inspector.get_columns("students")}
    if not isinstance(columns.get("organization_id"), sa.Uuid) or str(columns.get("student_number")) != "VARCHAR(50)":
        raise RuntimeError("037 requires native PostgreSQL UUID/literal number semantics")
    constraints = [item for item in inspector.get_unique_constraints("students")
        if item["column_names"] == ["organization_id", "student_number"]]
    indexes = [item for item in inspector.get_indexes("students") if item["name"] == INDEX]
    if indexes:
        index = indexes[0]
        predicate = str(index.get("dialect_options", {}).get("postgresql_where", ""))
        if (constraints or not index["unique"] or index["column_names"] != ["organization_id", "student_number"]
            or index.get("dialect_options", {}).get("postgresql_ops")
            or index.get("dialect_options", {}).get("postgresql_nulls_not_distinct")
            or not re.fullmatch(r'\(?"?deleted_at"? IS NULL\)?', predicate)):
            raise RuntimeError("037 found an unexpected pre-existing student index")
        return
    if len(constraints) != 1 or not constraints[0]["name"]:
        raise RuntimeError("037 requires exactly one known legacy number constraint")
    if collisions(connection, False):
        raise RuntimeError("037 found conflicting unarchived student numbers; no rows were changed")
    op.drop_constraint(constraints[0]["name"], "students", type_="unique")
    op.create_index(INDEX, "students", ["organization_id", "student_number"], unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"))


def downgrade():
    raise RuntimeError("037 geri dönüşü doğrulanmış veritabanı yedeğinden yapılmalıdır; arşiv geçmişi silinemez")
