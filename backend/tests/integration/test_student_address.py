from datetime import date
import importlib.util
from pathlib import Path
from uuid import UUID

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, text, select

from test_saas_platform import platform_client  # noqa: F401
from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.infrastructure.models.models import Student, Role, User, Permission


async def test_student_address_notes_and_enrollment_persist_and_private_fields_respect_permissions(platform_client):
    client, sessions, data = platform_client
    auth = {**headers(data["root"]), "X-SCS360-Organization-Id": str(data["org"].id)}
    body = {"organization_id": str(data["org"].id), "branch_id": str(data["branch"].id), "first_name": "Adres", "last_name": "Kaydi",
        "address": "İstanbul kabul adresi", "notes": "Kayıt notu", "health_notes": "Tıbbi kayıt notu", "enrollment_date": "2026-01-02"}
    response = await client.post("/api/students", headers=auth, json=body)
    assert response.status_code == 200, response.text
    created = response.json()["data"]
    assert created["address"] == body["address"] and created["notes"] == body["notes"]
    path = f'/api/students/{created["id"]}'
    assert (await client.put(path, headers=auth, json={"address": "x" * 501})).status_code == 422
    assert (await client.put(path, headers=auth, json={"enrollment_date": None})).status_code == 422
    changed = await client.put(path, headers=auth, json={"address": "Güncellenen adres", "notes": "Güncellenen not", "enrollment_date": "2026-02-03"})
    assert changed.status_code == 200, changed.text
    read = (await client.get(path, headers=auth)).json()["data"]
    assert read["address"] == "Güncellenen adres" and read["notes"] == "Güncellenen not" and read["enrollment_date"] == "2026-02-03"
    child_path = f'/api/students/{data["children"][0].id}'
    assert (await client.put(child_path, headers=auth, json={"address": body["address"], "notes": body["notes"], "health_notes": body["health_notes"]})).status_code == 200
    teacher = await client.get(child_path, headers=headers(data["teacher"]))
    assert teacher.status_code == 200, teacher.text
    assert not {"address", "notes", "health_notes"}.intersection(teacher.json()["data"])
    async with sessions() as db:
        read_permission = (await db.execute(select(Permission).where(Permission.code == "students.read"))).scalar_one()
        write_permission = Permission(code="students.write", name="Student registration", module="students")
        role = Role(organization_id=data["org"].id, name="Registration", slug="staff", permissions=[read_permission, write_permission])
        writer = User(organization_id=data["org"].id, email="registration@acceptance.example.com", first_name="Registration", last_name="Test", password_hash="unused", roles=[role])
        db.add(writer); await db.commit()
    assert (await client.put(path, headers=headers(writer), json={"health_notes": "Forbidden change"})).status_code == 403
    assert (await client.post("/api/students", headers=headers(writer), json=body)).status_code == 403
    cleared = await client.put(path, headers=auth, json={"address": None, "notes": None})
    assert cleared.status_code == 200
    async with sessions() as db:
        row = await db.get(Student, UUID(created["id"]))
        assert row.address is None and row.notes is None and row.enrollment_date == date(2026, 2, 3)
        assert row.health_notes == body["health_notes"]


async def test_034_only_adds_nullable_address_preserves_all_existing_student_columns_and_accounts(portal_db):
    sessions, data = portal_db
    async with sessions() as db:
        def migrate(connection):
            connection.execute(text('ALTER TABLE students DROP COLUMN address'))
            columns = [column["name"] for column in inspect(connection).get_columns("students")]
            select_old = 'SELECT ' + ','.join('"' + column + '"' for column in columns) + ' FROM students ORDER BY id'
            students = connection.execute(text(select_old)).fetchall()
            users = connection.execute(text('SELECT id,email,password_hash FROM users ORDER BY id')).fetchall()
            path = Path(__file__).resolve().parents[2] / "alembic/versions/034_student_address.py"
            spec = importlib.util.spec_from_file_location("migration034", path)
            module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
            with Operations.context(MigrationContext.configure(connection)):
                module.upgrade(); module.upgrade()
            assert connection.execute(text(select_old)).fetchall() == students
            assert connection.execute(text('SELECT id,email,password_hash FROM users ORDER BY id')).fetchall() == users
            assert connection.execute(text('SELECT COUNT(*) FROM students WHERE address IS NOT NULL')).scalar() == 0
        await (await db.connection()).run_sync(migrate)
        await db.commit()
