"""Persist operations, wallet balances and notification read state."""
import sqlalchemy as sa
from alembic import op
from app.core.uuid_type import CustomUUID

revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


def timestamps():
    return [sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)]


def upgrade():
    from app.core.database import Base
    connection = op.get_bind()
    for table, column in [
        ("users", sa.Column("avatar_url", sa.String(500))),
        ("notification_recipients", sa.Column("read_at", sa.DateTime(timezone=True))),
        *[("bus_routes", sa.Column(name, sa.String(length))) for name, length in
            [("driver_name", 150), ("driver_phone", 30), ("hostess_name", 150), ("hostess_phone", 30)]],
    ]:
        if column.name not in {item["name"] for item in sa.inspect(connection).get_columns(table)}:
            op.add_column(table, column)
    Base.metadata.create_all(bind=connection, tables=[Base.metadata.tables[name] for name in
        ("operational_records", "student_wallets", "user_device_tokens")], checkfirst=True)


def downgrade():
    op.drop_table("user_device_tokens")
    op.drop_table("student_wallets")
    op.drop_table("operational_records")
    for name in ("driver_name", "driver_phone", "hostess_name", "hostess_phone"):
        op.drop_column("bus_routes", name)
    op.drop_column("notification_recipients", "read_at")
    op.drop_column("users", "avatar_url")
