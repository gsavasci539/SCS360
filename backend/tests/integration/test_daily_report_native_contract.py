import asyncio
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from test_material_files import headers, materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401

from app.infrastructure.models.models import Branch, ClassRoom, DailyDevelopmentReport, Role, Student, StudentTeacherAssignment, UserBranch
from app.routers import daily_reports


async def test_daily_report_roundtrip_and_branch_filter(materials_client):  # noqa: F811
    client, _, data = materials_client
    child = data["children"][0]
    path = "/api/daily-reports"
    authorization = headers(data["teacher"])
    today = date(2026, 11, 19).isoformat()
    draft = {"student_id": str(child.id), "class_id": str(child.class_id), "date": today,
        "meal_breakfast": "Tümünü Yedi", "meal_lunch": "Yarısını Yedi", "meal_snack": "Az Yedi",
        "sleep_status": "30 dk", "mood": "Sakin", "activities": ["Çizim"], "teacher_notes": "Kayıtlı gözlem"}
    assert (await client.post(path, headers=headers(data["user"]), json=draft)).status_code == 403
    response = await client.post(path, headers=authorization, json=draft)
    assert response.status_code == 200, response.text
    row = response.json()["data"]
    assert row["meal_status"] == "Kahvaltı: Tümünü Yedi / Öğle: Yarısını Yedi / Ara öğün: Az Yedi"
    assert row["recorded_by"] == str(data["teacher"].id)
    assert row["sleep_status"] == "30 dk" and row["activities"] == ["Çizim"]
    assert (await client.get(f'{path}/{row["id"]}', headers=authorization)).json()["data"] == row
    params = {"student_id": str(child.id), "date": today, "branch_id": str(data["branch"].id)}
    assert (await client.get(path, headers=authorization, params=params)).json()["data"]["items"] == [row]
    assert (await client.get(path, headers=authorization, params={**params,
        "branch_id": str(data["other_branch"].id)})).json()["data"]["items"] == []
    assert (await client.post(path, headers=authorization, json=draft)).status_code == 409


async def test_daily_report_edit_and_delete_are_scoped_to_assigned_students(materials_client):  # noqa: F811
    client, sessions, data = materials_client
    actor = data["teacher"]
    child = data["children"][0]
    today = date(2026, 11, 19)
    async with sessions() as db:
        other_class = data["other_class"]
        other = Student(first_name="Unassigned", last_name="Test", organization_id=other_class.organization_id,
            branch_id=other_class.branch_id, class_id=other_class.id)
        db.add(other)
        await db.flush()
        assigned = DailyDevelopmentReport(student_id=child.id, class_id=child.class_id, date=today,
            teacher_notes="Önceki gözlem", mood="Sakin", recorded_by=actor.id)
        unassigned = DailyDevelopmentReport(student_id=other.id, class_id=other_class.id, date=today, teacher_notes="Korunacak")
        db.add_all([assigned, unassigned])
        await db.commit()
        path = f"/api/daily-reports/{assigned.id}"
        other_path = f"/api/daily-reports/{unassigned.id}"
        unassigned_id = unassigned.id

    teacher = headers(actor)
    parent = headers(data["user"])
    change = {"meal_status": "Kahvaltı: Tümünü Yedi", "sleep_status": "30 dk", "mood": None,
        "activities": ["Çizim"], "teacher_notes": "Güncel gözlem"}
    assert (await client.put(path, headers=parent, json=change)).status_code == 403
    assert (await client.put(other_path, headers=teacher, json=change)).status_code == 404
    response = await client.put(path, headers=teacher, json=change)
    assert response.status_code == 200, response.text
    readback = await client.get(path, headers=teacher)
    assert readback.status_code == 200, readback.text
    assert readback.json()["data"] == response.json()["data"]
    assert {key: readback.json()["data"][key] for key in change} == change
    assert (await client.delete(other_path, headers=teacher)).status_code == 404
    assert (await client.delete(path, headers=teacher)).status_code == 200
    assert (await client.get(path, headers=teacher)).status_code == 404
    async with sessions() as db:
        other_record = await db.get(DailyDevelopmentReport, unassigned_id)
        assert other_record.teacher_notes == "Korunacak"


async def test_concurrent_daily_report_write_and_stale_delete_preserve_latest_record(materials_client, monkeypatch):  # noqa: F811
    client, _, data = materials_client
    actor = headers(data["teacher"])
    child = data["children"][0]
    created = await client.post("/api/daily-reports", headers=actor, json={"student_id": str(child.id),
        "date": "2026-11-19", "teacher_notes": "İlk not"})
    assert created.status_code == 200, created.text
    initial = created.json()["data"]
    path = f'/api/daily-reports/{initial["id"]}'
    stale = {**actor, "If-Match": f'"{initial["version"]}"'}

    captured = asyncio.Event()
    release = asyncio.Event()
    original = daily_reports.mutation_filter

    async def pause_first_snapshot(*args):
        conditions = await original(*args)
        if not captured.is_set():
            captured.set()
            await release.wait()
        return conditions

    monkeypatch.setattr(daily_reports, "mutation_filter", pause_first_snapshot)
    first = asyncio.create_task(client.put(path, headers=stale, json={"teacher_notes": "Eski taslak"}))
    try:
        await asyncio.wait_for(captured.wait(), timeout=8)
        newer = await client.put(path, headers=stale, json={"teacher_notes": "Yeni gözlem"})
    finally:
        release.set()
        superseded = await first
    assert newer.status_code == 200, newer.text
    assert superseded.status_code == 412, superseded.text
    latest = newer.json()["data"]
    assert latest["version"] != initial["version"]
    assert (await client.delete(path, headers=stale)).status_code == 412
    assert (await client.get(path, headers=actor)).json()["data"]["teacher_notes"] == "Yeni gözlem"
    assert (await client.delete(path, headers={**actor, "If-Match": f'"{latest["version"]}"'})).status_code == 200


async def test_daily_report_student_choices_follow_write_permission_and_assignments(materials_client):  # noqa: F811
    client, sessions, data = materials_client
    teacher, branch, institution = data["teacher"], data["branch"], data["org"]
    async with sessions() as db:
        role = (await db.execute(select(Role).where(Role.slug == "teacher").options(selectinload(Role.permissions)))).scalar_one()
        role.permissions = [permission for permission in role.permissions
            if permission.code not in {"students.read", "daily_reports.read", "academic.read"}]
        distant = Branch(name="Other campus", organization_id=institution.id)
        db.add_all([distant, UserBranch(user_id=teacher.id, branch_id=branch.id)])
        await db.flush()
        distant_class = ClassRoom(name="Other class", organization_id=institution.id, branch_id=distant.id)
        db.add(distant_class)
        await db.flush()

        def student(name, campus, classroom=None, number=None):
            return Student(first_name=name, last_name="Test", organization_id=institution.id,
                branch_id=campus.id, class_id=classroom.id if classroom else None, student_number=number)

        direct = student("Bireysel", branch, data["other_class"], "KARNE-11")
        unrelated = student("Unassigned", branch, data["other_class"])
        without_class = student("Classless", branch)
        outside = student("Another campus", distant, distant_class)
        db.add_all([direct, unrelated, without_class, outside])
        await db.flush()
        db.add_all([StudentTeacherAssignment(student_id=row.id, teacher_id=teacher.id, subject_name="Matematik")
            for row in (direct, without_class, outside)])
        await db.commit()

    authorization = headers(teacher)
    path = "/api/daily-reports/student-options"
    assert (await client.get(path, headers=headers(data["user"]))).status_code == 403
    assert (await client.get("/api/students", headers=authorization)).status_code == 403
    assert (await client.get("/api/daily-reports", headers=authorization)).status_code == 403

    async def listed(**params):
        response = await client.get(path, headers=authorization, params=params)
        assert response.status_code == 200, response.text
        return response.json()["data"]

    selected = {"id": str(direct.id), "name": "Bireysel Test · KARNE-11", "student_name": "Bireysel Test",
        "class_id": str(direct.class_id)}
    page = await listed(page=2, page_size=1, selected_id=str(direct.id))
    assert page["total"] == 3 and page["total_pages"] == 3 and page["selected"] == selected
    assert selected not in page["items"]
    assert (await listed(search="KARNE-11", branch_id=str(branch.id)))["items"] == [selected]
    assert (await listed(class_id=str(direct.class_id)))["items"] == [selected]
    assert (await listed(class_id=str(distant_class.id)))["items"] == []
    for excluded in (unrelated, without_class, outside, data["stranger"]):
        assert (await listed(selected_id=str(excluded.id)))["selected"] is None
    created = await client.post("/api/daily-reports", headers=authorization,
        json={"student_id": str(direct.id), "class_id": selected["class_id"], "date": "2026-11-19", "teacher_notes": "Bireysel gözlem"})
    assert created.status_code == 200, created.text
    assert created.json()["data"]["student_id"] == str(direct.id)
