import asyncio
from datetime import timedelta

import pytest
from sqlalchemy import select

from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.core.dates import school_today, school_day_bounds
from app.domain.entities.health import HealthRecord, MedicationLog, MedicationSchedule
from app.infrastructure.models.models import Permission, Role, RolePermission, User, ClassTeacher


@pytest.fixture
async def infirmary_client(materials_client):
    client, sessions, data = materials_client
    async with sessions() as db:
        permissions = [Permission(code=code, name=code, module="health") for code in ("health.read", "health.write", "parent.medicine_request")]
        db.add_all(permissions); await db.flush()
        parent_role = (await db.execute(select(Role).where(Role.slug == "parent"))).scalar_one()
        teacher_role = (await db.execute(select(Role).where(Role.slug == "teacher"))).scalar_one()
        db.add_all([RolePermission(role_id=parent_role.id, permission_id=permissions[2].id), RolePermission(role_id=teacher_role.id, permission_id=permissions[0].id)])
        nurse = User(email="nurse@test.invalid", password_hash="unused", first_name="Clinic", last_name="Officer",
            organization_id=data["org"].id, branches=[data["branch"]], roles=[Role(name="Clinic", slug="staff",
                organization_id=data["org"].id, permissions=permissions[:2])])
        db.add(nurse); await db.commit()
    return client, sessions, {**data, "nurse": nurse}


def schedule_body(data, **extra):
    return {"student_id": str(data["children"][0].id), "medication_name": "Acceptance record only", "dosage": "Test instruction",
        "frequency": "10:00", "instruction": "NOT_SPECIFIED", "start_date": str(school_today() - timedelta(days=3)), **extra}


async def test_health_record_path_cannot_create_a_different_child_and_upsert_is_serial(infirmary_client):
    client, sessions, data = infirmary_client
    child = str(data["children"][0].id); auth = headers(data["nurse"])
    bad = await client.put(f"/api/infirmary/health-records/{child}", headers=auth,
        json={"student_id": str(data["children"][1].id), "allergies": "Wrong child"})
    assert bad.status_code == 422, bad.text
    replies = await asyncio.gather(*[client.put(f"/api/infirmary/health-records/{child}", headers=auth,
        json={"student_id": child, "blood_type": "A+", "allergies": "Acceptance allergy"}) for _ in range(2)])
    assert all(row.status_code == 200 for row in replies), [row.text for row in replies]
    async with sessions() as db:
        rows = (await db.execute(select(HealthRecord))).scalars().all()
        assert len(rows) == 1 and rows[0].updated_by == data["nurse"].id
    denied = await client.put(f'/api/infirmary/health-records/{data["stranger"].id}', headers=auth,
        json={"student_id": str(data["stranger"].id), "allergies": "Forbidden"})
    assert denied.status_code in {403, 404}


async def test_medication_log_cannot_reference_another_childs_schedule(infirmary_client):
    client, _, data = infirmary_client
    auth = headers(data["nurse"])
    created = await client.post("/api/infirmary/medication-schedules", headers=auth, json=schedule_body(data))
    assert created.status_code == 200, created.text
    wrong = await client.post("/api/infirmary/medication/mark-given", headers=auth, json={"schedule_id": created.json()["data"]["id"],
        "student_id": str(data["children"][1].id), "scheduled_time": "10:00", "status": "GIVEN", "given_by": str(data["teacher"].id)})
    assert wrong.status_code in {403, 422}, wrong.text


async def test_staff_schedules_have_real_actor_and_nonempty_request_list_works_on_postgresql(infirmary_client):
    client, sessions, data = infirmary_client
    auth = headers(data["nurse"])
    created = await client.post("/api/infirmary/medication-schedules", headers=auth, json=schedule_body(data))
    assert created.status_code == 200, created.text
    async with sessions() as db:
        row = (await db.execute(select(MedicationSchedule))).scalar_one()
        assert row.created_by == row.updated_by == data["nurse"].id
    requests = await client.get("/api/infirmary/medicine-requests", headers=auth)
    assert requests.status_code == 200 and requests.json()["data"][0]["status"] == "APPROVED", requests.text


async def test_dose_dates_preserve_history_actor_and_same_day_retries_without_duplicate(infirmary_client):
    client, sessions, data = infirmary_client
    auth = headers(data["nurse"])
    created = await client.post("/api/infirmary/medication-schedules", headers=auth, json=schedule_body(data))
    identifier = created.json()["data"]["id"]
    body = {"schedule_id": identifier, "student_id": str(data["children"][0].id), "scheduled_time": "10:00",
        "scheduled_date": str(school_today()), "status": "GIVEN", "given_by": str(data["teacher"].id)}
    replies = await asyncio.gather(*[client.post("/api/infirmary/medication/mark-given", headers=auth, json=body) for _ in range(2)])
    assert all(row.status_code == 200 for row in replies), [row.text for row in replies]
    assert replies[0].json()["data"]["id"] == replies[1].json()["data"]["id"]
    assert replies[0].json()["data"]["given_time"] == replies[1].json()["data"]["given_time"]
    assert replies[0].json()["data"]["given_by"] == str(data["nurse"].id)
    yesterday = school_today() - timedelta(days=1)
    instant = school_day_bounds(yesterday)[0] + timedelta(hours=12)
    history = await client.post("/api/infirmary/medication/mark-given", headers=auth, json={**body,
        "scheduled_date": str(yesterday), "given_time": instant.isoformat()})
    assert history.status_code == 200 and history.json()["data"]["id"] != replies[0].json()["data"]["id"], history.text
    async with sessions() as db:
        assert len((await db.execute(select(MedicationLog))).scalars().all()) == 2
    # Several doses in one day must be a list, never scalar_one_or_none/500.
    assert (await client.post("/api/infirmary/medication/mark-given", headers=auth, json={**body, "scheduled_time": "11:00", "status": "SKIPPED"})).status_code == 200
    for day, count in ((school_today(), 2), (yesterday, 1)):
        result = await client.get("/api/infirmary/medication-logs", headers=auth, params={"date": str(day)})
        assert result.status_code == 200 and len(result.json()["data"]) == count, result.text
        daily = await client.get("/api/infirmary/daily-medication-schedule", headers=auth, params={"date": str(day)})
        assert daily.status_code == 200 and len(daily.json()["data"][0]["logs"]) == count, daily.text
    overwrite = await client.post("/api/infirmary/medication/mark-given", headers=auth, json={**body, "status": "SKIPPED"})
    assert overwrite.status_code == 409


async def test_parent_requests_need_review_and_rejection_persists_across_portals(infirmary_client):
    client, _, data = infirmary_client
    child = str(data["children"][0].id); auth = headers(data["nurse"])
    instructions = ("Parent supplied instructions " * 12).strip()
    path = f"/api/parent/child/{child}/medicine-requests"
    created = await client.post(path, headers=headers(data["user"]), json={"medicine_name": "Test record", "dosage": "Test instruction", "time_to_give": "10:00", "instructions": instructions})
    assert created.status_code == 200, created.text
    identifier = created.json()["data"]["id"]
    unapproved = await client.post("/api/infirmary/medication/mark-given", headers=auth, json={"schedule_id": identifier, "student_id": child, "scheduled_time": "10:00", "status": "GIVEN"})
    assert unapproved.status_code == 409
    decision = await client.put("/api/infirmary/medicine-requests/" + identifier, headers=auth, json={"status": "REJECTED"})
    assert decision.status_code == 200, decision.text
    again = await client.get(path, headers=headers(data["user"]))
    assert again.json()["data"]["medicine_requests"][0]["status"] == "REJECTED"
    assert again.json()["data"]["medicine_requests"][0]["instructions"] == instructions
    reopened = await client.put("/api/infirmary/medicine-requests/" + identifier, headers=auth, json={"status": "APPROVED"})
    assert reopened.status_code == 409


async def test_visits_derive_student_branch_examiner_and_summary_uses_real_rows(infirmary_client):
    client, _, data = infirmary_client
    auth = headers(data["nurse"])
    created = await client.post("/api/infirmary/infirmary-visits", headers=auth, json={"student_id": str(data["children"][0].id),
        "complaint": "Acceptance visit", "examined_by": str(data["teacher"].id), "follow_up_required": True})
    assert created.status_code == 200, created.text
    visits = await client.get("/api/infirmary/infirmary-visits", headers=auth)
    assert visits.json()["data"][0]["examined_by"] == str(data["nurse"].id)
    assert visits.json()["data"][0]["branch_id"] == str(data["branch"].id)
    result = await client.get("/api/infirmary/summary", headers=auth)
    assert result.status_code == 200 and result.json()["data"]["recent_visits"] == 1, result.text
    assert result.json()["data"]["follow_up_visits"] == 1
    readonly = await client.post("/api/infirmary/infirmary-visits", headers=headers(data["teacher"]), json={"student_id": str(data["children"][0].id)})
    assert readonly.status_code == 403


async def test_parent_notice_and_dashboard_adapters_cannot_bypass_clinical_permissions(infirmary_client):
    client, sessions, data = infirmary_client
    async with sessions() as db:
        permissions = {row.code: row for row in (await db.execute(select(Permission))).scalars()}
        for code in ("students.write", "dashboard.view"):
            permissions[code] = Permission(code=code, name=code, module="dashboard")
        observers = []
        for name, codes in (("reader", ("students.read", "students.write", "health.read", "dashboard.view")),
            ("academic", ("students.read", "students.write", "dashboard.view"))):
            user = User(email=f"{name}@clinic.invalid", password_hash="unused", first_name=name, last_name="Observer",
                organization_id=data["org"].id, branches=[data["branch"]], roles=[Role(name=name, slug="staff",
                    organization_id=data["org"].id, permissions=[permissions[code] for code in codes])])
            db.add(user); observers.append(user)
        teacher_without_health = User(email="no-clinic-teacher@test.invalid", password_hash="unused", first_name="Limited", last_name="Teacher",
            organization_id=data["org"].id, roles=[Role(name="Limited teacher", slug="teacher", organization_id=data["org"].id)], branches=[data["branch"]])
        db.add(teacher_without_health); await db.flush()
        db.add(ClassTeacher(class_id=data["classroom"].id, user_id=teacher_without_health.id))
        await db.commit()
    created = await client.post(f'/api/parent/child/{data["children"][0].id}/medicine-requests', headers=headers(data["user"]),
        json={"medicine_name": "Private clinical record", "dosage": "Test instruction", "time_to_give": "10:00"})
    assert created.status_code == 200, created.text
    identifier = created.json()["data"]["id"]
    assert (await client.get("/api/teacher/medicine-requests", headers=headers(teacher_without_health))).status_code == 403
    denied = await client.put("/api/parent-notices/" + identifier, headers=headers(observers[0]), json={"status": "APPROVED"})
    assert denied.status_code == 403, denied.text
    hidden = await client.get("/api/parent-notices", headers=headers(observers[1]))
    assert hidden.status_code == 200 and "Private clinical record" not in hidden.text
    for actor, count in ((observers[0], 1), (observers[1], 0)):
        result = await client.get("/api/dashboard/pending-actions", headers=headers(actor), params={"branch_id": str(data["branch"].id)})
        assert result.status_code == 200 and result.json()["data"]["medicine_requests"]["count"] == count, result.text


async def test_teacher_medication_reader_includes_direct_student_assignment_without_cross_institution_link(infirmary_client):
    from app.infrastructure.models.models import Student, StudentTeacherAssignment
    client, sessions, data = infirmary_client
    async with sessions() as db:
        direct = Student(first_name="Direct", last_name="Clinic", organization_id=data["org"].id, branch_id=data["branch"].id)
        db.add(direct); await db.flush()
        for child in (direct, data["stranger"]):
            db.add(StudentTeacherAssignment(student_id=child.id, teacher_id=data["teacher"].id, subject_name="Clinic teacher"))
            db.add(MedicationSchedule(student_id=child.id, medication_name="Direct clinic" if child == direct else "Private clinic",
                dosage="Test instruction", frequency="10:00", start_date=school_today()))
        await db.commit()
    response = await client.get("/api/teacher/medicine-requests", headers=headers(data["teacher"]))
    assert response.status_code == 200, response.text
    assert {row["medicine_name"] for row in response.json()["data"]} == {"Direct clinic"}, response.text
