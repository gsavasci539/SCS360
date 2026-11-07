"""Exercise 034-shaped checkout data through 035 without rewriting old values."""
from datetime import date
import hashlib
import importlib.util
import json
from pathlib import Path
from uuid import uuid4

from alembic.migration import MigrationContext
from alembic.operations import Operations
import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

from app.core.uuid_type import CustomUUID
from app.infrastructure.models.models import Debt, DebtType
from test_parent_homework_outbox import portal_db  # noqa: F401


async def test_035_preserves_every_old_column_and_scopes_provider_references(portal_db):
    sessions, data = portal_db
    async with sessions() as db:
        debt = Debt(organization_id=data["org"].id, branch_id=data["branch"].id,
            student_id=data["children"][0].id, debt_type=DebtType.EDUCATION, amount=100, paid_amount=25, due_date=date(2026, 11, 1))
        db.add(debt); await db.commit()

        def migrate(connection):
            connection.execute(sa.text("DROP TABLE payment_checkouts"))
            connection.execute(sa.text("DROP TABLE school_payment_merchants"))
            metadata = sa.MetaData()
            for name in ("organizations", "users", "debts", "payments"):
                sa.Table(name, metadata, autoload_with=connection)
            old = sa.Table("payment_checkouts", metadata,
                sa.Column("id", CustomUUID(), primary_key=True),
                sa.Column("organization_id", CustomUUID(), sa.ForeignKey("organizations.id"), nullable=False),
                sa.Column("debt_id", CustomUUID(), sa.ForeignKey("debts.id"), nullable=False),
                sa.Column("created_by", CustomUUID(), sa.ForeignKey("users.id"), nullable=False),
                sa.Column("amount", sa.Numeric(12, 2), nullable=False),
                sa.Column("currency", sa.String(3), nullable=False, server_default="TRY"),
                sa.Column("token_hash", sa.String(64), unique=True),
                sa.Column("provider_payment_id", sa.String(100), unique=True),
                sa.Column("payment_id", CustomUUID(), sa.ForeignKey("payments.id"), unique=True),
                sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
                sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
                sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
            old.create(connection)
            identifier = uuid4()
            connection.execute(old.insert().values(id=identifier, organization_id=data["org"].id, debt_id=debt.id,
                created_by=data["user"].id, amount="25.00", token_hash="legacy-token-hash", provider_payment_id="provider-old", status="COMPLETED"))
            # A historical 32-hex key stays byte-for-byte intact on SQLite.
            if connection.dialect.name == "sqlite":
                connection.execute(sa.text("UPDATE payment_checkouts SET organization_id = :value WHERE id = :identifier"),
                    {"value": data["org"].id.hex, "identifier": str(identifier)})
            tables = sa.inspect(connection).get_table_names()
            columns = {name: [column["name"] for column in sa.inspect(connection).get_columns(name)] for name in tables}

            def manifest():
                result = {}
                for name, names in columns.items():
                    quoted = ", ".join('"' + column + '"' for column in names)
                    rows = connection.execute(sa.text('SELECT ' + quoted + ' FROM "' + name + '"')).fetchall()
                    encoded = sorted(json.dumps(list(row), default=str, sort_keys=True, ensure_ascii=False) for row in rows)
                    result[name] = (len(rows), hashlib.sha256("\n".join(encoded).encode()).hexdigest())
                return result

            before = manifest()
            module_path = Path(__file__).resolve().parents[2] / "alembic/versions/035_school_payment_merchants.py"
            spec = importlib.util.spec_from_file_location("school_merchant_migration_035", module_path)
            module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
            with Operations.context(MigrationContext.configure(connection)):
                module.upgrade(); module.upgrade()
            assert manifest() == before
            scope = connection.execute(sa.text("SELECT merchant_scope FROM payment_checkouts")).scalar_one()
            assert scope == "legacy:" + str(data["org"].id)
            assert connection.execute(sa.text("SELECT COUNT(*) FROM school_payment_merchants")).scalar_one() == 0
            checkout = sa.Table("payment_checkouts", sa.MetaData(), autoload_with=connection)
            account = sa.Table("school_payment_merchants", sa.MetaData(), autoload_with=connection)
            account_id = uuid4()
            def native(value):
                return str(value) if connection.dialect.name == "sqlite" else value
            connection.execute(account.insert().values(id=native(account_id), organization_id=native(data["org"].id), is_current=True,
                enabled=False, environment="LIVE", created_by=native(data["user"].id), updated_by=native(data["user"].id)))
            common = {"organization_id": native(data["org"].id), "debt_id": native(debt.id), "created_by": native(data["user"].id),
                "amount": "25.00", "currency": "TRY", "status": "PENDING"}
            connection.execute(checkout.insert().values(id=native(uuid4()), merchant_scope="school:"+str(account_id), provider_payment_id="provider-old", **common))
            with pytest.raises(IntegrityError):
                with connection.begin_nested():
                    connection.execute(checkout.insert().values(id=native(uuid4()), merchant_scope="school:"+str(account_id), provider_payment_id="provider-old", **common))
            with pytest.raises(IntegrityError):
                with connection.begin_nested():
                    connection.execute(account.insert().values(id=native(uuid4()), organization_id=native(data["org"].id), is_current=True,
                        enabled=False, environment="LIVE", created_by=native(data["user"].id), updated_by=native(data["user"].id)))
            connection.execute(account.insert().values(id=native(uuid4()), organization_id=native(data["org"].id), is_current=False,
                enabled=False, environment="SANDBOX", created_by=native(data["user"].id), updated_by=native(data["user"].id)))

        await (await db.connection()).run_sync(migrate)
        await db.commit()
