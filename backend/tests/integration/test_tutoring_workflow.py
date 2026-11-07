import asyncio
from datetime import timedelta

import pytest
from sqlalchemy import select

from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.core.dates import school_today
from app.infrastructure.models.models import Permission, Role, RolePermission, User, ClassTeacher, Student, Branch, ClassRoom


@pytest.fixture
async def tutoring_client(materials_client):
    client, sessions, data = materials_client
    async with sessions() as db:
        role = (await db.execute(select(Role).where(Role.slug == "teacher"))).scalar_one()
        permissions = [Permission(code=code, name=code, module="tutoring") for code in ("tutoring.read", "tutoring.write")]
        db.add_all(permissions); await db.flush()
        db.add_all([RolePermission(role_id=role.id, permission_id=row.id) for row in permissions])
        other = User(email="other-tutor@test.invalid", password_hash="unused", first_name="Other", last_name="Tutor",
            organization_id=data["org"].id, roles=[role], branches=[data["branch"]])
        manager = User(email="tutoring-manager@test.invalid", password_hash="unused", first_name="Tutoring", last_name="Manager",
            organization_id=data["org"].id, branches=[data["branch"]], roles=[Role(name="Tutor manager", slug="branch_manager",
                organization_id=data["org"].id, permissions=permissions)])
        db.add_all([other, manager]); await db.flush()
        db.add(ClassTeacher(class_id=data["classroom"].id, user_id=other.id))
        await db.commit()
        data = {**data, "other_teacher": other, "manager": manager}
    return client, sessions, data


def request_body(data, **extra):
    return {"student_id": str(data["children"][0].id), "teacher_id": str(data["teacher"].id),
        "requested_date": str(school_today() + timedelta(days=1)), "subject": "Mathematics", **extra}


async def test_tutoring_approval_records_real_actor_and_retry_preserves_first_decision(tutoring_client):
    client, _, data = tutoring_client
    auth = headers(data["teacher"])
    created = await client.post("/api/tutoring/requests", headers=auth, json=request_body(data))
    assert created.status_code == 200, created.text
    identifier = created.json()["data"]["id"]
    approvals = await asyncio.gather(*[client.post(f"/api/tutoring/requests/{identifier}/approve", headers=auth) for _ in range(2)])
    assert all(row.status_code == 200 for row in approvals), [row.text for row in approvals]
    assert approvals[0].json()["data"]["approved_at"] == approvals[1].json()["data"]["approved_at"]
    response = approvals[0]
    assert response.status_code == 200, response.text
    assert response.json()["data"].get("approved_by") == str(data["teacher"].id), response.text
    repeated = await client.post(f"/api/tutoring/requests/{identifier}/approve", headers=auth)
    assert repeated.json()["data"]["approved_at"] == response.json()["data"]["approved_at"]
    rejected = await client.post(f"/api/tutoring/requests/{identifier}/reject", headers=auth, json={"rejection_reason": "Too late"})
    assert rejected.status_code == 409, rejected.text


async def test_tutoring_teacher_cannot_write_another_teachers_calendar_or_session(tutoring_client):
    client, _, data = tutoring_client
    auth = headers(data["teacher"])
    availability = {"teacher_id": str(data["other_teacher"].id), "day_of_week": 1, "start_time": "09:00", "end_time": "12:00"}
    denied = await client.post("/api/tutoring/availability", headers=auth, json=availability)
    assert denied.status_code == 403, denied.text
    body = {"teacher_id": str(data["other_teacher"].id), "student_id": str(data["children"][0].id),
        "session_date": str(school_today() + timedelta(days=1)), "start_time": "10:00", "end_time": "11:00"}
    assert (await client.post("/api/tutoring/sessions", headers=auth, json=body)).status_code == 403


async def test_tutoring_validates_times_and_serializes_conflicting_bookings(tutoring_client):
    client, _, data = tutoring_client
    auth = headers(data["teacher"])
    day = school_today() + timedelta(days=1)
    availability = {"teacher_id": str(data["teacher"].id), "day_of_week": day.weekday(), "start_time": "09:00", "end_time": "12:00", "max_students": 1}
    invalid = await client.post("/api/tutoring/availability", headers=auth, json={**availability, "end_time": "08:00"})
    assert invalid.status_code == 422, invalid.text
    assert (await client.post("/api/tutoring/availability", headers=auth, json=availability)).status_code == 200
    session = {"teacher_id": str(data["teacher"].id), "student_id": str(data["children"][0].id),
        "session_date": str(day), "start_time": "10:00", "end_time": "11:00", "subject": "Math"}
    responses = await asyncio.gather(*[client.post("/api/tutoring/sessions", headers=auth, json={**session,
        "student_id": str(child.id)}) for child in data["children"]])
    assert sorted(row.status_code for row in responses) == [200, 409], [row.text for row in responses]
    booked = next(row for row in responses if row.status_code == 200).json()["data"]["id"]
    attendance = await client.post(f"/api/tutoring/sessions/{booked}/attendance", headers=auth, json={"attendance_status": "UNKNOWN"})
    assert attendance.status_code == 422
    attendance = await client.post(f"/api/tutoring/sessions/{booked}/attendance", headers=auth, json={"attendance_status": "PRESENT", "progress_score": 87})
    assert attendance.status_code == 200, attendance.text
    moved = await client.put(f"/api/tutoring/sessions/{booked}", headers=auth, json={**session, "start_time": "11:00", "end_time": "12:00"})
    assert moved.status_code == 409


async def test_tutoring_scope_options_summary_and_request_states_are_real(tutoring_client):
    client, _, data = tutoring_client
    auth = headers(data["manager"])
    choices = await client.get("/api/tutoring/options", headers=auth, params={"student_id": str(data["children"][0].id)})
    assert choices.status_code == 200, choices.text
    assert {row["id"] for row in choices.json()["data"]["teachers"]} == {str(data["teacher"].id), str(data["other_teacher"].id)}
    assert str(data["stranger"].id) not in {row["id"] for row in choices.json()["data"]["students"]}
    forbidden = await client.post("/api/tutoring/requests", headers=auth, json=request_body(data, student_id=str(data["stranger"].id)))
    assert forbidden.status_code in {403, 404}
    created = await client.post("/api/tutoring/requests", headers=auth, json=request_body(data))
    identifier = created.json()["data"]["id"]
    # A second teacher of the same class still cannot decide the first teacher's request.
    denied = await client.post(f"/api/tutoring/requests/{identifier}/approve", headers=headers(data["other_teacher"]))
    assert denied.status_code in {403, 404}, denied.text
    rejected = await client.post(f"/api/tutoring/requests/{identifier}/reject", headers=auth, json={"rejection_reason": "Choose another date"})
    assert rejected.status_code == 200 and rejected.json()["data"]["rejection_reason"] == "Choose another date", rejected.text
    assert (await client.post(f"/api/tutoring/requests/{identifier}/approve", headers=auth)).status_code == 409
    summary = await client.get("/api/tutoring/summary", headers=auth)
    assert summary.status_code == 200 and summary.json()["data"]["rejected_requests"] == 1, summary.text
    assert summary.json()["data"]["total_sessions"] == 0
    legacy_analysis = await client.get("/api/ai/tutoring-analysis", headers=auth)
    assert legacy_analysis.status_code == 200 and legacy_analysis.json()["data"]["rejected_requests"] == 1
    assert (await client.get("/api/ai/tutoring-analysis", headers=headers(data["user"]))).status_code == 403


async def test_tutoring_capacity_uses_peak_overlap_and_student_conflicts_include_other_teachers(tutoring_client):
    client, sessions, data = tutoring_client
    auth = headers(data["teacher"])
    async with sessions() as db:
        children = [Student(first_name=f"Extra{i}", last_name="Tutor", organization_id=data["org"].id,
            branch_id=data["branch"].id, class_id=data["classroom"].id) for i in range(2)]
        db.add_all(children); await db.commit()
    day = school_today() + timedelta(days=2)
    availability = {"teacher_id": str(data["teacher"].id), "day_of_week": day.weekday(), "start_time": "09:00", "end_time": "12:00", "max_students": 2}
    window = await client.post("/api/tutoring/availability", headers=auth, json=availability)
    assert window.status_code == 200, window.text
    async def book(child, start, end, teacher=None):
        actor = teacher or data["teacher"]
        return await client.post("/api/tutoring/sessions", headers=headers(actor), json={"student_id": str(child.id),
            "teacher_id": str(actor.id), "session_date": str(day), "start_time": start, "end_time": end})
    first = await book(data["children"][0], "09:00", "10:00")
    second = await book(data["children"][1], "10:00", "11:00")
    spanning = await book(children[0], "09:00", "11:00")
    assert first.status_code == second.status_code == spanning.status_code == 200, spanning.text
    assert (await book(children[1], "09:30", "10:30")).status_code == 409
    other = data["other_teacher"]
    assert (await client.post("/api/tutoring/availability", headers=headers(other), json={**availability, "teacher_id": str(other.id)})).status_code == 200
    assert (await book(data["children"][0], "09:30", "10:30", other)).status_code == 409
    identifier = first.json()["data"]["id"]
    assert (await client.post(f"/api/tutoring/sessions/{identifier}/cancel", headers=auth)).status_code == 200
    assert (await book(data["children"][0], "09:30", "10:30", other)).status_code == 200
    assert (await client.post(f"/api/tutoring/sessions/{identifier}/attendance", headers=auth, json={"attendance_status": "PRESENT"})).status_code == 409
    assert (await client.delete("/api/tutoring/availability/" + window.json()["data"]["id"], headers=auth)).status_code == 200
    assert (await book(children[1], "11:00", "12:00")).status_code == 409
    # Disabling a recurring window must not erase or invalidate an existing lesson.
    assert (await client.post(f'/api/tutoring/sessions/{second.json()["data"]["id"]}/attendance', headers=auth,
        json={"attendance_status": "LATE", "progress_score": 82})).status_code == 200


async def test_tutoring_branch_calendar_scope_and_concurrent_unassigned_request_claim(tutoring_client):
    client, sessions, data = tutoring_client
    from app.domain.entities.tutoring import TeacherAvailability
    from datetime import time
    async with sessions() as db:
        branch = Branch(name="Private tutor branch", organization_id=data["org"].id)
        db.add(branch); await db.flush()
        other = User(email="private-tutor@test.invalid", password_hash="unused", first_name="Private", last_name="Tutor",
            organization_id=data["org"].id, branches=[branch])
        db.add(other); await db.flush()
        db.add(ClassRoom(name="Private class", teacher_id=other.id, branch_id=branch.id, organization_id=data["org"].id))
        window = TeacherAvailability(teacher_id=other.id, day_of_week=0, start_time=time(9), end_time=time(10))
        db.add(window); await db.commit()
    auth = headers(data["manager"])
    windows = await client.get("/api/tutoring/availability", headers=auth)
    assert windows.status_code == 200 and windows.json()["data"] == [], windows.text
    assert (await client.delete(f"/api/tutoring/availability/{window.id}", headers=auth)).status_code == 404
    denied = await client.post("/api/tutoring/availability", headers=auth, json={"teacher_id": str(other.id), "day_of_week": 1, "start_time": "09:00", "end_time": "10:00"})
    assert denied.status_code == 403, denied.text
    created = await client.post("/api/tutoring/requests", headers=auth, json=request_body(data, teacher_id=None))
    assert created.status_code == 200, created.text
    identifier = created.json()["data"]["id"]
    replies = await asyncio.gather(*[client.post(f"/api/tutoring/requests/{identifier}/approve", headers=headers(actor),
        json={"teacher_id": str(actor.id)}) for actor in (data["teacher"], data["other_teacher"])])
    assert sorted(row.status_code for row in replies) == [200, 404], [row.text for row in replies]
