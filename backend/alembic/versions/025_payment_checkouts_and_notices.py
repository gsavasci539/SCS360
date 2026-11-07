"""Durable payment reconciliation and parent requests."""
from alembic import op
import sqlalchemy as sa
from app.core.uuid_type import CustomUUID

revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None


def timestamps():
    return [sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)]


def upgrade():
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if set(["payment_checkouts","parent_notices"]).issubset(existing):
        return
    op.create_table("payment_checkouts",
        sa.Column("id", CustomUUID(), primary_key=True),
        sa.Column("organization_id", CustomUUID(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("debt_id", CustomUUID(), sa.ForeignKey("debts.id"), nullable=False),
        sa.Column("created_by", CustomUUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="TRY"),
        sa.Column("token_hash", sa.String(64), unique=True),
        sa.Column("provider_payment_id", sa.String(100), unique=True),
        sa.Column("payment_id", CustomUUID(), sa.ForeignKey("payments.id"), unique=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"), *timestamps())
    op.create_table("parent_notices",
        sa.Column("id", CustomUUID(), primary_key=True),
        sa.Column("organization_id", CustomUUID(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("student_id", CustomUUID(), sa.ForeignKey("students.id"), nullable=False),
        sa.Column("created_by", CustomUUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type", sa.String(50), nullable=False), sa.Column("description", sa.Text()),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("deleted_at", sa.DateTime(timezone=True)), *timestamps())


def downgrade():
    op.drop_table("parent_notices")
    op.drop_table("payment_checkouts")
