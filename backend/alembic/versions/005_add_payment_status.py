"""Add status column to payments table"""

from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add status column to payments table with default value
    op.add_column('payments', sa.Column('status', sa.String(length=50), nullable=True, server_default='pending'))


def downgrade() -> None:
    # Remove status column from payments table
    op.drop_column('payments', 'status')
