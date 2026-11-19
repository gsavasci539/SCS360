"""Keep private attachment metadata alongside the authorized message."""
from alembic import op
import sqlalchemy as sa

revision = "039"
down_revision = "038"
branch_labels = depends_on = None


def upgrade():
    existing = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("chat_messages")}
    for name, length in (("attachment_name", 255), ("attachment_sha256", 64)):
        if name not in existing:
            op.add_column("chat_messages", sa.Column(name, sa.String(length), nullable=True))


def downgrade():
    raise RuntimeError("Mesaj eki bilgilerini korumak için uyumlu yedekten geri dönün")
