from datetime import date, time
from uuid import uuid4

from sqlalchemy import func, select
from test_material_files import materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401

from app.core.security import create_access_token
from app.infrastructure.models.models import Appointment, NotificationJob, Permission, Role, TimeSlot


async def test_parent_appointment_options_creation_replay_and_cancellation(materials_client):
    client, sessions, fixture = materials_client
    parent, child, teacher = fixture["user"], fixture["children"][0], fixture["teacher"]
    async with sessions() as db:
        role = await db.scalar(select(Role).where(Role.slug == "parent", Role.organization_id == fixture["org"].id))
        await db.refresh(role, ["permissions"])
        for code in ("appointments.read", "appointments.write"):
            role.permissions.append(Permission(code=code, name=code, module="appointments"))
        db.add(TimeSlot(teacher_id=teacher.id, date=date(2027, 1, 4), start_time=time(14), end_time=time(14, 30)))
        await db.commit()
    auth = {"Authorization": "Bearer " + create_access_token(parent.id)}
    route = "/api/appointments"
    options = await client.get(route + "/options", headers=auth, params={"page_size": 1})
    assert options.status_code == 200, options.text
    assert options.json()["data"]["total"] == 2
    second = await client.get(route + "/options", headers=auth, params={"page": 2, "page_size": 1})
    assert {options.json()["data"]["items"][0]["id"], second.json()["data"]["items"][0]["id"]} == {
        str(row.id) for row in fixture["children"]}
    assert (await client.get(route + "/options", headers=auth,
        params={"student_id": str(fixture["stranger"].id)})).status_code == 404
    teachers = await client.get(route + "/options", headers=auth, params={"student_id": str(child.id)})
    assert teachers.status_code == 200 and [row["id"] for row in teachers.json()["data"]["items"]] == [str(teacher.id)]
    slots = await client.get(route + "/teacher-slots/" + str(teacher.id), headers=auth, params={"date": "2027-01-04"})
    assert slots.status_code == 200 and slots.json()["data"][0]["start_time"] == "14:00"
    key = str(uuid4())
    payload = dict(teacher_id=str(teacher.id), student_id=str(child.id), slot_datetime="2027-01-04T14:00",
        parent_note="Görüşme notu", duration_minutes=30, request_id=key)
    created = await client.post(route + "/request", headers=auth, json=payload)
    assert created.status_code == 200, created.text
    assert created.json()["data"]["id"] == key and created.json()["data"]["status"] == "PENDING"
    replay = await client.post(route + "/request", headers=auth, json=payload)
    assert replay.status_code == 200 and replay.json()["data"] == created.json()["data"]
    assert (await client.post(route + "/request", headers=auth, json={**payload, "parent_note": "Different"})).status_code == 409
    rows = (await client.get(route, headers=auth, params={"branch_id": str(fixture["branch"].id)})).json()["data"]
    rows = rows["items"] if isinstance(rows, dict) else rows
    assert len(rows) == 1 and rows[0]["id"] == key and rows[0]["appointment_time"] == "14:00"
    assert (await client.patch(f"{route}/{key}/status", headers=auth, json={"status": "APPROVED"})).status_code == 403
    cancelled = await client.patch(f"{route}/{key}/status", headers=auth, json={"status": "CANCELLED"})
    assert cancelled.status_code == 200 and cancelled.json()["data"]["status"] == "CANCELLED"
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(Appointment)) == 1
        assert await db.scalar(select(func.count()).select_from(NotificationJob)) == 0
