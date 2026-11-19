import asyncio
from datetime import date

from test_material_files import headers, materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401

from app.infrastructure.models.models import DailyDevelopmentReport, Student
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
