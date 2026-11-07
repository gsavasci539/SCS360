import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, text

from test_parent_homework_outbox import portal_db  # noqa: F401


async def test_033_only_adds_empty_commercial_tables_and_preserves_existing_data(portal_db):
    sessions, data = portal_db
    async with sessions() as db:
        def migrate(connection):
            for name in ("subscription_checkouts", "subscription_invoices", "organization_subscriptions", "subscription_plans"):
                connection.execute(text("DROP TABLE " + name))
            tables = inspect(connection).get_table_names()
            before = {name: connection.execute(text('SELECT COUNT(*) FROM "' + name + '"')).scalar() for name in tables}
            accounts = connection.execute(text("SELECT id, email, password_hash FROM users ORDER BY email")).fetchall()
            with Operations.context(MigrationContext.configure(connection)):
                path = Path(__file__).resolve().parents[2] / "alembic/versions/033_saas_memberships.py"
                spec = importlib.util.spec_from_file_location("migration033", path)
                module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
                module.upgrade(); module.upgrade()
            for name, count in before.items():
                assert connection.execute(text('SELECT COUNT(*) FROM "' + name + '"')).scalar() == count
            assert connection.execute(text("SELECT id, email, password_hash FROM users ORDER BY email")).fetchall() == accounts
            for name in ("subscription_checkouts", "subscription_invoices", "organization_subscriptions", "subscription_plans"):
                assert connection.execute(text("SELECT COUNT(*) FROM " + name)).scalar() == 0
        await (await db.connection()).run_sync(migrate)
        await db.commit()
