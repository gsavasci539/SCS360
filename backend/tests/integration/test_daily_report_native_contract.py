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


async def test_daily_report_concurrent_creates_keep_one_record_per_selected_date(materials_client):  # noqa: F811
    client, _, data = materials_client
    child = data["children"][0]
    path = "/api/daily-reports"
    authorization = headers(data["teacher"])
    draft = {"student_id": str(child.id), "class_id": str(child.class_id), "date": "2026-11-16"}
    first, second = await asyncio.gather(
        client.post(path, headers=authorization, json={**draft, "teacher_notes": "Birinci gözlem"}),
        client.post(path, headers=authorization, json={**draft, "teacher_notes": "İkinci gözlem"}),
    )
    assert sorted([first.status_code, second.status_code]) == [200, 409], (first.text, second.text)
    created = (first if first.status_code == 200 else second).json()["data"]
    historical = await client.post(path, headers=authorization, json={**draft, "date": "2026-11-15"})
    assert historical.status_code == 200, historical.text
    assert historical.json()["data"]["id"] != created["id"]
    listed = await client.get(path, headers=authorization, params={"student_id": str(child.id), "date": draft["date"]})
    assert listed.json()["data"]["items"] == [created]


async def test_daily_report_filters_before_pagination_and_preserves_scope(materials_client):  # noqa: F811
    client, sessions, data = materials_client
    match, newer = data["children"]
    async with sessions() as db:
        visible = await db.get(Student, match.id)
        visible.first_name, visible.last_name = "IŞIK", "ÇAĞLAR"
        visible.student_number = "KARNE-20"
        outside = Student(first_name="IŞIK", last_name="ÇAĞLAR", organization_id=visible.organization_id,
            branch_id=visible.branch_id, class_id=data["other_class"].id)
        db.add(outside)
        await db.flush()
        db.add_all([DailyDevelopmentReport(student_id=student.id, class_id=student.class_id,
            date=date(2026, 11, day), teacher_notes=note) for student, day, note in [
            (outside, 20, "Kapsam dışı %_"), (newer, 19, "Yeni karne"),
            (visible, 18, "Gözlem %_ kayıtlı"), (visible, 17, "Önceki karne"),
        ]])
        await db.commit()

    async def listed(**params):
        response = await client.get("/api/daily-reports", headers=headers(data["teacher"]), params=params)
        assert response.status_code == 200, response.text
        return response.json()["data"]

    assert (await listed(page_size=1))["items"][0]["student_id"] == str(newer.id)
    filtered = await listed(page_size=1, search="  ışık  çağlar  ")
    assert (filtered["total"], filtered["total_pages"]) == (2, 2)
    assert [(row["student_id"], row["date"]) for row in filtered["items"]] == [(str(match.id), "2026-11-18")]
    assert (await listed(page_size=1, page=2, search="KARNE-20"))["items"][0]["date"] == "2026-11-17"
    by_date = await listed(search="ışık çağlar", date="2026-11-17", branch_id=str(data["branch"].id))
    assert by_date["total"] == 1 and by_date["items"][0]["date"] == "2026-11-17"
    literal = await listed(search="%_")
    assert literal["total"] == 1 and literal["items"][0]["student_id"] == str(match.id)


async def test_daily_report_bulk_create_preserves_order_and_rolls_back_on_conflict(materials_client):  # noqa: F811
    client, _, data = materials_client
    path = "/api/daily-reports"
    authorization = headers(data["teacher"])
    higher, lower = sorted((str(child.id) for child in data["children"]), reverse=True)
    batch = {"class_id": str(data["classroom"].id), "date": "2026-11-15", "reports": [
        {"student_id": student, "date": "2026-11-15", "teacher_notes": "Toplu gözlem"}
        for student in (higher, lower)
    ]}
    response = await client.post(f"{path}/bulk", headers=authorization, json=batch)
    assert response.status_code == 200, response.text
    assert [row["student_id"] for row in response.json()["data"]] == [higher, lower]

    conflict_date = "2026-11-16"
    existing = await client.post(path, headers=authorization, json={"student_id": higher, "date": conflict_date})
    assert existing.status_code == 200, existing.text
    conflict = await client.post(f"{path}/bulk", headers=authorization, json={**batch, "date": conflict_date})
    assert conflict.status_code == 409, conflict.text
    remaining = await client.get(path, headers=authorization, params={"date": conflict_date})
    assert remaining.json()["data"]["items"] == [existing.json()["data"]]


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
    assert (await client.get("/api/ai/ai-daily-reports-analysis", headers=authorization)).status_code == 403

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


async def test_daily_report_analysis_uses_the_readable_student_scope(materials_client):  # noqa: F811
    client, sessions, data = materials_client
    teacher, branch, institution = data["teacher"], data["branch"], data["org"]
    authorization = headers(teacher)
    path = "/api/ai/ai-daily-reports-analysis"
    empty = await client.get(path, headers=authorization)
    assert empty.status_code == 200, empty.text
    assert empty.json()["data"]["recommendations"] == ["Gösterilebilecek günlük karne bulunamadı."]

    async with sessions() as db:
        distant = Branch(name="Other campus", organization_id=institution.id)
        db.add_all([distant, UserBranch(user_id=teacher.id, branch_id=branch.id)])
        await db.flush()
        distant_class = ClassRoom(name="Outside classroom", organization_id=institution.id, branch_id=distant.id)
        db.add(distant_class)
        await db.flush()
        outside = Student(first_name="Outside", last_name="Test", organization_id=institution.id,
            branch_id=distant.id, class_id=distant_class.id)
        unrelated = Student(first_name="Unassigned", last_name="Test", organization_id=institution.id,
            branch_id=branch.id, class_id=data["other_class"].id)
        db.add_all([outside, unrelated])
        await db.flush()
        db.add(StudentTeacherAssignment(student_id=outside.id, teacher_id=teacher.id, subject_name="Matematik"))
        child = data["children"][0]
        db.add_all([DailyDevelopmentReport(student_id=student.id, class_id=student.class_id,
            date=date(2026, 11, 19), mood="TIRED", sleep_status="SHORT", meal_status="NONE")
            for student in (child, outside, unrelated)])
        await db.commit()

    response = await client.get(path, headers=authorization)
    assert response.status_code == 200, response.text
    result = response.json()["data"]
    assert result["report_stats"]["total"] == 1
    assert [row["student_id"] for row in result["students_needing_attention"]] == [str(child.id)]

    denied = await client.get(path, headers=authorization, params={"branch_id": str(distant.id)})
    assert denied.status_code == 404, denied.text
    foreign = await client.get(path, headers=authorization, params={"branch_id": str(data["other_branch"].id)})
    assert foreign.status_code == 404, foreign.text

    async with sessions() as db:
        db.add(UserBranch(user_id=teacher.id, branch_id=distant.id))
        await db.commit()

    all_branches = await client.get(path, headers=authorization)
    assert all_branches.status_code == 200, all_branches.text
    assert all_branches.json()["data"]["report_stats"]["total"] == 2
    chosen = await client.get(path, headers=authorization, params={"branch_id": str(distant.id)})
    assert chosen.status_code == 200, chosen.text
    selected = chosen.json()["data"]
    assert selected["branch_id"] == str(distant.id) and selected["report_stats"]["total"] == 1
    assert [row["student_id"] for row in selected["students_needing_attention"]] == [str(outside.id)]


async def test_daily_report_analysis_counts_observed_web_and_android_values(materials_client):  # noqa: F811
    client, _, data = materials_client
    authorization = headers(data["teacher"])
    first, second = data["children"]
    path = "/api/ai/ai-daily-reports-analysis"

    async def create(student, day, **fields):
        response = await client.post("/api/daily-reports", headers=authorization,
            json={"student_id": str(student.id), "date": day, **fields})
        assert response.status_code == 200, response.text

    await create(first, "2026-11-19", mood="Not happy", meal_status="Allergy note", teacher_notes="Henüz gözlem yok")
    unknown = (await client.get(path, headers=authorization)).json()["data"]
    assert unknown["recommendations"] == ["Özetlenecek kayıtlı gözlem bulunamadı."]
    assert unknown["students_needing_attention"] == []
    assert all(unknown["report_stats"][f"{domain}_rate"] is None for domain in ("mood", "sleep", "meal"))

    await create(first, "2026-11-18", mood="HAPPY", sleep_status="SHORT", meal_status="ALL")
    await create(first, "2026-11-17", mood="Çok Neşeli & Uyumlu", sleep_status="30 dk",
        meal_breakfast="Tümünü Yedi", meal_lunch="Yarısını Yedi", meal_snack="Yemedi")
    await create(first, "2026-11-16", mood="Sakin")
    await create(second, "2026-11-15", mood="Yorgun", sleep_status="Uyumadı")
    response = await client.get(path, headers=authorization)
    assert response.status_code == 200, response.text
    analysis = response.json()["data"]
    assert analysis["report_stats"] == {
        "total": 5, "mood_happy": 2, "mood_tired": 1,
        "mood_observations": 4, "sleep_observations": 3, "meal_observations": 4,
        "mood_rate": 50, "sleep_rate": 66.7, "meal_rate": 50,
    }
    follow_up = {row["student_id"]: row for row in analysis["students_needing_attention"]}
    assert follow_up[str(first.id)]["poor_meal"] == 2
    assert follow_up[str(second.id)]["poor_meal"] == 0
