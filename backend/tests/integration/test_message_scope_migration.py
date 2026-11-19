import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect


def test_message_scope_upgrade_keeps_existing_records_and_is_repeatable(tmp_path):
    script = Path(__file__).resolve().parents[2] / "alembic" / "versions" / "038_message_scope.py"
    spec = importlib.util.spec_from_file_location("message_scope_migration", script)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_engine(f"sqlite:///{(tmp_path / 'legacy.db').as_posix()}")
    try:
        with engine.begin() as db:
            db.exec_driver_sql("PRAGMA foreign_keys = ON")
            db.exec_driver_sql("CREATE TABLE organizations (id VARCHAR(36) PRIMARY KEY)")
            db.exec_driver_sql("CREATE TABLE branches (id VARCHAR(36) PRIMARY KEY)")
            db.exec_driver_sql("CREATE TABLE chat_messages (id VARCHAR(36) PRIMARY KEY, content TEXT NOT NULL)")
            db.exec_driver_sql("INSERT INTO chat_messages VALUES ('older', 'Eski kayıt')")
            with Operations.context(MigrationContext.configure(db)):
                migration.upgrade()
                migration.upgrade()
            assert db.exec_driver_sql("SELECT * FROM chat_messages").one() == ("older", "Eski kayıt", None, None)
            assert {key["referred_table"] for key in inspect(db).get_foreign_keys("chat_messages")} == {"organizations", "branches"}
    finally:
        engine.dispose()
