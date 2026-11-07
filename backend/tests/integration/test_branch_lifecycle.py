import asyncio
from uuid import UUID
import pytest

from sqlalchemy import select
from test_saas_platform import platform_client  # noqa: F401
from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.infrastructure.models.models import Branch, Student
from app.core.tenant import TenantContext
from app.core.exceptions import ValidationException


def auth(data):
    return {**headers(data["root"]), "X-SCS360-Organization-Id": str(data["org"].id)}


async def test_populated_branch_cannot_be_deleted_and_deactivation_keeps_its_history_visible(platform_client):
    client, sessions, data = platform_client; h = auth(data); path = f'/api/branches/{data["branch"].id}'
    deleted = await client.delete(path, headers=h)
    assert deleted.status_code == 409, deleted.text
    closed = await client.put(path, headers=h, json={"is_active": False})
    assert closed.status_code == 200 and closed.json()["data"]["student_count"] == 2, closed.text
    for child in data["children"]:
        assert (await client.get(f'/api/students/{child.id}', headers=h)).status_code == 200
    async with sessions() as db:
        assert (await db.get(Branch, data["branch"].id)).deleted_at is None


async def test_inactive_branch_blocks_new_class_unassigned_student_transfer_and_import_but_keeps_old_edits(platform_client):
    client, sessions, data = platform_client; h = auth(data); org = str(data["org"].id); branch = str(data["branch"].id)
    assert (await client.put(f"/api/branches/{branch}", headers=h, json={"is_active": False})).status_code == 200
    payload = {"organization_id": org, "branch_id": branch, "first_name": "Invalid", "last_name": "Admission"}
    assert (await client.post("/api/students", headers=h, json=payload)).status_code == 409
    assert (await client.post("/api/classes", headers=h, json={"organization_id": org, "branch_id": branch, "name": "Invalid new class", "capacity": 20})).status_code == 409
    assert (await client.put(f'/api/students/{data["children"][0].id}', headers=h, json={"first_name": "Preserved"})).status_code == 200
    active = await client.post("/api/branches", headers=h, json={"organization_id": org, "name": "Active target"}); assert active.status_code == 200, active.text
    active_id = active.json()["data"]["id"]
    child = await client.post("/api/students", headers=h, json={**payload, "branch_id": active_id}); assert child.status_code == 200, child.text
    transferred = await client.put(f'/api/students/{child.json()["data"]["id"]}', headers=h, json={"branch_id": branch})
    assert transferred.status_code == 409, transferred.text
    csv = f"branch_id,first_name,last_name,student_number\n{branch},Import,Blocked,INACTIVE-IMPORT"
    imported = await client.post("/api/import/students", headers=h, files={"file": ("inactive.csv", csv.encode(), "text/csv")})
    assert imported.status_code == 200 and imported.json()["data"]["imported"] == 0 and len(imported.json()["data"]["errors"]) == 1, imported.text
    async with sessions() as db:
        assert (await db.get(Student, UUID(child.json()["data"]["id"]))).branch_id == UUID(active_id)


async def test_last_empty_branch_deletion_serializes_with_first_student_admission(platform_client):
    client, sessions, data = platform_client; h = auth(data)
    new = await client.post("/api/branches", headers=h, json={"organization_id": str(data["org"].id), "name": "Deletion race"})
    assert new.status_code == 200; branch = new.json()["data"]["id"]
    deleted, admitted = await asyncio.gather(client.delete(f"/api/branches/{branch}", headers=h),
        client.post("/api/students", headers=h, json={"organization_id": str(data["org"].id), "branch_id": branch, "first_name": "Racing", "last_name": "Admission"}))
    assert sorted([deleted.status_code, admitted.status_code]) in [[200, 409], [200, 404], [200, 403]], (deleted.text, admitted.text)
    async with sessions() as db:
        row = await db.get(Branch, UUID(branch))
        roster = (await db.execute(select(Student).where(Student.branch_id == UUID(branch)))).scalars().all()
        assert row.deleted_at is None or roster == []


async def test_orm_branch_transfer_cannot_leave_the_students_class_in_another_branch(platform_client):
    client, sessions, data = platform_client
    created = await client.post("/api/branches", headers=auth(data), json={"organization_id": str(data["org"].id), "name": "ORM target"})
    assert created.status_code == 200, created.text
    async with sessions() as db:
        db.info["tenant_context"] = TenantContext(user_id=data["root"].id, organization_id=data["org"].id, is_super_admin=True)
        student = await db.get(Student, data["children"][0].id)
        student.branch_id = UUID(created.json()["data"]["id"])
        with pytest.raises(ValidationException, match="aynı kurum ve şubeye"):
            await db.flush()
        await db.rollback()
    async with sessions() as db:
        assert (await db.get(Student, data["children"][0].id)).branch_id == data["branch"].id
