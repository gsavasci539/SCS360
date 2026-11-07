import importlib.util
from datetime import date, time
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, select, text

from test_parent_homework_outbox import portal_db  # noqa: F401
from app.domain.entities.health import MedicationLog, MedicationSchedule


async def test_032_leaves_legacy_decisions_dates_duplicates_and_accounts_unchanged(portal_db):
    sessions, data = portal_db
    async with sessions() as db:
        schedule = MedicationSchedule(student_id=data["children"][0].id, medication_name="Legacy", dosage="Legacy",
            frequency="10:00", start_date=date(2026, 1, 1), is_active=False)
        db.add(schedule); await db.flush()
        db.add_all([MedicationLog(schedule_id=schedule.id, student_id=schedule.student_id, scheduled_time=time(10)) for _ in range(2)])
        await db.commit()
        def migrate(connection):
            connection.execute(text('DROP INDEX uq_medication_log_dose'))
            connection.execute(text('ALTER TABLE medication_logs DROP COLUMN scheduled_date'))
            connection.execute(text('ALTER TABLE medication_schedules DROP COLUMN request_status'))
            before = {name: connection.execute(text('SELECT * FROM ' + name)).fetchall() for name in ('users', 'user_roles', 'role_permissions')}
            with Operations.context(MigrationContext.configure(connection)):
                path = Path(__file__).resolve().parents[2] / 'alembic/versions/032_medication_decisions_and_dose_date.py'
                spec = importlib.util.spec_from_file_location('migration032', path)
                module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
                module.upgrade(); module.upgrade()
            for name, rows in before.items():
                assert connection.execute(text('SELECT * FROM ' + name)).fetchall() == rows
            assert 'uq_medication_log_dose' in {index['name'] for index in inspect(connection).get_indexes('medication_logs')}
        await (await db.connection()).run_sync(migrate); await db.commit()
        rows = (await db.execute(select(MedicationLog))).scalars().all()
        assert len(rows) == 2 and all(row.scheduled_date is None for row in rows)
        row = (await db.execute(select(MedicationSchedule))).scalar_one()
        assert row.request_status is None and row.is_active is False and row.medication_name == 'Legacy'
