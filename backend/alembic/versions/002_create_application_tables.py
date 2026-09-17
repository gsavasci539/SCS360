"""Create the application tables for installations where revision 001 was empty."""

from alembic import op
from app.core.database import Base
from app.infrastructure.models import models  # noqa: F401

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    # Schema removal is intentionally not automatic: production data must not
    # be destroyed by a routine rollback.
    pass
