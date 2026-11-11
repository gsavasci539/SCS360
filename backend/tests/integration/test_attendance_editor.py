import asyncio
from datetime import date
from uuid import uuid4

from sqlalchemy import select
from test_material_files import headers, materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from test_saas_platform import platform_client  # noqa: F401

from app.infrastructure.models.models import AttendanceRecord

DAY = date(2026, 11, 10)


def auth(data):
    return {**headers(data["root"]), "X-SCS360-Organization-Id": str(data["org"].id)}


async def seed(sessions, data):
    async with sessions() as db:
        row = AttendanceRecord(organization_id=data["org"].id, branch_id=data["branch"].id,
            class_id=data["classroom"].id, student_id=data["children"][0].id,
            attendance_date=DAY, status="ABSENT", notes="Original note", recorded_by=data["teacher"].id)
        db.add(row)
        await db.commit()
        return row.id


async def listing(client, data):
    reply = await client.get("/api/attendance", headers=auth(data), params={"class_id": str(data["classroom"].id), "attendance_date": DAY.isoformat()})
    assert reply.status_code == 200, reply.text
    return reply.json()["data"]["items"]


async def test_attendance_editor_reads_notes_and_atomically_edits_creates_and_replays(platform_client):  # noqa: F811
    client, sessions, data = platform_client
    identifier = await seed(sessions, data)
    rows = await listing(client, data)
    assert rows[0]["notes"] == "Original note" and len(rows[0]["version"]) == 64
    body = {"class_id": str(data["classroom"].id), "attendance_date": DAY.isoformat(), "request_id": str(uuid4()),
        "records": [{"student_id": str(data["children"][0].id), "status": "LATE", "notes": "Edited note", "expected_version": rows[0]["version"]},
            {"student_id": str(data["children"][1].id), "status": "EXCUSED", "notes": "New note", "expected_version": None}]}
    first = await client.put("/api/attendance/bulk", headers=auth(data), json=body)
    assert first.status_code == 200, first.text
    assert {key: first.json()["data"][key] for key in ("created", "updated", "unchanged")} == {"created": 1, "updated": 1, "unchanged": 0}
    retry = await client.put("/api/attendance/bulk", headers=auth(data), json=body)
    assert retry.status_code == 200 and retry.json()["data"] == first.json()["data"]
    async with sessions() as db:
        row = await db.get(AttendanceRecord, identifier)
        assert row.status.value == "LATE" and row.notes == "Edited note" and row.recorded_by == data["teacher"].id
        records = (await db.execute(select(AttendanceRecord))).scalars().all()
        assert len(records) == 2 and {r.notes for r in records} == {"Edited note", "New note"}
    assert (await client.put("/api/attendance/bulk", headers=auth(data), json={**body, "request_id": str(uuid4())})).status_code == 409
    assert (await client.put("/api/attendance/bulk", headers=auth(data), json={**body, "records": body["records"][:1]})).status_code == 409


async def test_attendance_editor_conflict_rolls_back_other_rows_and_does_not_move_class(platform_client):  # noqa: F811
    client, sessions, data = platform_client
    identifier = await seed(sessions, data)
    rows = await listing(client, data)
    body = {"class_id": str(data["classroom"].id), "attendance_date": DAY.isoformat(), "request_id": str(uuid4()),
        "records": [{"student_id": str(data["children"][1].id), "status": "PRESENT", "notes": "Must rollback", "expected_version": None},
            {"student_id": str(data["children"][0].id), "status": "LATE", "notes": "Stale", "expected_version": "0" * 64}]}
    assert (await client.put("/api/attendance/bulk", headers=auth(data), json=body)).status_code == 409
    async with sessions() as db:
        assert len((await db.execute(select(AttendanceRecord))).scalars().all()) == 1
        assert (await db.get(AttendanceRecord, identifier)).notes == "Original note"
    body["class_id"] = str(data["other_class"].id)
    body["records"] = [{"student_id": str(data["children"][0].id), "status": "PRESENT", "expected_version": rows[0]["version"]}]
    assert (await client.put("/api/attendance/bulk", headers=auth(data), json=body)).status_code in (403, 409)


async def test_attendance_editor_denies_foreign_student_and_validates_input(platform_client):  # noqa: F811
    client, _, data = platform_client
    body = {"class_id": str(data["classroom"].id), "attendance_date": DAY.isoformat(), "request_id": str(uuid4()),
        "records": [{"student_id": str(data["stranger"].id), "status": "PRESENT", "expected_version": None}]}
    assert (await client.put("/api/attendance/bulk", headers=auth(data), json=body)).status_code in (403, 404)
    assert (await client.put("/api/attendance/bulk", headers=headers(data["root"]), json=body)).status_code == 403
    assert (await client.put("/api/attendance/bulk", headers=headers(data["user"]), json=body)).status_code == 403
    for field, invalid in (("attendance_date", "2026-02-30"), ("class_id", "invalid"), ("request_id", "invalid")):
        assert (await client.put("/api/attendance/bulk", headers=auth(data), json={**body, field: invalid})).status_code == 422
    own = {"student_id": str(data["children"][0].id), "status": "PRESENT"}
    assert (await client.put("/api/attendance/bulk", headers=auth(data), json={**body, "records": [own, own]})).status_code == 422
    assert (await client.get("/api/attendance", headers=auth(data), params={"attendance_date": "wrong"})).status_code == 422


async def test_attendance_legacy_bulk_preserves_new_notes_and_reports_skipped_existing(platform_client):  # noqa: F811
    client, sessions, data = platform_client
    await seed(sessions, data)
    body = {"class_id": str(data["classroom"].id), "attendance_date": DAY.isoformat(),
        "records": [{"student_id": str(child.id), "status": "PRESENT", "notes": "New note"} for child in data["children"]]}
    reply = await client.post("/api/attendance/bulk", headers=auth(data), json=body)
    assert reply.status_code == 200, reply.text
    assert reply.json()["data"] == {"created": 1, "skipped": 1}
    rows = await listing(client, data)
    assert {r["notes"] for r in rows} == {"Original note", "New note"}


async def test_two_attendance_editors_cannot_silently_overwrite_each_other(platform_client):  # noqa: F811
    client, sessions, data = platform_client
    await seed(sessions, data)
    original = (await listing(client, data))[0]
    bodies = [{"class_id": str(data["classroom"].id), "attendance_date": DAY.isoformat(), "request_id": str(uuid4()),
        "records": [{"student_id": str(data["children"][0].id), "status": status, "notes": status,
            "expected_version": original["version"]}]} for status in ("LATE", "EXCUSED")]
    results = await asyncio.gather(*[client.put("/api/attendance/bulk", headers=auth(data), json=body) for body in bodies])
    assert sorted(r.status_code for r in results) == [200, 409], [r.text for r in results]
    saved = (await listing(client, data))[0]
    assert saved["status"] in ("LATE", "EXCUSED") and saved["notes"] == saved["status"]


async def test_noop_attendance_retry_does_not_undo_a_later_edit(platform_client):  # noqa: F811
    client, sessions, data = platform_client
    await seed(sessions, data)
    original = (await listing(client, data))[0]
    body = {"class_id": str(data["classroom"].id), "attendance_date": DAY.isoformat(), "request_id": str(uuid4()),
        "records": [{"student_id": str(data["children"][0].id), "status": "ABSENT", "notes": original["notes"], "expected_version": original["version"]}]}
    noop = await client.put("/api/attendance/bulk", headers=auth(data), json=body)
    assert noop.status_code == 200 and noop.json()["data"]["unchanged"] == 1
    changed = {**body, "request_id": str(uuid4()), "records": [{**body["records"][0], "status": "LATE", "notes": "Later edit"}]}
    assert (await client.put("/api/attendance/bulk", headers=auth(data), json=changed)).status_code == 200
    assert (await client.put("/api/attendance/bulk", headers=auth(data), json=body)).json()["data"] == noop.json()["data"]
    assert (await listing(client, data))[0]["notes"] == "Later edit"
