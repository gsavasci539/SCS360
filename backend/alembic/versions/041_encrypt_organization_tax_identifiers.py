"""Encrypt organization tax identifiers and retain keyed lookup fingerprints."""

import sqlalchemy as sa
from alembic import op
from alembic import context

from app.core.config import get_settings
from app.core.tax_identifier import encrypt_tax_identifier, tax_identifier_fingerprint


revision = "041"
down_revision = "040"
branch_labels = depends_on = None


def upgrade() -> None:
    if context.is_offline_mode():
        raise RuntimeError("Organization tax identifier encryption requires an online migration with the encryption key")
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("organizations"):
        return

    columns = {column["name"] for column in inspector.get_columns("organizations")}
    key = None
    if "tax_number" in columns:
        key = get_settings().ORGANIZATION_TAX_NUMBER_ENCRYPTION_KEY
        if not key:
            raise RuntimeError("Set ORGANIZATION_TAX_NUMBER_ENCRYPTION_KEY before migrating organization tax data")

    if "tax_number_ciphertext" not in columns:
        op.add_column("organizations", sa.Column("tax_number_ciphertext", sa.Text(), nullable=True))
    if "tax_number_fingerprint" not in columns:
        op.add_column("organizations", sa.Column("tax_number_fingerprint", sa.String(64), nullable=True))

    if "tax_number" in columns:
        table = sa.Table("organizations", sa.MetaData(), autoload_with=bind)
        seen: set[str] = set()
        rows = bind.execute(
            sa.select(table.c.id, table.c.tax_number).where(table.c.tax_number.is_not(None))
        ).all()
        for organization_id, tax_number in rows:
            fingerprint = tax_identifier_fingerprint(tax_number, key)
            if fingerprint in seen:
                raise RuntimeError(
                    "Duplicate organization tax identifiers must be resolved through an approved secure process"
                )
            seen.add(fingerprint)
            bind.execute(
                table.update()
                .where(table.c.id == organization_id)
                .values(
                    tax_number_ciphertext=encrypt_tax_identifier(tax_number, key),
                    tax_number_fingerprint=fingerprint,
                )
            )

    index_name = "uq_organizations_tax_number_fingerprint"
    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("organizations")}
    if index_name not in indexes:
        op.create_index(index_name, "organizations", ["tax_number_fingerprint"], unique=True)

    if "tax_number" in columns:
        with op.batch_alter_table("organizations") as batch_op:
            batch_op.drop_column("tax_number")


def downgrade() -> None:
    raise RuntimeError(
        "This migration is intentionally irreversible: restore only through an approved encrypted backup procedure"
    )
