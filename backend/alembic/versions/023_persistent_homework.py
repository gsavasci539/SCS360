"""Persist class assignments and student submissions."""
import sqlalchemy as sa
from alembic import op
from app.core.uuid_type import CustomUUID

revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade():
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if set(["homework","homework_submissions"]).issubset(existing):
        return
    op.create_table("homework",
        sa.Column("id", CustomUUID(), primary_key=True),
        sa.Column("organization_id", CustomUUID(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("class_id", CustomUUID(), sa.ForeignKey("classes.id")),
        sa.Column("title", sa.String(255), nullable=False), sa.Column("subject", sa.String(100)),
        sa.Column("description", sa.Text()), sa.Column("due_date", sa.Date()),
        sa.Column("attachment_url", sa.String(500)), sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
        sa.Column("created_by", CustomUUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table("homework_submissions",
        sa.Column("id", CustomUUID(), primary_key=True),
        sa.Column("homework_id", CustomUUID(), sa.ForeignKey("homework.id"), nullable=False),
        sa.Column("student_id", CustomUUID(), sa.ForeignKey("students.id"), nullable=False),
        sa.Column("submission_text", sa.Text()), sa.Column("attachment_file_name", sa.String(255)),
        sa.Column("attachment_file_size_mb", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("status", sa.String(30), nullable=False, server_default="SUBMITTED"),
        sa.Column("score", sa.Numeric(5, 2)), sa.Column("teacher_feedback", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("homework_id", "student_id"),
    )


def downgrade():
    op.drop_table("homework_submissions")
    op.drop_table("homework")
