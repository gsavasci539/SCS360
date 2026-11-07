"""Install feature permissions and built-in roles without demo users or data."""
from uuid import uuid4
from alembic import op
from sqlalchemy import insert, select

revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None


def upgrade():
    from app.core.role_catalog import PERMISSION_CODES, ROLE_NAMES, default_permissions
    from app.infrastructure.models.models import Permission, Role, RolePermission
    db = op.get_bind()
    permissions = {row.code: row.id for row in db.execute(select(Permission.__table__))}
    for code in PERMISSION_CODES:
        if code not in permissions:
            identifier = uuid4()
            db.execute(insert(Permission.__table__).values(id=identifier, code=code, name=code, module=code.split(".")[0]))
            permissions[code] = identifier
    existing = db.execute(select(Role.__table__)).all()
    system = {row.slug: row for row in existing if row.organization_id is None and row.is_system}
    for slug, name in ROLE_NAMES.items():
        if slug not in system:
            identifier = uuid4()
            db.execute(insert(Role.__table__).values(id=identifier, name=name, slug=slug, is_system=True))
            role_id = identifier
        else:
            role_id = system[slug].id
        assigned = set(db.execute(select(RolePermission.permission_id).where(RolePermission.role_id == role_id)).scalars())
        for code in default_permissions(slug):
            if permissions[code] not in assigned:
                db.execute(insert(RolePermission.__table__).values(role_id=role_id, permission_id=permissions[code]))


def downgrade():
    # Preserve configured role assignments during rollback.
    pass
