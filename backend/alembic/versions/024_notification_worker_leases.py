"""Durable claims prevent two workers sending the same job concurrently."""
from alembic import op
import sqlalchemy as sa
from app.core.uuid_type import CustomUUID

revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("notification_jobs")}
    if "locked_until" not in columns:
        op.add_column("notification_jobs", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))
    if "lock_token" not in columns:
        op.add_column("notification_jobs", sa.Column("lock_token", CustomUUID(), nullable=True))
    if "ix_notification_jobs_pending" not in {index["name"] for index in inspector.get_indexes("notification_jobs")}:
        op.create_index("ix_notification_jobs_pending", "notification_jobs", ["status", "scheduled_at", "locked_until"])


def downgrade():
    op.drop_index("ix_notification_jobs_pending", table_name="notification_jobs")
    op.drop_column("notification_jobs", "lock_token")
    op.drop_column("notification_jobs", "locked_until")
