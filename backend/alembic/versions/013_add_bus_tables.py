"""Add bus routes, stops, telemetry logs, and attendance tables"""

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from alembic import op
    from app.core.database import Base
    # Revision 002 may already have created these tables on a clean install.
    # Use the canonical UUID types on both PostgreSQL and SQLite.
    names = ["bus_routes","bus_stops","bus_telemetry_logs","bus_attendance"]
    Base.metadata.create_all(bind=op.get_bind(), tables=[Base.metadata.tables[name] for name in names], checkfirst=True)


def downgrade() -> None:
    from alembic import op

    op.drop_table('bus_attendance')
    op.drop_table('bus_telemetry_logs')
    op.drop_table('bus_stops')
    op.drop_table('bus_routes')
