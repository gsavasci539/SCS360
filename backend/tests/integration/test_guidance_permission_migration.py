import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import select

from test_parent_homework_outbox import portal_db  # noqa: F401
from app.infrastructure.models.models import Permission, Role, RolePermission


async def test_031_confidential_permission_is_explicit_and_custom_roles_are_preserved(portal_db):
    sessions, _ = portal_db
    async with sessions() as db:
        admin = Role(name="Builtin Admin", slug="org_admin", is_system=True)
        manager = Role(name="Builtin Manager", slug="branch_manager", is_system=True)
        db.add_all([admin, manager]); await db.commit()
        before = set((await db.execute(select(RolePermission.role_id, RolePermission.permission_id))).all())
        def migrate(sync):
            with Operations.context(MigrationContext.configure(sync)):
                spec = importlib.util.spec_from_file_location("migration031", Path(__file__).resolve().parents[2] / "alembic/versions/031_guidance_confidential_permission.py")
                module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
                module.upgrade(); module.upgrade()
        await (await db.connection()).run_sync(migrate); await db.commit()
        permission = (await db.execute(select(Permission).where(Permission.code == "guidance.read_confidential"))).scalar_one()
        after = set((await db.execute(select(RolePermission.role_id, RolePermission.permission_id))).all())
        assert after - before == {(admin.id, permission.id)}
        assert before.issubset(after)
