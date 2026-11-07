"""Seed permissions, demo organization, roles, and the initial admin account."""

import os
from pathlib import Path

import sqlalchemy as sa

from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Only seed data in development or if explicitly enabled
    seed_demo_data = os.getenv("SEED_DEMO_DATA", "false").lower() == "true"
    app_env = os.getenv("APP_ENV", "production").lower()
    
    if not seed_demo_data:
        print("Skipping demo seed (SEED_DEMO_DATA=false)")
        return
    if app_env in {"production", "staging"}:
        raise RuntimeError("Demo data cannot be seeded in production or staging")
    
    seed_file = Path(__file__).resolve().parents[2] / "sql" / "002_seed.sql"
    sql = seed_file.read_text(encoding="utf-8")
    connection = op.get_bind()
    for statement in (part.strip() for part in sql.split(";")):
        if statement:
            connection.execute(sa.text(statement))


def downgrade() -> None:
    # Baseline rows may be referenced by user data; never delete them automatically.
    pass
