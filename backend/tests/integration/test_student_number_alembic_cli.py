"""Run the actual Alembic chain in disposable SQLite/PostgreSQL databases."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


@pytest.mark.parametrize("dialect", ["sqlite", "postgresql"])
def test_fresh_alembic_chain_and_repeat_head_have_one_live_number_index(tmp_path, dialect):
    backend = Path(__file__).resolve().parents[2]
    maintenance = target = None
    if dialect == "sqlite":
        url = "sqlite+aiosqlite:///" + (tmp_path / "fresh.db").as_posix()
        inspection_url = "sqlite:///" + (tmp_path / "fresh.db").as_posix()
    else:
        source = os.getenv("TEST_POSTGRES_URL")
        if not source:
            pytest.skip("Disposable TEST_POSTGRES_URL required")
        parsed = make_url(source)
        if not parsed.database.startswith("scs360_acceptance"):
            raise RuntimeError("Only the disposable acceptance PostgreSQL is allowed")
        name = "scs360_acceptance_student037_" + uuid4().hex
        assert re.fullmatch(r"scs360_acceptance_student037_[0-9a-f]{32}", name)
        # psycopg2 is not required: use the local PostgreSQL CLI for database
        # lifecycle and inspection; the migration itself uses asyncpg.
        binaries = Path("C:/Program Files/PostgreSQL/16/bin")
        common = ["-h", parsed.host, "-p", str(parsed.port), "-U", parsed.username]
        made = subprocess.run([str(binaries / "createdb.exe"), *common, "--maintenance-db", parsed.database, name],
            capture_output=True, text=True, timeout=45, check=False)
        assert made.returncode == 0, made.stderr
        maintenance, target = (binaries, common, parsed.database), name
        url = parsed.set(database=name).render_as_string(hide_password=False)
    environment = os.environ | {"DATABASE_URL": url, "APP_ENV": "test", "SEED_DEMO_DATA": "false", "NOTIFICATION_DELIVERY_ENABLED": "false"}
    try:
        for _ in range(2):
            result = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=backend,
                env=environment, capture_output=True, text=True, encoding="utf-8", timeout=150, check=False)
            assert result.returncode == 0, result.stderr[-4000:]
        if dialect == "sqlite":
            engine = create_engine(inspection_url)
            try:
                with engine.connect() as db:
                    assert db.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "037"
                    indexes = db.execute(text("PRAGMA index_list(students)")).all()
                    assert [row[1] for row in indexes if row[2] and row[3] != "pk"] == ["uq_students_org_student_number_live"]
                    assert db.execute(text("PRAGMA integrity_check")).scalar_one() == "ok"
            finally:
                engine.dispose()
        else:
            sql = "SELECT json_build_object('revision',(SELECT version_num FROM alembic_version),'indexes',(SELECT count(*) FROM pg_indexes WHERE tablename='students' AND indexname='uq_students_org_student_number_live'),'global_unique',(SELECT count(*) FROM pg_constraint WHERE conrelid='students'::regclass AND contype='u'));"
            checked = subprocess.run([str(binaries / "psql.exe"), *common, "-d", name, "-At", "-c", sql],
                capture_output=True, text=True, timeout=30, check=False)
            assert checked.returncode == 0, checked.stderr
            assert json.loads(checked.stdout) == {"revision": "037", "indexes": 1, "global_unique": 0}
    finally:
        if maintenance and target:
            binaries, common, _ = maintenance
            dropped = subprocess.run([str(binaries / "dropdb.exe"), *common, "--if-exists", target],
                capture_output=True, text=True, timeout=45, check=False)
            assert dropped.returncode == 0, dropped.stderr
