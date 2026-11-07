"""Add status column to payments table"""

from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add status column to payments table with default value if it doesn't exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('payments')]
    
    if 'status' not in columns:
        op.add_column('payments', sa.Column('status', sa.String(length=50), nullable=True, server_default='pending'))


def downgrade() -> None:
    # Remove status column from payments table
    op.drop_column('payments', 'status')
