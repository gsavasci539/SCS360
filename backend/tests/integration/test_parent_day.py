from datetime import UTC, date, datetime, time, timedelta

from test_material_files import materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.core.security import create_access_token
from app.core.config import get_settings
from app.application.services import parent_day_service
from app.infrastructure.models.models import AttendanceRecord, AttendanceStatus, DailyDevelopmentReport, OperationalRecord
from app.infrastructure.models.models import UserBranch
from app.domain.entities.health import MedicationLog, MedicationSchedule, InfirmaryVisit
from app.domain.entities.bus import BusRoute, BusAttendance
from app.domain.entities.pickup import PickupLog


def auth(user):
    return {"Authorization": "Bearer " + create_access_token(user.id)}


async def test_parent_timeline_reads_real_child_events_and_school_day_boundaries(materials_client, monkeypatch):
    client, sessions, data = materials_client
    monkeypatch.setattr(get_settings(), "BUSINESS_TIMEZONE", "Europe/Istanbul")
    day = date(2026, 11, 3)
    student = data["children"][0]
    async with sessions() as db:
        db.add(AttendanceRecord(organization_id=data["org"].id, branch_id=data["branch"].id, class_id=student.class_id,
            student_id=student.id, attendance_date=day, status=AttendanceStatus.PRESENT, check_in_time=time(8, 30), recorded_by=data["teacher"].id))
        db.add(DailyDevelopmentReport(student_id=student.id, class_id=student.class_id, date=day, meal_status="ALL",
            activities=["Kitap okuma"], teacher_notes="Kalıcı öğretmen notu", recorded_by=data["teacher"].id,
            updated_at=datetime(2026, 11, 3, 10, tzinfo=UTC)))
        prescription = MedicationSchedule(student_id=student.id, medication_name="Test talimatı", dosage="Test dozu",
            frequency="Günde bir", start_date=day)
        other_prescription = MedicationSchedule(student_id=data["children"][1].id, medication_name="Başka çocuğun kaydı",
            dosage="Gizli", frequency="Günde bir", start_date=day)
        route = BusRoute(branch_id=data["branch"].id, route_name="Test güzergâhı")
        db.add_all([prescription, other_prescription, route])
        await db.flush()
        for instant in (datetime(2026, 11, 2, 20, 59, tzinfo=UTC), datetime(2026, 11, 2, 22, 30, tzinfo=UTC),
            datetime(2026, 11, 3, 21, tzinfo=UTC)):
            db.add(MedicationLog(student_id=student.id, schedule_id=prescription.id, scheduled_time=time(1, 30),
                given_time=instant, status="GIVEN", given_by=data["teacher"].id))
        # Corrupt auxiliary relationship must not reveal a sibling's prescription.
        db.add(MedicationLog(student_id=student.id, schedule_id=other_prescription.id, scheduled_time=time(1),
            given_time=datetime(2026, 11, 3, 9, tzinfo=UTC), status="GIVEN"))
        db.add(InfirmaryVisit(student_id=student.id, branch_id=data["branch"].id, visit_date=day, visit_time=time(11),
            complaint="Test revir kaydı", examined_by=data["teacher"].id))
        db.add(BusAttendance(route_id=route.id, student_id=student.id, date=day, pickup_time=time(7, 45), dropoff_time=time(16, 30)))
        db.add(PickupLog(student_id=student.id, pickup_person_name="Yetkili veli", verified_by=data["teacher"].id,
            pickup_time=datetime(2026, 11, 3, 14, tzinfo=UTC)))
        await db.commit()
    path = f"/api/parent/child/{student.id}/timeline"
    response = await client.get(path, headers=auth(data["user"]), params={"date": str(day)})
    assert response.status_code == 200, response.text
    events = response.json()["data"]["events"]
    assert [row["type"] for row in events] == ["MEDICATION", "BUS_PICKUP", "ATTENDANCE", "INFIRMARY", "DAILY_REPORT", "BUS_DROPOFF", "PICKUP"]
    assert events[0]["time"] == "01:30" and events[0]["timestamp"].endswith("+03:00")
    assert "Başka çocuğun kaydı" not in response.text
    assert all(row["detail_url"].startswith("/parent/") for row in events)
    response = await client.get(f'/api/parent/child/{data["children"][1].id}/timeline', headers=auth(data["user"]), params={"date": str(day)})
    assert response.json()["data"]["events"] == []
    assert (await client.get(f'/api/parent/child/{data["stranger"].id}/timeline', headers=auth(data["user"]))).status_code == 403


async def test_today_status_uses_school_date_and_saved_class_schedule(materials_client, monkeypatch):
    client, sessions, data = materials_client
    day = date(2026, 11, 3)
    monkeypatch.setattr(parent_day_service, "school_today", lambda: day)
    student = data["children"][0]
    async with sessions() as db:
        db.add(AttendanceRecord(organization_id=data["org"].id, branch_id=data["branch"].id, class_id=student.class_id,
            student_id=student.id, attendance_date=day, status=AttendanceStatus.PRESENT, check_in_time=time(8), recorded_by=data["teacher"].id))
        db.add(OperationalRecord(organization_id=data["org"].id, branch_id=data["branch"].id, class_id=student.class_id,
            created_by=data["teacher"].id, kind="CLASS_SCHEDULE", data={"schedule": [
                {"day": "SALI", "periods": [{"subject": "Türkçe", "time": "09:00 - 09:40", "teacher_name": "Öğretmen"}]},
                {"day": "MONDAY", "periods": [{"subject": "Başka gün", "time": "10:00 - 10:40"}]}]}))
        await db.commit()
    response = await client.get(f'/api/parent/child/{student.id}/today-status', headers=auth(data["user"]))
    assert response.status_code == 200, response.text
    result = response.json()["data"]
    assert result["date"] == str(day) and result["attendance"]["status"] == "PRESENT"
    assert result["today_schedule"] == [{"subject": "Türkçe", "start_time": "09:00", "end_time": "09:40", "teacher": "Öğretmen"}]
    assert (await client.get(f'/api/parent/child/{data["stranger"].id}/today-status', headers=auth(data["user"]))).status_code == 403


async def test_date_only_records_do_not_invent_an_event_time(materials_client):
    client, sessions, data = materials_client
    day = date(2026, 11, 3)
    student = data["children"][0]
    async with sessions() as db:
        db.add(AttendanceRecord(organization_id=data["org"].id, branch_id=data["branch"].id, class_id=student.class_id,
            student_id=student.id, attendance_date=day, status=AttendanceStatus.ABSENT, recorded_by=data["teacher"].id))
        await db.commit()
    response = await client.get(f'/api/parent/child/{student.id}/timeline', headers=auth(data["user"]), params={"date": str(day)})
    row = response.json()["data"]["events"][0]
    assert row["time"] is None and row["timestamp"] is None and row["status"] == "ABSENT"


async def test_teacher_with_assigned_branch_can_read_daily_reports_without_server_error(materials_client):
    client, sessions, data = materials_client
    async with sessions() as db:
        db.add(UserBranch(user_id=data["teacher"].id, branch_id=data["branch"].id))
        db.add(DailyDevelopmentReport(student_id=data["children"][0].id, class_id=data["classroom"].id,
            date=date(2026, 11, 3), teacher_notes="Şube kapsamındaki rapor", recorded_by=data["teacher"].id))
        await db.commit()
    response = await client.get("/api/daily-reports", headers=auth(data["teacher"]))
    assert response.status_code == 200, response.text
    assert "Şube kapsamındaki rapor" in response.text
