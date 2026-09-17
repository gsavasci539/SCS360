"""Seed permissions, demo organization, roles, and the initial admin account."""

from pathlib import Path

import sqlalchemy as sa

from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    seed_file = Path(__file__).resolve().parents[2] / "sql" / "002_seed.sql"
    sql = seed_file.read_text(encoding="utf-8")
    connection = op.get_bind()
    for statement in (part.strip() for part in sql.split(";")):
        if statement:
            connection.execute(sa.text(statement))


def downgrade() -> None:
    # Baseline rows may be referenced by user data; never delete them automatically.
    pass
