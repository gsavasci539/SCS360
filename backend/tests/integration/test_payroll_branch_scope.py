from datetime import date
import asyncio
from sqlalchemy import func, select

from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.domain.entities.payroll import PayrollRecord, StaffTimesheet, AdditionalCourseHours
from app.infrastructure.models.models import Branch, Permission, Role, User, StudentTeacherAssignment


async def test_payroll_reader_and_writer_are_limited_to_their_actual_branch_staff(materials_client):
    client, sessions, data = materials_client
    async with sessions() as db:
        branch = Branch(organization_id=data["org"].id, name="Private other branch")
        db.add(branch); await db.flush()
        manager = User(email="payroll-branch@scope.invalid", password_hash="unused", first_name="Scoped", last_name="Manager",
            organization_id=data["org"].id, branches=[data["branch"]],
            roles=[Role(name="Scoped Payroll", slug="branch_manager", organization_id=data["org"].id,
                permissions=[Permission(code=code, name=code, module="payroll") for code in ("payroll.read", "payroll.write")])])
        other = User(email="other-staff@scope.invalid", password_hash="unused", first_name="Private", last_name="Salary",
            organization_id=data["org"].id, branches=[branch])
        direct = User(email="direct-staff@scope.invalid", password_hash="unused", first_name="Direct", last_name="Teacher", organization_id=data["org"].id)
        db.add_all([manager, other, direct]); await db.flush()
        db.add(StudentTeacherAssignment(student_id=data["children"][0].id, teacher_id=direct.id, subject_name="Math"))
        for staff in (data["teacher"], other, direct):
            db.add(PayrollRecord(staff_id=staff.id, period="MONTHLY", year=2026, month=11, base_salary=50000, net_salary=50000))
            db.add(StaffTimesheet(staff_id=staff.id, date=date(2026, 11, 3), work_hours=8))
            db.add(AdditionalCourseHours(staff_id=staff.id, period="MONTHLY", year=2026, month=11, total_hours=8))
        await db.commit()
    for path in ("records", "timesheets", "additional-hours"):
        response = await client.get("/api/payroll/" + path, headers=headers(manager))
        assert response.status_code == 200, response.text
        assert {row["staff_id"] for row in response.json()["data"]} == {str(data["teacher"].id), str(direct.id)}, response.text
        assert all(row["staff_name"] for row in response.json()["data"]), response.text
    choices = await client.get("/api/payroll/options", headers=headers(manager))
    assert choices.status_code == 200, choices.text
    identifiers = {row["id"] for row in choices.json()["data"]["staff"]}
    assert str(direct.id) in identifiers and str(other.id) not in identifiers and str(data["user"].id) not in identifiers
    summary = await client.get("/api/payroll/summary", headers=headers(manager), params={"year": 2026, "month": 11})
    assert summary.status_code == 200, summary.text
    assert summary.json()["data"]["total_payroll"] == 2 and summary.json()["data"]["net_salary_total"] == 100000
    for path, payload in (("records", {"period": "MONTHLY", "year": 2026, "month": 12, "base_salary": 50000}),
                          ("timesheets", {"timesheet_date": "2026-11-04", "work_hours": 8}),
                          ("additional-hours", {"period": "MONTHLY", "year": 2026, "month": 12, "total_hours": 8})):
        response = await client.post("/api/payroll/" + path, headers=headers(manager), json={"staff_id": str(other.id), **payload})
        assert response.status_code in {403, 404}, response.text
        own = await client.post("/api/payroll/" + path, headers=headers(manager), json={"staff_id": str(data["teacher"].id), **payload})
        assert own.status_code == 200, own.text
    records = (await client.get("/api/payroll/records", headers=headers(manager))).json()["data"]
    record_id = next(row["id"] for row in records if row["month"] == 12)
    approvals = await asyncio.gather(*[client.post(f"/api/payroll/records/{record_id}/approve", headers=headers(manager)) for _ in range(2)])
    assert all(response.status_code == 200 for response in approvals), [response.text for response in approvals]
    assert approvals[0].json()["data"] == approvals[1].json()["data"]
    assert approvals[0].json()["data"]["approved_by"] == str(manager.id)
    approved_rows = (await client.get("/api/payroll/records", headers=headers(manager))).json()["data"]
    assert next(row["approved_at"] for row in approved_rows if row["id"] == record_id) == approvals[0].json()["data"]["approved_at"]
    edited = await client.post("/api/payroll/records", headers=headers(manager), json={"staff_id": str(data["teacher"].id), "period": "MONTHLY", "year": 2026, "month": 12, "base_salary": 12345})
    assert edited.status_code == 409, edited.text
    concurrent = await asyncio.gather(*[client.post("/api/payroll/records", headers=headers(manager), json={"staff_id": str(data["teacher"].id), "period": "MONTHLY", "year": 2027, "month": 1, "base_salary": 12345}) for _ in range(2)])
    assert all(response.status_code == 200 for response in concurrent), [response.text for response in concurrent]
    async with sessions() as db:
        assert (await db.execute(select(func.count(PayrollRecord.id)).where(PayrollRecord.staff_id == data["teacher"].id, PayrollRecord.year == 2027))).scalar() == 1
    for path, payload in (("records", {"period": "MONTHLY", "year": 2027, "month": 3, "base_salary": "10000000000000000"}),
                          ("timesheets", {"timesheet_date": "2026-11-04", "work_hours": 25}),
                          ("timesheets", {"timesheet_date": "2026-11-04", "check_in_time": "2026-11-04T10:00:00Z", "check_out_time": "2026-11-04T09:00:00Z"}),
                          ("additional-hours", {"period": "MONTHLY", "year": 2027, "month": 3, "hourly_rate": "10000000000"})):
        response = await client.post("/api/payroll/" + path, headers=headers(manager), json={"staff_id": str(data["teacher"].id), **payload})
        assert response.status_code == 422, response.text
    quarterly = await client.post("/api/payroll/records", headers=headers(manager), json={"staff_id": str(data["teacher"].id), "period": "QUARTERLY", "year": 2026, "month": 11, "base_salary": 150000})
    assert quarterly.status_code == 200, quarterly.text
    async with sessions() as db:
        db.add_all([StaffTimesheet(staff_id=data["teacher"].id, date=day, work_hours=8) for day in (date(2026, 12, 3), date(2027, 1, 3))]); await db.commit()
    quarter = await client.get("/api/payroll/summary", headers=headers(manager), params={"staff_id": str(data["teacher"].id), "period": "QUARTERLY", "year": 2026, "month": 11})
    assert quarter.status_code == 200 and quarter.json()["data"]["net_salary_total"] == 150000, quarter.text
    assert quarter.json()["data"]["total_timesheets"] == 4  # November 3, November 4, December 3, January 3
    clocking = {"staff_id": str(data["teacher"].id), "timesheet_date": "2026-11-05", "work_hours": 8,
        "check_in_time": "2026-11-05T08:00:00+03:00", "check_out_time": "2026-11-05T16:00:00+03:00"}
    response = await client.post("/api/payroll/timesheets", headers=headers(manager), json=clocking)
    assert response.status_code == 200, response.text
    clocks = (await client.get("/api/payroll/timesheets", headers=headers(manager), params={"staff_id": str(data["teacher"].id), "start_date": "2026-11-05", "end_date": "2026-11-05"})).json()["data"]
    assert clocks[0]["check_in_time"] == "2026-11-05T05:00:00+00:00" and clocks[0]["check_out_time"] == "2026-11-05T13:00:00+00:00"
    ambiguous = await client.post("/api/payroll/timesheets", headers=headers(manager), json={**clocking, "check_in_time": "2026-11-05T08:00:00"})
    assert ambiguous.status_code == 422, ambiguous.text
