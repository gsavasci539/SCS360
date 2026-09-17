"""Add position and department columns to users table"""

from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add position column to users table
    op.add_column('users', sa.Column('position', sa.String(length=100), nullable=True))
    # Add department column to users table
    op.add_column('users', sa.Column('department', sa.String(length=100), nullable=True))


def downgrade() -> None:
    # Remove position column from users table
    op.drop_column('users', 'position')
    # Remove department column from users table
    op.drop_column('users', 'department')
