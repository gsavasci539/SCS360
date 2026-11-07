"""Separate guardian survey participation from management permissions."""
from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision = "030"
down_revision = "029"
branch_labels = None
depends_on = None


def upgrade():
    from app.core.database import Base
    from app.domain.entities.surveys import SurveyParticipation
    from app.core.role_catalog import default_permissions
    from app.infrastructure.models.models import Permission, Role, RolePermission
    db = op.get_bind()
    Base.metadata.create_all(bind=db, tables=[SurveyParticipation.__table__], checkfirst=True)
    for code in ("parent.respond_survey", "surveys.respond"):
        permission_id = db.execute(sa.select(Permission.id).where(Permission.code == code)).scalar_one_or_none()
        if permission_id is None:
            permission_id = uuid4()
            db.execute(sa.insert(Permission).values(id=permission_id, code=code, name=code, module=code.split(".")[0]))
        for role in db.execute(sa.select(Role.__table__).where(Role.is_system.is_(True), Role.organization_id.is_(None), Role.deleted_at.is_(None))):
            if code in default_permissions(role.slug):
                exists = db.execute(sa.select(RolePermission.role_id).where(RolePermission.role_id == role.id, RolePermission.permission_id == permission_id)).first()
                if not exists:
                    db.execute(sa.insert(RolePermission).values(role_id=role.id, permission_id=permission_id))


def downgrade():
    op.drop_table("survey_participations")
