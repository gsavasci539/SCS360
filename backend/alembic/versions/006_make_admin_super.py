"""Make admin@demo.com a super admin"""

from alembic import op
import sqlalchemy as sa

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Update admin@demo.com to be a super admin
    op.execute("UPDATE users SET is_super_admin = 1 WHERE email = 'admin@demo.com'")


def downgrade() -> None:
    # Revert admin@demo.com from super admin
    op.execute("UPDATE users SET is_super_admin = 0 WHERE email = 'admin@demo.com'")
