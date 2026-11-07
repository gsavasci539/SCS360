from uuid import UUID

from sqlalchemy import select
from test_saas_platform import platform_client  # noqa: F401
from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.infrastructure.models.models import Branch, ClassRoom, Permission, Role, User


async def writer(sessions, data):
    async with sessions() as db:
        permission = Permission(code="students.write", name="Student write", module="students")
        role = Role(organization_id=data["org"].id, slug="admissions", name="Admissions", permissions=[permission])
        account = User(organization_id=data["org"].id, email="admissions@test.invalid", first_name="Admissions", last_name="Test",
            password_hash="unused", roles=[role], branches=[await db.get(Branch, data["branch"].id)])
        db.add(account); await db.commit()
    return headers(account)


async def test_student_writer_uses_paged_scoped_choices_without_general_registry_read(platform_client):
    client, sessions, data = platform_client; auth = await writer(sessions, data)
    assert (await client.get("/api/classes", headers=auth)).status_code == 403
    assert (await client.get("/api/branches", headers=auth)).status_code == 403
    assert (await client.get(f'/api/students/{data["children"][0].id}', headers=auth)).status_code == 403
    form = await client.get(f'/api/students/{data["children"][0].id}/form', headers=auth)
    assert form.status_code == 200 and form.json()["data"]["first_name"] == "Child0", form.text
    assert (await client.get(f'/api/students/{data["stranger"].id}/form', headers=auth)).status_code == 404
    organizations = await client.get("/api/students/organization-options", headers=auth)
    assert organizations.status_code == 200 and [row["id"] for row in organizations.json()["data"]["items"]] == [str(data["org"].id)], organizations.text
    branches = await client.get("/api/students/branch-options", headers=auth, params={"organization_id": str(data["org"].id)})
    assert branches.status_code == 200 and [row["id"] for row in branches.json()["data"]["items"]] == [str(data["branch"].id)], branches.text
    async with sessions() as db:
        rows = [ClassRoom(name=f"Choice {number:03}", organization_id=data["org"].id, branch_id=data["branch"].id, capacity=5) for number in range(105)]
        db.add_all(rows); await db.commit()
    params = {"branch_id": str(data["branch"].id), "page_size": 100}
    first = await client.get("/api/students/class-options", headers=auth, params=params)
    assert first.status_code == 200 and first.json()["data"]["total"] == 107, first.text
    second = await client.get("/api/students/class-options", headers=auth, params={**params, "page": 2})
    assert second.status_code == 200 and len(second.json()["data"]["items"]) == 7, second.text
    assert any(row["name"] == "Choice 104 (0/5)" for row in second.json()["data"]["items"])
    last = await client.get("/api/students/class-options", headers=auth, params={**params, "search": "Choice 104"})
    assert last.status_code == 200 and [row["name"] for row in last.json()["data"]["items"]] == ["Choice 104 (0/5)"], last.text
    forbidden = await client.get("/api/students/class-options", headers=auth, params={"branch_id": str(data["other_branch"].id)})
    assert forbidden.status_code in {403, 404} and "Choice" not in forbidden.text


async def test_full_inactive_classes_are_omitted_but_current_assignment_is_pinned_only_for_own_student(platform_client):
    client, sessions, data = platform_client; auth = await writer(sessions, data)
    async with sessions() as db:
        full = await db.get(ClassRoom, data["classroom"].id); full.capacity = 2
        inactive = await db.get(ClassRoom, data["other_class"].id); inactive.is_active = False
        await db.commit()
    params = {"branch_id": str(data["branch"].id), "selected_id": str(data["classroom"].id)}
    initial = await client.get("/api/students/class-options", headers=auth, params=params)
    assert initial.status_code == 200 and initial.json()["data"]["items"] == [] and initial.json()["data"]["selected"] is None, initial.text
    pinned = await client.get("/api/students/class-options", headers=auth, params={**params, "student_id": str(data["children"][0].id)})
    assert pinned.status_code == 200 and pinned.json()["data"]["selected"]["id"] == str(data["classroom"].id), pinned.text
    assert pinned.json()["data"]["items"] == []
    assert (await client.get("/api/students/class-options", headers=auth, params={**params, "student_id": str(data["stranger"].id)})).status_code == 404
    assert (await client.get("/api/students/class-options", headers=headers(data["user"]), params=params)).status_code == 403
