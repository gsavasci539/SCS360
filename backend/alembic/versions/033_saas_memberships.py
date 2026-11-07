"""Add commercial configuration without rewriting existing accounts or school data."""
from alembic import op
import sqlalchemy as sa
from app.core.uuid_type import CustomUUID

revision = "033"
down_revision = "032"
branch_labels = None
depends_on = None


def upgrade():
    db = op.get_bind()
    if not sa.inspect(db).has_table("subscription_plans"):
        op.create_table("subscription_plans",
            sa.Column("id", CustomUUID(), primary_key=True), sa.Column("code", sa.String(50), unique=True, nullable=False),
            sa.Column("name", sa.String(120), nullable=False),
            *[sa.Column(key, sa.Integer(), nullable=False) for key in ("branch_limit", "student_limit", "user_limit")],
            sa.Column("price", sa.Numeric(12, 2), nullable=False), sa.Column("currency", sa.String(3), nullable=False),
            sa.Column("period_months", sa.Integer(), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    if not sa.inspect(db).has_table("organization_subscriptions"):
        op.create_table("organization_subscriptions",
            sa.Column("organization_id", CustomUUID(), sa.ForeignKey("organizations.id"), primary_key=True),
            sa.Column("plan_id", CustomUUID(), sa.ForeignKey("subscription_plans.id")),
            sa.Column("owner_user_id", CustomUUID(), sa.ForeignKey("users.id")),
            sa.Column("admin_status", sa.String(20), nullable=False),
            sa.Column("period_start", sa.DateTime(timezone=True)), sa.Column("period_end", sa.DateTime(timezone=True)),
            sa.Column("package_snapshot", sa.JSON()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    if not sa.inspect(db).has_table("subscription_invoices"):
        op.create_table("subscription_invoices",
            sa.Column("id", CustomUUID(), primary_key=True),
            sa.Column("organization_id", CustomUUID(), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("plan_id", CustomUUID(), sa.ForeignKey("subscription_plans.id"), nullable=False),
            sa.Column("created_by", CustomUUID(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("package_snapshot", sa.JSON(), nullable=False), sa.Column("amount", sa.Numeric(12, 2), nullable=False),
            sa.Column("currency", sa.String(3), nullable=False), sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
            sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
            sa.Column("base_period_end", sa.DateTime(timezone=True)), sa.Column("base_membership_digest", sa.String(64), nullable=False),
            sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column("payment_reference", sa.String(255), unique=True), sa.Column("paid_at", sa.DateTime(timezone=True)),
            sa.Column("settled_by", CustomUUID(), sa.ForeignKey("users.id")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
        op.create_index("ix_subscription_invoices_organization_id", "subscription_invoices", ["organization_id"])
    if not sa.inspect(db).has_table("subscription_checkouts"):
        op.create_table("subscription_checkouts",
            sa.Column("id", CustomUUID(), primary_key=True),
            sa.Column("organization_id", CustomUUID(), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("invoice_id", CustomUUID(), sa.ForeignKey("subscription_invoices.id"), nullable=False),
            sa.Column("created_by", CustomUUID(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("request_digest", sa.String(64), nullable=False), sa.Column("status", sa.String(20), nullable=False),
            sa.Column("token_hash", sa.String(64), unique=True), sa.Column("checkout_secret", sa.Text()),
            sa.Column("provider_payment_id", sa.String(255), unique=True), sa.Column("provider_transaction_id", sa.String(255)),
            sa.Column("paid_amount", sa.Numeric(12, 2)),
            sa.Column("currency", sa.String(3)),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
        op.create_index("ix_subscription_checkouts_organization_id", "subscription_checkouts", ["organization_id"])
        op.create_index("ix_subscription_checkouts_invoice_id", "subscription_checkouts", ["invoice_id"])
    # Missing old subscriptions remain explicit legacy/unmanaged accounts.
    # Never guess their package, fees, owner, expiry, or payment history.


def downgrade():
    op.drop_table("subscription_checkouts")
    op.drop_table("subscription_invoices")
    op.drop_table("organization_subscriptions")
    op.drop_table("subscription_plans")
