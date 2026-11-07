import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import select

from test_parent_homework_outbox import portal_db  # noqa: F401
from app.domain.entities.surveys import SurveyParticipation
from app.infrastructure.models.models import Permission, Role, RolePermission, User


async def test_030_creates_ledger_and_preserves_custom_role_and_account_state(portal_db):
    sessions, _ = portal_db
    async with sessions() as db:
        parent = Role(name="Builtin Parent", slug="parent", is_system=True)
        teacher = Role(name="Builtin Teacher", slug="teacher", is_system=True)
        db.add_all([parent, teacher]); await db.commit()
        before_links = set((await db.execute(select(RolePermission.role_id, RolePermission.permission_id))).all())
        accounts = (await db.execute(select(User.id, User.email, User.password_hash))).all()
        connection = await db.connection()
        def migrate(sync):
            SurveyParticipation.__table__.drop(sync)
            with Operations.context(MigrationContext.configure(sync)):
                spec = importlib.util.spec_from_file_location("migration030", Path(__file__).resolve().parents[2] / "alembic/versions/030_survey_participation.py")
                module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
                module.upgrade(); module.upgrade()
        await connection.run_sync(migrate); await db.commit()
        permissions = dict((await db.execute(select(Permission.code, Permission.id))).all())
        after_links = set((await db.execute(select(RolePermission.role_id, RolePermission.permission_id))).all())
        assert after_links - before_links == {(parent.id, permissions["parent.respond_survey"]), (teacher.id, permissions["surveys.respond"])}
        assert before_links.issubset(after_links)
        assert (await db.execute(select(User.id, User.email, User.password_hash))).all() == accounts
        assert (await db.execute(select(SurveyParticipation))).scalars().all() == []
