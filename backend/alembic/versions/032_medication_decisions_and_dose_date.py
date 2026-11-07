"""Keep medication decisions and each day's dose history explicit."""
from alembic import op
import sqlalchemy as sa

revision = "032"
down_revision = "031"
branch_labels = None
depends_on = None


def upgrade():
    db = op.get_bind()
    inspector = sa.inspect(db)
    if "request_status" not in {row["name"] for row in inspector.get_columns("medication_schedules")}:
        op.add_column("medication_schedules", sa.Column("request_status", sa.String(20), nullable=True))
    if "scheduled_date" not in {row["name"] for row in inspector.get_columns("medication_logs")}:
        op.add_column("medication_logs", sa.Column("scheduled_date", sa.Date(), nullable=True))
    if "uq_medication_log_dose" not in {row["name"] for row in sa.inspect(db).get_indexes("medication_logs")}:
        op.create_index("uq_medication_log_dose", "medication_logs", ["schedule_id", "scheduled_date", "scheduled_time"], unique=True)
    # Legacy decisions and intended dose dates are not recoverable reliably.
    # Leave NULL; compatibility reads use the old state and school-day bounds.
    # Duplicate legacy records remain intact because their dose date is NULL.


def downgrade():
    op.drop_index("uq_medication_log_dose", table_name="medication_logs")
    op.drop_column("medication_logs", "scheduled_date")
    op.drop_column("medication_schedules", "request_status")
