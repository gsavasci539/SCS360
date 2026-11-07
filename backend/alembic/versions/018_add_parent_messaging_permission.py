"""Grant the parent messaging permission to the system parent role."""

import uuid

from alembic import op
import sqlalchemy as sa
from app.core.uuid_type import CustomUUID


revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    permissions = sa.table(
        "permissions",
        sa.column("id", CustomUUID()), sa.column("code", sa.String), sa.column("name", sa.String),
        sa.column("module", sa.String), sa.column("description", sa.String),
    )
    roles = sa.table("roles", sa.column("id", CustomUUID()), sa.column("slug", sa.String))
    role_permissions = sa.table(
        "role_permissions", sa.column("role_id", CustomUUID()), sa.column("permission_id", CustomUUID())
    )
    permission_id = conn.execute(
        sa.select(permissions.c.id).where(permissions.c.code == "parent.send_message")
    ).scalar_one_or_none()
    if permission_id is None:
        permission_id = str(uuid.uuid4())
        op.bulk_insert(permissions, [{
            "id": permission_id,
            "code": "parent.send_message",
            "name": "Öğretmene Mesaj Gönder",
            "module": "parent",
            "description": "Velinin sadece çocuğunun atanmış öğretmenleriyle mesajlaşması",
        }])

    parent_role_ids = conn.execute(sa.select(roles.c.id).where(roles.c.slug == "parent")).scalars().all()
    for role_id in parent_role_ids:
        exists = conn.execute(
            sa.select(role_permissions.c.role_id).where(
                role_permissions.c.role_id == role_id,
                role_permissions.c.permission_id == permission_id,
            )
        ).scalar_one_or_none()
        if exists is None:
            op.bulk_insert(role_permissions, [{"role_id": role_id, "permission_id": permission_id}])


def downgrade() -> None:
    conn = op.get_bind()
    permission_id = conn.execute(
        sa.text("SELECT id FROM permissions WHERE code = 'parent.send_message'")
    ).scalar_one_or_none()
    if permission_id is not None:
        conn.execute(sa.text("DELETE FROM role_permissions WHERE permission_id = :permission_id"), {"permission_id": permission_id})
        conn.execute(sa.text("DELETE FROM permissions WHERE id = :permission_id"), {"permission_id": permission_id})
