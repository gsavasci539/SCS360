"""The actual release CLI distinguishes a current schema from sound stored data."""
import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text

import app.main  # noqa: F401 - register the same complete model graph as the CLI
from app.core.database import Base
from app.infrastructure.models.models import Branch, Organization, Parent, Student


@pytest.mark.parametrize("damaged", [False, True])
def test_actual_cli_reads_disposable_database_and_fails_closed_on_legacy_integrity(tmp_path, damaged):
    database = tmp_path / "release-acceptance.db"
    engine = create_engine(f"sqlite:///{database.as_posix()}")
    organization_id, branch_id, student_one, student_two = (uuid4() for _ in range(4))
    try:
        Base.metadata.create_all(engine)
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)"))
            from alembic.script import ScriptDirectory
            backend = Path(__file__).resolve().parents[2]
            head = ScriptDirectory(str(backend / "alembic")).get_current_head()
            connection.execute(text("INSERT INTO alembic_version (version_num) VALUES (:revision)"), {"revision": head})
            connection.execute(Organization.__table__.insert().values(id=organization_id, name="Temporary acceptance"))
            connection.execute(Branch.__table__.insert().values(id=branch_id, organization_id=organization_id, name="Temporary branch"))
            connection.execute(Student.__table__.insert().values(id=student_one, organization_id=organization_id,
                branch_id=branch_id, student_number="TEMP-1", first_name="Temporary", last_name="One"))
            if damaged:
                # Reproduce the pre-037 raw-key constraint in this disposable
                # damaged database; the current canonical index prevents it.
                connection.execute(text("DROP INDEX uq_students_org_student_number_live"))
                connection.execute(text("CREATE UNIQUE INDEX legacy_student_number ON students(organization_id,student_number)"))
                # Raw legacy values deliberately bypass the UUID binder only in
                # this temporary file, reproducing the two storage spellings.
                connection.execute(Student.__table__.insert().values(id=student_two, organization_id=organization_id,
                    branch_id=branch_id, student_number="TEMP-2", first_name="Temporary", last_name="Two"))
                connection.execute(text("UPDATE students SET organization_id=:legacy, student_number='TEMP-1' WHERE id=:student"),
                    {"legacy": organization_id.hex, "student": str(student_two)})
                connection.execute(Parent.__table__.insert().values(id=uuid4(), organization_id=organization_id,
                    first_name="Temporary", last_name="Parent"))
                connection.execute(text("UPDATE parents SET organization_id='invalid-uuid'"))
            snapshot = {table: connection.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar_one()
                for table in Base.metadata.tables}
            violations_before = len(connection.execute(text("PRAGMA foreign_key_check")).all())
        environment = os.environ | {"DATABASE_URL": f"sqlite+aiosqlite:///{database.as_posix()}",
            "APP_ENV": "test", "SEED_DEMO_DATA": "false", "NOTIFICATION_DELIVERY_ENABLED": "false"}
        result = subprocess.run([sys.executable, "scripts/release_preflight.py"], cwd=backend,
            env=environment, capture_output=True, text=True, encoding="utf-8", timeout=120, check=False)
        assert result.returncode == 1  # SQLite/test deployment flags remain false.
        report = json.loads(result.stdout)
        assert report["ready"] is False
        assert report["checks"]["schema_current"] is True
        assert report["checks"]["database_integrity"] is (not damaged)
        integrity = report["database_integrity"]
        assert integrity["ready"] is (not damaged)
        assert integrity["snapshot_read_only"] is True
        # Readiness output must never contain stored personal/identity values.
        for private in (str(organization_id), organization_id.hex, str(student_one), str(student_two), "TEMP-1", "invalid-uuid"):
            assert private not in result.stdout
        with engine.connect() as connection:
            after = {table: connection.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar_one()
                for table in Base.metadata.tables}
            assert after == snapshot
            assert len(connection.execute(text("PRAGMA foreign_key_check")).all()) == violations_before
            assert violations_before == (2 if damaged else 0)
            assert connection.execute(text("PRAGMA query_only")).scalar_one() == 0
    finally:
        engine.dispose()
