"""Add nullable timetable actor references without rebuilding legacy tables."""
from alembic import op
import sqlalchemy as sa

from app.core.uuid_type import CustomUUID

revision = "036"
down_revision = "035"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    tables = set(inspector.get_table_names())
    for table in ("timetables", "users"):
        if table not in tables:
            raise RuntimeError(f"036 requires the existing {table} table; restore the matching schema before retrying")
    dialect = connection.dialect.name
    if dialect not in {"sqlite", "postgresql"}:
        raise RuntimeError("036 supports SQLite and PostgreSQL; no schema changes were made")
    existing = {column["name"] for column in inspector.get_columns("timetables")}
    for name in ("created_by", "updated_by"):
        if name in existing:
            continue
        if dialect == "sqlite":
            # SQLite supports a nullable REFERENCES column with no default in
            # ADD COLUMN. Alembic's separate ADD CONSTRAINT would require a
            # table rebuild; this deliberately preserves every old row byte.
            op.execute(sa.text(f'ALTER TABLE "timetables" ADD COLUMN "{name}" VARCHAR(36) REFERENCES "users" ("id")'))
        else:
            op.add_column("timetables", sa.Column(name, CustomUUID(),
                sa.ForeignKey("users.id", name=f"fk_timetables_{name}_users"), nullable=True))


def downgrade():
    # Actor metadata may have been recorded after upgrade. Never erase it or
    # rebuild the table automatically to roll back an application release.
    raise RuntimeError("036 geri dönüşü, uyumlu uygulama sürümüyle doğrulanmış veritabanı yedeğinden yapılmalıdır")
