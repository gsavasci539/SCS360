from datetime import date, timedelta

from test_material_files import materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.infrastructure.models.models import (AttendanceRecord, AttendanceStatus, Branch, ClassRoom,
    DailyDevelopmentReport, Debt, DebtStatus, DebtType, Student, User)
from app.core.security import create_access_token


def auth(user):
    return {"Authorization": "Bearer " + create_access_token(user.id)}


async def test_excuse_is_persisted_reviewed_and_limited_to_the_child_and_branch(materials_client):
    client, sessions, data = materials_client
    async with sessions() as db:
        admin = User(organization_id=data["org"].id, email="admin@test.invalid", first_name="Admin",
            last_name="Acceptance", password_hash="unused", is_super_admin=True)
        db.add(admin)
        await db.commit()
    child = data["children"][0]
    path = f"/api/parent/child/{child.id}/excuse-request"
    body = {"start_date": "2026-11-03", "end_date": "2026-11-04", "reason_type": "ILLNESS", "description": "İstirahat"}
    response = await client.post(path, headers=auth(data["user"]), json=body)
    assert response.status_code == 200, response.text
    request_id = response.json()["data"]["id"]
    listed = await client.get(path + "s", headers=auth(data["user"]))
    assert listed.json()["data"][0]["id"] == request_id
    sibling_path = f'/api/parent/child/{data["children"][1].id}/excuse-requests'
    assert (await client.get(sibling_path, headers=auth(data["user"]))).json()["data"] == []
    other_path = f'/api/parent/child/{data["stranger"].id}/excuse-request'
    assert (await client.post(other_path, headers=auth(data["user"]), json=body)).status_code == 403
    assert (await client.post(path, headers=auth(data["user"]), json={**body, "end_date": "2026-11-02"})).status_code == 422
    pending_path = f'/api/dashboard/pending-actions?branch_id={data["branch"].id}'
    pending = await client.get(pending_path, headers=auth(admin))
    assert pending.status_code == 200, pending.text
    assert pending.json()["data"]["excuse_requests"]["count"] == 1
    assert pending.json()["data"]["excuse_requests"]["items"][0]["id"] == request_id
    review_path = f"/api/dashboard/excuse-requests/{request_id}"
    assert (await client.put(review_path, headers=auth(data["user"]), json={"status": "APPROVED"})).status_code == 403
    assert (await client.put(review_path, headers=auth(admin), json={"status": "APPROVED", "comment": "Geçmiş olsun"})).status_code == 200
    assert (await client.put(review_path, headers=auth(admin), json={"status": "REJECTED"})).status_code == 409
    listed = (await client.get(path + "s", headers=auth(data["user"]))).json()["data"][0]
    assert listed["status"] == "APPROVED" and listed["review_comment"] == "Geçmiş olsun"
    assert (await client.get(pending_path, headers=auth(admin))).json()["data"]["excuse_requests"]["count"] == 0


async def test_daily_stats_and_pending_counts_use_real_records_in_requested_branch(materials_client):
    client, sessions, data = materials_client
    today = date.today()
    async with sessions() as db:
        admin = User(organization_id=data["org"].id, email="stats@test.invalid", first_name="Admin",
            last_name="Acceptance", password_hash="unused", is_super_admin=True)
        other_branch = Branch(organization_id=data["org"].id, name="Second branch")
        db.add_all([admin, other_branch])
        await db.flush()
        classroom = ClassRoom(organization_id=data["org"].id, branch_id=other_branch.id, name="Second")
        db.add(classroom)
        await db.flush()
        other = Student(organization_id=data["org"].id, branch_id=other_branch.id, class_id=classroom.id,
            first_name="Other", last_name="Student")
        db.add(other)
        await db.flush()
        for student, status, meal in ((data["children"][0], AttendanceStatus.PRESENT, "ALL"),
            (data["children"][1], AttendanceStatus.ABSENT, "HALF"), (other, AttendanceStatus.PRESENT, "NONE")):
            db.add(AttendanceRecord(organization_id=student.organization_id, branch_id=student.branch_id,
                class_id=student.class_id, student_id=student.id, attendance_date=today, status=status, recorded_by=admin.id))
            db.add(DailyDevelopmentReport(student_id=student.id, class_id=student.class_id, date=today,
                meal_status=meal, recorded_by=admin.id))
        for index in range(13):
            student = data["children"][0] if index < 12 else other
            db.add(Debt(organization_id=student.organization_id, branch_id=student.branch_id, student_id=student.id,
                debt_type=DebtType.EDUCATION, description="Acceptance", amount=100,
                paid_amount=0, status=DebtStatus.OVERDUE, due_date=today - timedelta(days=2)))
        await db.commit()
    response = await client.get(f'/api/dashboard/daily-stats?branch_id={data["branch"].id}', headers=auth(admin))
    assert response.status_code == 200, response.text
    result = response.json()["data"]
    assert result["attendance"]["present"] == 1 and result["attendance"]["absent"] == 1
    assert result["attendance"]["total"] == 2 and result["attendance"]["rate"] == 50
    assert result["meals"] == {"full": 1, "half": 1, "none": 0, "total": 2}
    response = await client.get(f'/api/dashboard/pending-actions?branch_id={data["branch"].id}', headers=auth(admin))
    assert response.status_code == 200, response.text
    debts = response.json()["data"]["overdue_debts"]
    assert debts["count"] == 12 and len(debts["items"]) == 10
