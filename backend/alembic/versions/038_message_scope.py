"""Record institution and branch for new direct messages without guessing legacy ownership."""
from alembic import op
import sqlalchemy as sa

from app.core.uuid_type import CustomUUID

revision = "038"
down_revision = "037"
branch_labels = depends_on = None


def upgrade():
    connection = op.get_bind()
    existing = {column["name"] for column in sa.inspect(connection).get_columns("chat_messages")}
    for name, target in (("organization_id", "organizations"), ("branch_id", "branches")):
        if name in existing:
            continue
        if connection.dialect.name == "sqlite":
            connection.exec_driver_sql(
                f'ALTER TABLE "chat_messages" ADD COLUMN "{name}" VARCHAR(36) REFERENCES "{target}" ("id")'
            )
        else:
            op.add_column("chat_messages", sa.Column(name, CustomUUID(), sa.ForeignKey(f"{target}.id"), nullable=True))


def downgrade():
    raise RuntimeError("Mesaj kapsamını korumak için uyumlu yedekten geri dönün")
