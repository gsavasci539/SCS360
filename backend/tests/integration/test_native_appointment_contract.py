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
    assert (await client.delete(f"{route}/{key}", headers=auth)).status_code == 403
    cancelled = await client.patch(f"{route}/{key}/status", headers=auth, json={"status": "CANCELLED"})
    assert cancelled.status_code == 200 and cancelled.json()["data"]["status"] == "CANCELLED"
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(Appointment)) == 1
        assert await db.scalar(select(func.count()).select_from(NotificationJob)) == 0


async def test_teacher_manages_only_own_slots_and_deletes_own_appointment(materials_client):
    client, sessions, fixture = materials_client
    parent, teacher, child = fixture["user"], fixture["teacher"], fixture["children"][0]
    async with sessions() as db:
        roles = (await db.scalars(select(Role).where(
            Role.organization_id == fixture["org"].id, Role.slug.in_(("parent", "teacher")),
        ))).all()
        permissions = [Permission(code=code, name=code, module="appointments")
                       for code in ("appointments.read", "appointments.write")]
        for role in roles:
            await db.refresh(role, ["permissions"])
            role.permissions.extend(permissions)
        await db.commit()
    teacher_auth = {"Authorization": "Bearer " + create_access_token(teacher.id)}
    parent_auth = {"Authorization": "Bearer " + create_access_token(parent.id)}
    route = "/api/appointments"
    date_filter = {"date": "2027-01-04"}
    payload = {**date_filter, "teacher_id": str(teacher.id), "start_time": "14:00", "end_time": "14:30"}
    assert (await client.get(route + "/slots", headers=parent_auth, params=date_filter)).status_code == 403
    assert (await client.post(route + "/slots", headers=parent_auth, json=payload)).status_code == 403
    assert (await client.get(route + "/slots", headers=teacher_auth,
        params={**date_filter, "teacher_id": str(parent.id)})).status_code == 403
    created = await client.post(route + "/slots", headers=teacher_auth, json=payload)
    assert created.status_code == 200, created.text
    slot = created.json()["data"]
    replay = await client.post(route + "/slots", headers=teacher_auth, json=payload)
    assert replay.json()["data"] == slot
    assert (await client.post(route + "/slots", headers=teacher_auth,
        json={**payload, "start_time": "14:15"})).status_code == 409
    listed = await client.get(route + "/slots", headers=teacher_auth, params=date_filter)
    assert listed.json()["data"] == [slot]
    slot_url = f"{route}/slots/{slot['id']}"
    assert (await client.delete(slot_url, headers=parent_auth)).status_code == 403
    key = str(uuid4())
    booked = await client.post(route + "/request", headers=parent_auth, json={
        "teacher_id": str(teacher.id), "student_id": str(child.id),
        "slot_datetime": "2027-01-04T14:00", "duration_minutes": 30, "request_id": key,
    })
    assert booked.status_code == 200, booked.text
    assert (await client.get(route + "/slots", headers=teacher_auth, params=date_filter)).json()["data"] == [slot]
    detail_url = f"{route}/{key}"
    status_url = detail_url + "/status"
    note = "Görüşme notu\nİkinci satır"
    assert (await client.patch(status_url, headers=teacher_auth, json={
        "status": "APPROVED", "feedback_notes": note,
    })).status_code == 200
    assert (await client.put(detail_url, headers=teacher_auth, json={"status": "confirmed"})).status_code == 200
    assert (await client.get(detail_url, headers=teacher_auth)).json()["data"]["feedback_notes"] == note
    assert (await client.patch(status_url, headers=parent_auth, json={
        "status": "CANCELLED", "feedback_notes": "Veli metni",
    })).status_code == 200
    assert (await client.get(detail_url, headers=teacher_auth)).json()["data"]["feedback_notes"] == note
    assert (await client.patch(status_url, headers=teacher_auth, json={"status": "COMPLETED"})).status_code == 200
    assert (await client.get(detail_url, headers=teacher_auth)).json()["data"]["feedback_notes"] == note
    assert (await client.put(status_url, headers=teacher_auth, json={
        "status": "completed", "teacher_note": None,
    })).status_code == 200
    assert (await client.get(detail_url, headers=teacher_auth)).json()["data"]["feedback_notes"] is None
    assert (await client.delete(f"{route}/{key}", headers=teacher_auth)).status_code == 200
    assert (await client.get(f"{route}/{key}", headers=teacher_auth)).status_code == 404
    assert (await client.delete(slot_url, headers=teacher_auth)).status_code == 200
    assert (await client.get(route + "/slots", headers=teacher_auth, params=date_filter)).json()["data"] == []
