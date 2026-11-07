from uuid import UUID

from sqlalchemy import select

from test_saas_platform import platform_client  # noqa: F401
from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.infrastructure.models.models import Branch, ClassRoom, ClassTeacher, Permission, Role, Student, User, UserStatus


async def editor(sessions, data, codes):
    async with sessions() as db:
        existing = {row.code: row for row in (await db.execute(select(Permission))).scalars()}
        permissions = [existing.get(code) or Permission(code=code, name=code, module=code.split(".")[0]) for code in codes]
        role = Role(organization_id=data["org"].id, slug="staff", name="Registration", permissions=permissions)
        actor = User(organization_id=data["org"].id, email="class-editor@test.invalid", first_name="Editor", last_name="Test", password_hash="unused", roles=[role])
        db.add(actor); await db.commit()
    return actor


async def test_class_teacher_and_active_fields_persist_and_teacher_portal_reads_real_assignment(platform_client):
    client, sessions, data = platform_client
    actor = await editor(sessions, data, ["classes.read", "classes.write"])
    auth = headers(actor)
    assert (await client.get("/api/users", headers=auth)).status_code == 403
    choices = await client.get("/api/classes/teacher-options", headers=auth)
    assert choices.status_code == 200, choices.text
    assert choices.json()["data"]["items"] == [{"id": str(data["teacher"].id), "name": "Teacher Test"}]
    body = {"organization_id": str(data["org"].id), "branch_id": str(data["branch"].id), "name": "New assigned class",
        "teacher_id": str(data["teacher"].id), "is_active": False, "description": "Saved description", "capacity": 21}
    response = await client.post("/api/classes", headers=auth, json=body)
    assert response.status_code == 200, response.text
    record = response.json()["data"]; path = f'/api/classes/{record["id"]}'
    assert record["teacher_id"] == body["teacher_id"] and record["teacher_name"] == "Teacher Test" and record["is_active"] is False
    assert (await client.get(path, headers=auth)).json()["data"]["description"] == "Saved description"
    assert (await client.post("/api/classes", headers=auth, json=body)).status_code == 409
    portal = await client.get("/api/teacher/my-classes", headers=headers(data["teacher"]))
    assert portal.status_code == 200 and record["id"] in {row["id"] for row in portal.json()["data"]}, portal.text
    changed = await client.put(path, headers=auth, json={"is_active": True, "teacher_id": None})
    assert changed.status_code == 200 and changed.json()["data"]["teacher_id"] is None
    listing = await client.get("/api/classes", headers=auth, params={"search": "New assigned"})
    assert listing.status_code == 200 and [row["id"] for row in listing.json()["data"]["items"]] == [record["id"]]
    async with sessions() as db:
        # Clearing the main teacher must preserve independently assigned co-teachers.
        db.add(ClassTeacher(class_id=UUID(record["id"]), user_id=data["teacher"].id)); await db.commit()
    await client.put(path, headers=auth, json={"teacher_id": body["teacher_id"]})
    await client.put(path, headers=auth, json={"teacher_id": None})
    async with sessions() as db:
        assert await db.get(ClassTeacher, (UUID(record["id"]), data["teacher"].id)) is not None


async def test_class_rejects_invalid_references_nulls_and_foreign_or_ineligible_teachers(platform_client):
    client, sessions, data = platform_client
    auth = {**headers(data["root"]), "X-SCS360-Organization-Id": str(data["org"].id)}
    body = {"organization_id": str(data["org"].id), "branch_id": str(data["branch"].id), "name": "Validated class"}
    async with sessions() as db:
        teacher_role = (await db.execute(select(Role).where(Role.slug == "teacher"))).scalar_one()
        branch = Branch(organization_id=data["org"].id, name="Restricted other branch"); db.add(branch); await db.flush()
        foreign = User(organization_id=data["stranger"].organization_id, email="foreign-class@test.invalid", first_name="Foreign", last_name="Teacher", password_hash="unused", roles=[teacher_role])
        inactive = User(organization_id=data["org"].id, email="inactive-class@test.invalid", first_name="Inactive", last_name="Teacher", password_hash="unused", status=UserStatus.PASSIVE, roles=[teacher_role])
        restricted = User(organization_id=data["org"].id, email="restricted-class@test.invalid", first_name="Restricted", last_name="Teacher", password_hash="unused", roles=[teacher_role], branches=[branch])
        db.add_all([foreign, inactive, restricted]); await db.commit()
    for key, value in [("teacher_id", "not-uuid"), ("organization_id", "bad"), ("branch_id", "bad"), ("name", " "), ("name", "x" * 151), ("capacity", None), ("is_active", None)]:
        assert (await client.post("/api/classes", headers=auth, json={**body, key: value})).status_code == 422
    for user in (data["root"], data["user"], foreign, inactive, restricted):
        rejected = await client.post("/api/classes", headers=auth, json={**body, "teacher_id": str(user.id)})
        assert rejected.status_code == 422, rejected.text
    record = (await client.post("/api/classes", headers=auth, json=body)).json()["data"]
    for key in ("capacity", "is_active", "name", "branch_id", "organization_id"):
        assert (await client.put(f'/api/classes/{record["id"]}', headers=auth, json={key: None})).status_code == 422
    assert (await client.put(f'/api/classes/{record["id"]}', headers=auth, json={"branch_id": str(data["other_branch"].id)})).status_code == 422
    filtered = await client.get("/api/classes/teacher-options", headers=auth, params={"branch_id": str(data["branch"].id), "search": "Teacher"})
    assert filtered.status_code == 200 and {row["id"] for row in filtered.json()["data"]["items"]} == {str(data["teacher"].id)}


async def test_finance_writer_gets_minimal_paginated_student_choices_without_directory_permissions(platform_client):
    client, sessions, data = platform_client
    actor = await editor(sessions, data, ["finance.write"]); auth = headers(actor)
    assert (await client.get("/api/students", headers=auth)).status_code == 403
    assert (await client.get("/api/organizations", headers=auth)).status_code == 403
    assert (await client.get("/api/ai/classes-overview", headers=auth)).status_code == 403
    assert (await client.get("/api/ai/parents-overview", headers=auth)).status_code == 403
    async with sessions() as db:
        db.add_all([Student(organization_id=data["org"].id, branch_id=data["branch"].id, first_name=f"Extra{i:03d}", last_name="Choice", student_number=f"CHOICE-{i:03d}") for i in range(102)])
        await db.commit()
    page = await client.get("/api/debts/student-options", headers=auth, params={"page_size": 50})
    assert page.status_code == 200 and page.json()["data"]["total"] == 104
    assert len(page.json()["data"]["items"]) == 50
    picked = await client.get("/api/debts/student-options", headers=auth, params={"search": "CHOICE-101"})
    rows = picked.json()["data"]["items"]; assert len(rows) == 1 and rows[0]["name"].endswith("CHOICE-101")
    assert set(rows[0]) == {"id", "name"}
    selected = await client.get("/api/debts/student-options", headers=auth, params={"selected_id": rows[0]["id"], "search": "Child0"})
    assert selected.json()["data"]["selected"] == rows[0]
    foreign = await client.get("/api/debts/student-options", headers=auth, params={"selected_id": str(data["stranger"].id)})
    assert foreign.json()["data"]["selected"] is None
    body = {"student_id": rows[0]["id"], "debt_type": "EDUCATION", "amount": 123.45, "due_date": "2026-12-01"}
    debt = await client.post("/api/debts", headers=auth, json=body)
    assert debt.status_code == 200, debt.text
    path = f'/api/debts/{debt.json()["data"]["id"]}'
    assert (await client.put(path, headers=auth, json={"amount": "125.50"})).status_code == 200
    for key, value in [("amount", "NaN"), ("amount", "Infinity"), ("amount", -1), ("amount", 0), ("amount", 1.234),
            ("amount", "10000000000"), ("amount", None), ("student_id", "bad"), ("debt_type", "BAD"), ("due_date", "2026-02-30")]:
        bad = await client.post("/api/debts", headers=auth, json={**body, key: value})
        assert bad.status_code == 422, bad.text
    for changes in ({"amount": None}, {"due_date": "bad"}, {"status": "BAD"}, {"status": "PAID"},
            {"student_id": str(data["children"][0].id)}, {"debt_type": "OTHER"}):
        bad = await client.put(path, headers=auth, json=changes)
        assert bad.status_code == 422, bad.text
