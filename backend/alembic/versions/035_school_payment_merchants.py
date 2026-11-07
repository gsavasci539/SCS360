"""School merchant accounts and immutable checkout evidence; preserve old columns."""
from uuid import UUID

from alembic import op
import sqlalchemy as sa

from app.core.uuid_type import CustomUUID

revision = "035"
down_revision = "034"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if "school_payment_merchants" not in inspector.get_table_names():
        op.create_table("school_payment_merchants",
            sa.Column("id", CustomUUID(), primary_key=True),
            sa.Column("organization_id", CustomUUID(), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("environment", sa.String(10), nullable=False),
            sa.Column("credentials_ciphertext", sa.Text(), nullable=True),
            sa.Column("created_by", CustomUUID(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("updated_by", CustomUUID(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
        op.create_index("ix_school_payment_merchants_organization_id", "school_payment_merchants", ["organization_id"])
        op.create_index("uq_school_payment_merchant_current_org", "school_payment_merchants", ["organization_id"], unique=True,
            sqlite_where=sa.text("is_current = 1"), postgresql_where=sa.text("is_current IS TRUE"))
    inspector = sa.inspect(connection)
    existing = {column["name"] for column in inspector.get_columns("payment_checkouts")}
    additions = [sa.Column("merchant_account_id", CustomUUID(), nullable=True), sa.Column("merchant_scope", sa.String(100), nullable=True),
        sa.Column("merchant_snapshot", sa.Text(), nullable=True), sa.Column("request_digest", sa.String(64), nullable=True),
        sa.Column("checkout_secret", sa.Text(), nullable=True), sa.Column("provider_transaction_id", sa.String(255), nullable=True),
        sa.Column("paid_amount", sa.Numeric(12, 2), nullable=True), sa.Column("paid_currency", sa.String(3), nullable=True),
        sa.Column("verified_metadata", sa.JSON(), nullable=True), sa.Column("review_reason", sa.String(255), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True)]
    uniques = inspector.get_unique_constraints("payment_checkouts")
    old_unique = [item for item in uniques if item["column_names"] == ["provider_payment_id"]]
    compound = any(item["column_names"] == ["merchant_scope", "provider_payment_id"] for item in uniques)
    missing = [column for column in additions if column.name not in existing]
    if missing or old_unique or not compound:
        with op.batch_alter_table("payment_checkouts", naming_convention={"uq": "uq_%(table_name)s_%(column_0_name)s"}) as batch:
            for column in missing:
                batch.add_column(column)
            if "merchant_account_id" not in existing:
                batch.create_foreign_key("fk_checkout_school_payment_merchant", "school_payment_merchants", ["merchant_account_id"], ["id"])
            for item in old_unique:
                batch.drop_constraint(item["name"] or "uq_payment_checkouts_provider_payment_id", type_="unique")
            if not compound:
                batch.create_unique_constraint("uq_payment_checkout_merchant_provider", ["merchant_scope", "provider_payment_id"])
    # Read raw IDs and write only the new scope. This never normalizes old IDs.
    rows = connection.execute(sa.text("SELECT id, organization_id FROM payment_checkouts WHERE merchant_scope IS NULL")).all()
    for identifier, organization_id in rows:
        try:
            canonical = str(UUID(str(organization_id)))
        except (TypeError, ValueError, AttributeError):
            canonical = str(organization_id)
        connection.execute(sa.text("UPDATE payment_checkouts SET merchant_scope = :scope WHERE id = :identifier"),
            {"scope": "legacy:" + canonical, "identifier": identifier})


def downgrade():
    # Global uniqueness is unsafe to restore after different accounts reuse a
    # reference. Restore a matching pre-035 backup instead of merging payments.
    raise RuntimeError("035 geri dönüşü, uyumlu uygulama sürümüyle doğrulanmış veritabanı yedeğinden yapılmalıdır")
