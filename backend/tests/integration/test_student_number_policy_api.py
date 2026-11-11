"""Registered HTTP CRUD/import must enforce only unarchived number ownership."""
# ruff: noqa: F811 -- pytest fixture injection.
from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from test_material_files import headers, materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from test_saas_platform import platform_client  # noqa: F401

from app.infrastructure.models.models import Debt, DebtType, Parent, Student, StudentParent


async def test_actual_crud_and_import_preserve_archived_identity_and_linked_history(platform_client):
    client, sessions, data = platform_client
    auth = {**headers(data["root"]), "X-SCS360-Organization-Id": str(data["org"].id)}
    body = {"organization_id": str(data["org"].id), "branch_id": str(data["branch"].id),
        "first_name": "Acceptance", "last_name": "Student", "student_number": "REUSE"}
    async def create(number):
        result = await client.post("/api/students", headers=auth, json={**body, "student_number": number})
        assert result.status_code == 200, result.text
        return UUID(result.json()["data"]["id"])
    original = await create("REUSE")
    passive = await client.put(f"/api/students/{original}", headers=auth, json={"status": "PASSIVE"})
    assert passive.status_code == 200, passive.text
    assert (await client.post("/api/students", headers=auth, json=body)).status_code == 409
    async with sessions() as db:
        parent = await db.scalar(select(Parent).where(Parent.user_id == data["user"].id))
        db.add_all([StudentParent(student_id=original, parent_id=parent.id),
            Debt(student_id=original, organization_id=data["org"].id, branch_id=data["branch"].id,
                debt_type=DebtType.EDUCATION, amount=10, paid_amount=0, due_date=date(2026, 1, 1))])
        await db.commit()
    assert (await client.delete(f"/api/students/{original}", headers=auth)).status_code == 200
    replacement = await create("REUSE")
    assert replacement != original
    await create("RESERVED")
    conflict = await client.put(f"/api/students/{replacement}", headers=auth, json={"student_number": "RESERVED", "first_name": "MustRollback"})
    assert conflict.status_code == 409, conflict.text
    imported_archive = await create("IMPORT-REUSE")
    assert (await client.delete(f"/api/students/{imported_archive}", headers=auth)).status_code == 200
    csv = "student_number,first_name,last_name,branch_id\n" + "\n".join(
        f"{number},Imported,Student,{data['branch'].id}" for number in ("IMPORT-REUSE", "REUSE", "AFTER-CONFLICT"))
    imported = await client.post("/api/import/students", headers=auth, files={"file": ("students.csv", csv.encode(), "text/csv")})
    assert imported.status_code == 200, imported.text
    facts = imported.json()["data"]
    assert facts["imported"] == 2 and len(facts["errors"]) == 1, facts
    async with sessions() as db:
        archive, live = await db.get(Student, original), await db.get(Student, replacement)
        assert archive.deleted_at is not None and live.deleted_at is None
        assert live.student_number == "REUSE" and live.first_name == "Acceptance"
        assert await db.scalar(select(func.count()).select_from(StudentParent).where(StudentParent.student_id == original)) == 1
        assert await db.scalar(select(func.count()).select_from(Debt).where(Debt.student_id == original)) == 1
        assert await db.scalar(select(func.count()).select_from(Student).where(Student.student_number == "IMPORT-REUSE")) == 2
    denied = await client.post("/api/students", headers=headers(data["user"]), json={**body, "student_number": "DENIED"})
    assert denied.status_code == 403, denied.text
    other_org = str(data["other_branch"].organization_id)
    other = await client.post("/api/students", headers={**headers(data["root"]), "X-SCS360-Organization-Id": other_org},
        json={**body, "organization_id": other_org, "branch_id": str(data["other_branch"].id)})
    assert other.status_code == 200, other.text
    assert (await client.post("/api/students", headers=headers(data["root"]), json={**body, "student_number": "UNSCOPED"})).status_code == 403
