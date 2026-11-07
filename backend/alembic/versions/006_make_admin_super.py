"""Make admin@demo.com a super admin"""

from alembic import op
import sqlalchemy as sa
import os

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if os.getenv("APP_ENV", "production").lower() == "production" or os.getenv("SEED_DEMO_DATA", "false").lower() != "true":
        return
    op.execute(sa.text("UPDATE users SET is_super_admin = true WHERE email = 'admin@demo.com'"))


def downgrade() -> None:
    # Revert admin@demo.com from super admin
    op.execute(sa.text("UPDATE users SET is_super_admin = false WHERE email = 'admin@demo.com'"))
