"""Persist the previously missing material submission model."""
from alembic import op
import sqlalchemy as sa
from app.core.uuid_type import CustomUUID

revision = "028"
down_revision = "027"
branch_labels = None
depends_on = None


def upgrade():
    if "material_submissions" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table("material_submissions",
        sa.Column("id", CustomUUID(), primary_key=True),
        sa.Column("organization_id", CustomUUID(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("branch_id", CustomUUID(), sa.ForeignKey("branches.id"), nullable=False),
        sa.Column("material_id", CustomUUID(), sa.ForeignKey("course_materials.id"), nullable=False),
        sa.Column("student_id", CustomUUID(), sa.ForeignKey("students.id"), nullable=False),
        sa.Column("submission_text", sa.Text()), sa.Column("file_url", sa.String(500)),
        sa.Column("status", sa.String(20), nullable=False, server_default="SUBMITTED"),
        sa.Column("grade", sa.Numeric(5, 2)), sa.Column("feedback", sa.Text()),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("graded_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("material_id", "student_id"),
    )


def downgrade():
    op.drop_table("material_submissions")
