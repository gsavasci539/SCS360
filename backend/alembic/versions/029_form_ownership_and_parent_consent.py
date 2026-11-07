"""Persist form ownership and add a separate guardian decision permission.

Unattributable legacy forms remain NULL and visible only to platform admins.
No custom role, account, password, decision or legacy UUID is rewritten.
"""
from uuid import uuid4

from alembic import op
import sqlalchemy as sa

from app.infrastructure.models.models import CustomUUID

revision = "029"
down_revision = "028"
branch_labels = None
depends_on = None


def upgrade():
    db = op.get_bind()
    for table in ("surveys", "consent_documents"):
        if "organization_id" not in {column["name"] for column in sa.inspect(db).get_columns(table)}:
            with op.batch_alter_table(table) as batch:
                batch.add_column(sa.Column("organization_id", CustomUUID(), nullable=True))
                batch.create_foreign_key(f"fk_{table}_organization", "organizations", ["organization_id"], ["id"])
                batch.create_index(f"ix_{table}_organization_id", ["organization_id"])
        # Compare historical UUID spellings without changing any stored IDs.
        owner = f"""SELECT DISTINCT o.id FROM users u JOIN organizations o
          ON lower(replace(cast(u.organization_id AS varchar(64)), '-', '')) = lower(replace(cast(o.id AS varchar(64)), '-', ''))
          WHERE lower(replace(cast(u.id AS varchar(64)), '-', '')) = lower(replace(cast({table}.created_by AS varchar(64)), '-', ''))"""
        db.execute(sa.text(f"UPDATE {table} SET organization_id = ({owner}) WHERE organization_id IS NULL AND (SELECT count(*) FROM ({owner}) AS owners) = 1"))
    from app.infrastructure.models.models import Permission, Role, RolePermission
    from app.core.role_catalog import default_permissions
    code = "parent.give_consent"
    permission_id = db.execute(sa.select(Permission.id).where(Permission.code == code)).scalar_one_or_none()
    if permission_id is None:
        permission_id = uuid4()
        db.execute(sa.insert(Permission).values(id=permission_id, code=code, name="Veli onay kararı", module="parent"))
    for role in db.execute(sa.select(Role.__table__).where(Role.is_system.is_(True), Role.organization_id.is_(None), Role.deleted_at.is_(None))):
        if code in default_permissions(role.slug):
            exists = db.execute(sa.select(RolePermission.role_id).where(RolePermission.role_id == role.id, RolePermission.permission_id == permission_id)).first()
            if not exists:
                db.execute(sa.insert(RolePermission).values(role_id=role.id, permission_id=permission_id))


def downgrade():
    # Retain configured permission assignments; only ownership columns roll back.
    for table in ("consent_documents", "surveys"):
        with op.batch_alter_table(table) as batch:
            batch.drop_index(f"ix_{table}_organization_id")
            batch.drop_constraint(f"fk_{table}_organization", type_="foreignkey")
            batch.drop_column("organization_id")
