"""Persist appointments and teacher availability."""
import sqlalchemy as sa
from alembic import op

revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade():
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if set(["appointments","appointment_time_slots"]).issubset(existing):
        return
    from app.core.uuid_type import CustomUUID
    op.create_table("appointments",
        sa.Column("id", CustomUUID(), primary_key=True),
        sa.Column("organization_id", CustomUUID(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("teacher_id", CustomUUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("student_id", CustomUUID(), sa.ForeignKey("students.id"), nullable=False),
        sa.Column("parent_id", CustomUUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("slot_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("status", sa.String(30), nullable=False, server_default="CONFIRMED"),
        sa.Column("parent_note", sa.Text()), sa.Column("teacher_note", sa.Text()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table("appointment_time_slots",
        sa.Column("id", CustomUUID(), primary_key=True),
        sa.Column("teacher_id", CustomUUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False), sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("appointment_time_slots")
    op.drop_table("appointments")
