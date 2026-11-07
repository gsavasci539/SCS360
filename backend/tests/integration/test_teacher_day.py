from datetime import UTC, date, datetime, time
from uuid import uuid4

from sqlalchemy import select

from test_material_files import materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.application.services import teacher_day_service
from app.core.security import create_access_token
from app.infrastructure.models.models import (AttendanceRecord, AttendanceStatus, ClassroomAssignment, DailyDevelopmentReport,
    OperationalRecord, Student, Timetable, TimetableSlot, User, UserRole)


def auth(user):
    return {"Authorization": "Bearer " + create_access_token(user.id)}


async def test_partial_class_work_stays_pending_until_each_active_student_has_records(materials_client, monkeypatch):
    from app.domain.entities.health import MedicationSchedule
    client, sessions, data = materials_client
    today = date(2026, 11, 3)
    monkeypatch.setattr(teacher_day_service, "school_today", lambda: today)
    async with sessions() as db:
        from app.infrastructure.models.models import Permission, Role, RolePermission
        feature = Permission(code="teacher.view_medicine_requests", name="Read class medication requests", module="teacher")
        db.add(feature); await db.flush()
        teacher_role = (await db.execute(select(Role).where(Role.slug == "teacher"))).scalar_one()
        db.add(RolePermission(role_id=teacher_role.id, permission_id=feature.id))
        db.add(Student(organization_id=data["org"].id, branch_id=data["branch"].id, class_id=data["classroom"].id,
            first_name="Archived", last_name="Student", deleted_at=datetime.now(UTC)))
        for student, name in ((data["children"][0], "Test talimatı"), (data["stranger"], "Yabancı kurum talimatı")):
            db.add(MedicationSchedule(student_id=student.id, medication_name=name, dosage="Test", frequency="Test", start_date=today))
        for student in data["children"][:1]:
            db.add(AttendanceRecord(organization_id=data["org"].id, branch_id=data["branch"].id, class_id=student.class_id,
                student_id=student.id, attendance_date=today, status=AttendanceStatus.PRESENT, recorded_by=data["teacher"].id))
            db.add(DailyDevelopmentReport(student_id=student.id, class_id=student.class_id, date=today, recorded_by=data["teacher"].id))
        await db.commit()
    classes = await client.get("/api/teacher/my-classes", headers=auth(data["teacher"]))
    assert classes.status_code == 200 and classes.json()["data"][0]["student_count"] == 2
    medicines = await client.get("/api/teacher/medicine-requests", headers=auth(data["teacher"]))
    assert medicines.status_code == 200, medicines.text
    assert len(medicines.json()["data"]) == 1 and medicines.json()["data"][0]["medicine_name"] == "Test talimatı"
    tasks = (await client.get("/api/teacher/pending-tasks", headers=auth(data["teacher"]))).json()["data"]
    assert tasks["date"] == str(today)
    assert {row["task_type"] for row in tasks["tasks"]} == {"attendance", "daily_report"}
    assert all(row["remaining_count"] == 1 and row["completed_count"] == 1 for row in tasks["tasks"])
    async with sessions() as db:
        student = data["children"][1]
        db.add(AttendanceRecord(organization_id=data["org"].id, branch_id=data["branch"].id, class_id=student.class_id,
            student_id=student.id, attendance_date=today, status=AttendanceStatus.ABSENT, recorded_by=data["teacher"].id))
        db.add(DailyDevelopmentReport(student_id=student.id, class_id=student.class_id, date=today, recorded_by=data["teacher"].id))
        await db.commit()
    assert (await client.get("/api/teacher/pending-tasks", headers=auth(data["teacher"]))).json()["data"]["tasks"] == []


async def test_teacher_sees_saved_class_schedule_on_the_school_day(materials_client, monkeypatch):
    client, sessions, data = materials_client
    monkeypatch.setattr(teacher_day_service, "school_today", lambda: date(2026, 11, 3))
    async with sessions() as db:
        db.add(OperationalRecord(organization_id=data["org"].id, branch_id=data["branch"].id, class_id=data["classroom"].id,
            kind="CLASS_SCHEDULE", created_by=data["teacher"].id, data={"schedule": [
                {"day": "SALI", "periods": [{"subject": "Türkçe", "time": "09:00 - 09:40", "teacher_name": "Teacher Test"}]},
                {"day": "WEDNESDAY", "periods": [{"subject": "Başka gün", "time": "10:00 - 10:40"}]}]}))
        await db.commit()
    response = await client.get("/api/teacher/today-schedule", headers=auth(data["teacher"]))
    assert response.status_code == 200, response.text
    rows = response.json()["data"]
    assert len(rows) == 1 and rows[0]["subject_id"] == "Türkçe" and rows[0]["start_time"] == "09:00"
    assert rows[0]["source"] == "CLASS_SCHEDULE"


async def test_lesson_assigned_teacher_has_matching_class_student_parent_and_homework_access(materials_client, monkeypatch):
    client, sessions, data = materials_client
    monkeypatch.setattr(teacher_day_service, "school_today", lambda: date(2026, 11, 3))
    async with sessions() as db:
        teacher_role_id = (await db.execute(select(UserRole.role_id).where(UserRole.user_id == data["teacher"].id))).scalar_one()
        subject_teacher = User(organization_id=data["org"].id, first_name="Subject", last_name="Teacher", password_hash="unused", email="subject@teacher.example.com")
        db.add(subject_teacher)
        await db.flush()
        db.add(UserRole(user_id=subject_teacher.id, role_id=teacher_role_id))
        subject_id = uuid4()
        assignment = ClassroomAssignment(class_id=data["classroom"].id, teacher_id=subject_teacher.id, subject_id=subject_id, room_number="Derslik 2")
        slot = TimetableSlot(day="TUESDAY", start_time=time(10), end_time=time(10, 40))
        db.add_all([assignment, slot])
        await db.flush()
        db.add(Timetable(class_id=data["classroom"].id, slot_id=slot.id, classroom_assignment_id=assignment.id, academic_year="2026-2027"))
        await db.commit()
    headers = auth(subject_teacher)
    classes = await client.get("/api/teacher/my-classes", headers=headers)
    assert classes.status_code == 200 and classes.json()["data"][0]["id"] == str(data["classroom"].id)
    students = await client.get(f'/api/teacher/class/{data["classroom"].id}/students', headers=headers)
    assert students.status_code == 200 and len(students.json()["data"]) == 2
    assert (await client.get(f'/api/students/{data["stranger"].id}', headers=headers)).status_code == 404
    schedule = await client.get("/api/teacher/today-schedule", headers=headers)
    assert schedule.status_code == 200 and schedule.json()["data"][0]["subject_id"] == str(subject_id)
    assert schedule.json()["data"][0]["subject"] == "Ders"
    parent_teachers = await client.get(f'/api/parent/child/{data["children"][0].id}/teachers', headers=auth(data["user"]))
    assert parent_teachers.status_code == 200 and str(subject_teacher.id) in {row["id"] for row in parent_teachers.json()["data"]}
    homework = await client.post("/api/homework", headers=headers, json={"title": "Ders öğretmeni ödevi", "class_id": str(data["classroom"].id)})
    assert homework.status_code == 200, homework.text
