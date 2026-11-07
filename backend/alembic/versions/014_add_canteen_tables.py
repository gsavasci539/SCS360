"""Add canteen products, dietary restrictions, orders, and wallet transactions tables"""

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from alembic import op
    from app.core.database import Base
    # Revision 002 may already have created these tables on a clean install.
    # Use the canonical UUID types on both PostgreSQL and SQLite.
    names = ["canteen_products","canteen_dietary_restrictions","canteen_orders","canteen_wallet_transactions"]
    Base.metadata.create_all(bind=op.get_bind(), tables=[Base.metadata.tables[name] for name in names], checkfirst=True)


def downgrade() -> None:
    from alembic import op

    op.drop_table('canteen_wallet_transactions')
    op.drop_table('canteen_orders')
    op.drop_table('canteen_dietary_restrictions')
    op.drop_table('canteen_products')
