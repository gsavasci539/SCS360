from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from test_material_files import headers, materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401

from app.core.dates import school_today
from app.infrastructure.models.models import (
    AttendanceRecord,
    AttendanceStatus,
    Branch,
    ClassRoom,
    Permission,
    Role,
    Student,
    StudentStatus,
    StudentTeacherAssignment,
    UserBranch,
)


async def test_legacy_teacher_summary_uses_only_assigned_students_and_saved_attendance(materials_client):  # noqa: F811
    client, sessions, data = materials_client
    teacher, branch, org = data["teacher"], data["branch"], data["org"]
    path = "/api/teacher/dashboard-summary"
    teacher_headers = headers(teacher)
    assert (await client.get(path, headers=teacher_headers)).status_code == 403

    async with sessions() as db:
        role = (await db.execute(select(Role).where(Role.slug == "teacher")
            .options(selectinload(Role.permissions)))).scalar_one()
        role.slug = "teacher2"
        role.permissions.append(Permission(code="dashboard.read", name="Dashboard", module="dashboard"))
        extra_branch = Branch(name="Restricted", organization_id=org.id)
        db.add_all([extra_branch, UserBranch(user_id=teacher.id, branch_id=branch.id)])
        await db.flush()
        restricted = ClassRoom(name="Restricted", organization_id=org.id, branch_id=extra_branch.id, teacher_id=teacher.id)
        foreign = ClassRoom(name="Foreign", organization_id=data["other_branch"].organization_id,
            branch_id=data["other_branch"].id, teacher_id=teacher.id)
        db.add_all([restricted, foreign])
        await db.flush()

        def student(name, classroom):
            return Student(first_name=name, last_name="Test", organization_id=classroom.organization_id,
                branch_id=classroom.branch_id, class_id=classroom.id)

        direct = student("Direct", data["other_class"])
        unassigned = student("Unassigned", data["other_class"])
        absent = student("Absent", data["classroom"])
        late = student("Late", data["classroom"])
        excused = student("Excused", data["classroom"])
        without_record = student("Unrecorded", data["classroom"])
        inactive = student("Inactive", data["classroom"])
        inactive.status = StudentStatus.PASSIVE
        restricted_student = student("Restricted", restricted)
        foreign_student = student("Foreign", foreign)
        db.add_all([direct, unassigned, absent, late, excused, without_record, inactive,
            restricted_student, foreign_student])
        await db.flush()
        db.add(StudentTeacherAssignment(teacher_id=teacher.id, student_id=direct.id, subject_name="Matematik"))
        today = school_today()

        def attendance(student, status, day=today):
            return AttendanceRecord(student_id=student.id, class_id=student.class_id, branch_id=student.branch_id,
                organization_id=student.organization_id, recorded_by=teacher.id, attendance_date=day, status=status)

        removed = attendance(without_record, AttendanceStatus.ABSENT)
        removed.deleted_at = datetime.now(UTC)
        db.add_all([attendance(data["children"][0], AttendanceStatus.PRESENT),
            attendance(data["children"][1], AttendanceStatus.ABSENT, today - timedelta(days=1)),
            attendance(direct, AttendanceStatus.HALF_DAY), attendance(absent, AttendanceStatus.ABSENT),
            attendance(late, AttendanceStatus.LATE), attendance(excused, AttendanceStatus.EXCUSED), removed,
            *[attendance(student, AttendanceStatus.ABSENT) for student in
                (unassigned, inactive, restricted_student, foreign_student)]])
        await db.commit()
        role_id = role.id

    response = await client.get(path, headers=teacher_headers)
    assert response.status_code == 200, response.text
    totals = {"date": today.isoformat(), "total_students": 8, "active_students": 7, "total_classes": 1}
    assert response.json()["data"] == {**totals, "attendance": None}

    async with sessions() as db:
        role = await db.get(Role, role_id, options=[selectinload(Role.permissions)])
        role.permissions.append(Permission(code="attendance.read", name="Attendance", module="attendance"))
        await db.commit()

    response = await client.get(path, headers=teacher_headers)
    assert response.status_code == 200, response.text
    assert response.json()["data"] == {**totals, "attendance": {
        "recorded_students": 5, "absent_students": 1, "participation_rate": 62.5,
    }}
