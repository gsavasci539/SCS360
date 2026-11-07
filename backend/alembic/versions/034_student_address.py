"""Persist the student's existing address form without changing old records."""
from alembic import op
import sqlalchemy as sa

revision = "034"
down_revision = "033"
branch_labels = None
depends_on = None


def upgrade():
    if "address" not in {column["name"] for column in sa.inspect(op.get_bind()).get_columns("students")}:
        op.add_column("students", sa.Column("address", sa.String(500), nullable=True))


def downgrade():
    op.drop_column("students", "address")
