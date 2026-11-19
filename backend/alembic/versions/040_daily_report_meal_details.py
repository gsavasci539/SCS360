"""Allow all meal observations to fit in a daily report."""
import sqlalchemy as sa
from alembic import op

revision = "040"
down_revision = "039"
branch_labels = depends_on = None


def upgrade():
    # SQLite already treats the old VARCHAR declaration as unbounded text.
    if op.get_context().dialect.name == "postgresql":
        op.alter_column("daily_development_reports", "meal_status", existing_type=sa.String(30),
            type_=sa.Text(), existing_nullable=True)


def downgrade():
    if op.get_context().dialect.name == "postgresql":
        table = sa.table("daily_development_reports", sa.column("meal_status", sa.Text()))
        if op.get_bind().scalar(sa.select(sa.func.count()).select_from(table)
                .where(sa.func.length(table.c.meal_status) > 30)):
            raise RuntimeError("Beslenme gözlemlerini korumak için uyumlu yedekten geri dönün")
        op.alter_column("daily_development_reports", "meal_status", existing_type=sa.Text(),
            type_=sa.String(30), existing_nullable=True)
