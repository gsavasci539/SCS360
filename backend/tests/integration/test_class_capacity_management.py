import asyncio
from uuid import UUID

from sqlalchemy import func, select

from test_saas_platform import platform_client  # noqa: F401
from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.infrastructure.models.models import Branch, ClassRoom, Student


def auth(data):
    return {**headers(data["root"]), "X-SCS360-Organization-Id": str(data["org"].id)}


async def target(sessions, data, capacity=1):
    async with sessions() as db:
        row = ClassRoom(organization_id=data["org"].id, branch_id=data["branch"].id, name="Capacity target", capacity=capacity)
        db.add(row); await db.commit()
        return row


def student(data, classroom, name="Seat"):
    return {"organization_id": str(data["org"].id), "branch_id": str(data["branch"].id), "class_id": str(classroom.id), "first_name": name, "last_name": "Capacity"}


async def test_student_create_update_and_repeat_assignment_respect_capacity(platform_client):
    client, sessions, data = platform_client; classroom = await target(sessions, data); h = auth(data)
    first = await client.post("/api/students", headers=h, json=student(data, classroom))
    assert first.status_code == 200, first.text
    assert (await client.post("/api/students", headers=h, json=student(data, classroom, "Second"))).status_code == 409
    assert (await client.put(f'/api/students/{data["children"][0].id}', headers=h, json={"class_id": str(classroom.id)})).status_code == 409
    repeated = await client.post(f"/api/classes/{classroom.id}/students", headers=h, json={"student_id": first.json()["data"]["id"]})
    assert repeated.status_code == 200, repeated.text
    async with sessions() as db:
        assert (await db.execute(select(func.count(Student.id)).where(Student.class_id == classroom.id))).scalar_one() == 1


async def test_bulk_transfer_and_capacity_shrink_preserve_rosters_on_failure(platform_client):
    client, sessions, data = platform_client; classroom = await target(sessions, data); h = auth(data)
    ids = [str(row.id) for row in data["children"]]
    assert (await client.post(f"/api/classes/{classroom.id}/assign-students", headers=h, json={"student_ids": ids})).status_code == 409
    assert (await client.put(f'/api/classes/{data["classroom"].id}', headers=h, json={"capacity": 1})).status_code == 409
    path = f'/api/classes/{data["classroom"].id}/transfer-students'
    assert (await client.post(path, headers=h, json={"student_ids": ids, "target_class_id": str(classroom.id)})).status_code == 409
    async with sessions() as db:
        for row in data["children"]:
            assert (await db.get(Student, row.id)).class_id == data["classroom"].id
    first = await client.post(path, headers=h, json={"student_ids": ids[:1], "target_class_id": str(classroom.id)})
    assert first.status_code == 200, first.text
    assert (await client.post(path, headers=h, json={"student_ids": ids[1:], "target_class_id": str(classroom.id)})).status_code == 409


async def test_parent_role_cannot_transfer_between_its_own_children_classes(materials_client):
    client, sessions, data = materials_client
    async with sessions() as db:
        row = await db.get(Student, data["children"][1].id); row.class_id = data["other_class"].id; await db.commit()
    response = await client.post(f'/api/classes/{data["classroom"].id}/transfer-students', headers=headers(data["user"]),
        json={"student_ids": [str(data["children"][0].id)], "target_class_id": str(data["other_class"].id)})
    assert response.status_code == 403, response.text


async def test_concurrent_last_seat_creates_serialize_on_both_databases(platform_client):
    client, sessions, data = platform_client; classroom = await target(sessions, data); h = auth(data)
    responses = await asyncio.gather(*[client.post("/api/students", headers=h, json=student(data, classroom, f"Concurrent{i}")) for i in range(2)])
    assert sorted(row.status_code for row in responses) == [200, 409], [row.text for row in responses]
    async with sessions() as db:
        assert (await db.execute(select(func.count(Student.id)).where(Student.class_id == classroom.id))).scalar_one() == 1


async def test_assignment_payloads_validate_ids_and_transfer_never_mismatches_branch(platform_client):
    client, sessions, data = platform_client; h = auth(data)
    for payload in ({}, {"student_id": 1}, {"student_id": None}):
        response = await client.post(f'/api/classes/{data["classroom"].id}/students', headers=h, json=payload)
        assert response.status_code == 422, response.text
    for payload in ({}, {"student_ids": [1]}, {"student_ids": None}):
        response = await client.post(f'/api/classes/{data["classroom"].id}/assign-students', headers=h, json=payload)
        assert response.status_code == 422, response.text
    async with sessions() as db:
        branch = Branch(organization_id=data["org"].id, name="Other branch"); db.add(branch); await db.flush()
        classroom = ClassRoom(organization_id=data["org"].id, branch_id=branch.id, name="Other branch class")
        db.add(classroom); await db.commit()
    response = await client.post(f'/api/classes/{data["classroom"].id}/transfer-students', headers=h,
        json={"student_ids": [str(data["children"][0].id)], "target_class_id": str(classroom.id)})
    assert response.status_code == 422, response.text


async def test_csv_import_reports_full_class_without_exceeding_the_roster(platform_client):
    client, sessions, data = platform_client; classroom = await target(sessions, data)
    csv = "branch_id,class_id,first_name,last_name,student_number\n" + "\n".join(
        f'{data["branch"].id},{classroom.id},Import{i},Capacity,IMPORT-CAP-{i}' for i in range(2))
    response = await client.post("/api/import/students", headers=auth(data), files={"file": ("capacity.csv", csv.encode(), "text/csv")})
    assert response.status_code == 200, response.text
    assert response.json()["data"]["imported"] == 1 and len(response.json()["data"]["errors"]) == 1
    async with sessions() as db:
        assert (await db.execute(select(func.count(Student.id)).where(Student.class_id == classroom.id))).scalar_one() == 1


async def test_legacy_over_capacity_records_are_preserved_and_populated_classes_cannot_be_deleted(platform_client):
    client, sessions, data = platform_client; h = auth(data)
    async with sessions() as db:
        row = await db.get(ClassRoom, data["classroom"].id); row.capacity = 1; await db.commit()
    # Existing unrelated edits never remove or silently move legacy students.
    changed = await client.put(f'/api/students/{data["children"][0].id}', headers=h, json={"first_name": "Preserved"})
    assert changed.status_code == 200, changed.text
    deleted = await client.delete(f'/api/classes/{data["classroom"].id}', headers=h)
    assert deleted.status_code == 409, deleted.text
    async with sessions() as db:
        assert (await db.get(ClassRoom, data["classroom"].id)).deleted_at is None
        for child in data["children"]:
            assert (await db.get(Student, child.id)).class_id == data["classroom"].id
