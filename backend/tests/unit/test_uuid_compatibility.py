from uuid import uuid4

from sqlalchemy import Column, MetaData, Table, create_engine, select
from sqlalchemy.dialects import postgresql

from app.core.uuid_type import CustomUUID


def test_legacy_uuid_lookup_join_and_membership_preserve_identifiers():
    metadata = MetaData()
    parent = Table("legacy_parent", metadata, Column("id", CustomUUID(), primary_key=True))
    child = Table("legacy_child", metadata, Column("id", CustomUUID(), primary_key=True), Column("parent_id", CustomUUID()))
    identifier, child_id = uuid4(), uuid4()
    engine = create_engine("sqlite://")
    metadata.create_all(engine)
    with engine.begin() as connection:
        connection.exec_driver_sql("INSERT INTO legacy_parent VALUES (?)", (identifier.hex,))
        connection.exec_driver_sql("INSERT INTO legacy_child VALUES (?, ?)", (str(child_id), str(identifier)))
        assert connection.execute(select(parent.c.id).where(parent.c.id == identifier)).scalar() == identifier
        assert connection.execute(select(parent.c.id).where(parent.c.id.in_([identifier]))).scalar() == identifier
        assert connection.execute(select(parent.c.id).where(parent.c.id.in_(select(child.c.parent_id)))).scalar() == identifier
        assert connection.execute(select(child.c.id).join(parent, child.c.parent_id == parent.c.id)).scalar() == child_id
        assert connection.execute(select(parent.c.id).where(parent.c.id.in_([]))).all() == []
    engine.dispose()


def test_postgresql_keeps_native_indexable_uuid_comparison():
    table = Table("records", MetaData(), Column("id", CustomUUID()))
    sql = str(select(table.c.id).where(table.c.id == uuid4()).compile(dialect=postgresql.dialect()))
    assert "replace" not in sql.lower()
