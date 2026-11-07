import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, select, text

from test_parent_homework_outbox import portal_db  # noqa: F401
from app.core.dates import school_today
from app.domain.entities.consents import ConsentDocument
from app.domain.entities.surveys import Survey
from app.infrastructure.models.models import Permission, Role, RolePermission, User


async def test_029_backfills_unambiguous_owners_and_preserves_custom_roles(portal_db):
    sessions, data = portal_db
    async with sessions() as db:
        doc = ConsentDocument(title="Legacy document", document_type="TEST", content="Keep terms", effective_date=school_today(), created_by=data["teacher"].id)
        survey = Survey(title="Legacy survey", start_date=school_today(), end_date=school_today(), created_by=data["teacher"].id)
        builtin = Role(name="Builtin parent", slug="parent", is_system=True)
        db.add_all([doc, survey, builtin]); await db.commit()
        account_snapshot = (await db.execute(select(User.id, User.email, User.password_hash))).all()
        role_snapshot = (await db.execute(select(RolePermission.role_id, RolePermission.permission_id))).all()
        connection = await db.connection()
        def migrate(sync):
            with Operations.context(MigrationContext.configure(sync)) as operations:
                for table in ("surveys", "consent_documents"):
                    fk = next(item for item in inspect(sync).get_foreign_keys(table) if item["constrained_columns"] == ["organization_id"])
                    with operations.batch_alter_table(table, naming_convention={"fk": "fk_%(table_name)s_%(column_0_name)s"}) as batch:
                        batch.drop_index(f"ix_{table}_organization_id")
                        batch.drop_constraint(fk["name"] or f"fk_{table}_organization_id", type_="foreignkey")
                        batch.drop_column("organization_id")
                path = Path(__file__).resolve().parents[2] / "alembic/versions/029_form_ownership_and_parent_consent.py"
                spec = importlib.util.spec_from_file_location("migration029", path)
                module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
                module.upgrade()
                # Fresh installations with current metadata can pass this migration too.
                module.upgrade()
        await connection.run_sync(migrate)
        await db.commit()
        assert (await db.execute(select(ConsentDocument.organization_id))).scalar_one() == data["org"].id
        assert (await db.execute(select(Survey.organization_id))).scalar_one() == data["org"].id
        assert (await db.execute(select(User.id, User.email, User.password_hash))).all() == account_snapshot
        permission = (await db.execute(select(Permission).where(Permission.code == "parent.give_consent"))).scalar_one()
        links = (await db.execute(select(RolePermission.role_id, RolePermission.permission_id))).all()
        assert set(links) - set(role_snapshot) == {(builtin.id, permission.id)}
        assert set(role_snapshot).issubset(set(links))
        assert (await db.execute(text("SELECT content FROM consent_documents"))).scalar_one() == "Keep terms"
