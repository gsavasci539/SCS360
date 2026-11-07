"""Teacher portal reads backed by actual class, schedule and student records."""
from uuid import UUID
from sqlalchemy import func, select

from app.core.dates import school_today
from app.core.exceptions import ValidationException
from app.core.teaching import teacher_classes_query
from app.application.services.parent_day_service import weekday_matches
from app.infrastructure.models.models import (AttendanceRecord, ClassRoom, ClassroomAssignment,
    DailyDevelopmentReport, OperationalRecord, Student, Timetable, TimetableSlot)


async def classes(db, user):
    rows = (await db.execute(teacher_classes_query(user.id).order_by(ClassRoom.name, ClassRoom.id))).scalars().all()
    ids = [row.id for row in rows if row is not None]
    counts = dict((await db.execute(select(Student.class_id, func.count(Student.id)).where(Student.class_id.in_(ids),
        Student.status == "ACTIVE", Student.deleted_at.is_(None)).group_by(Student.class_id))).all()) if ids else {}
    return [{"id": str(row.id), "name": row.name, "student_count": counts.get(row.id, 0)} for row in rows if row is not None]


async def pending_tasks(db, user):
    today = school_today()
    classrooms = await classes(db, user)
    ids = [UUID(row["id"]) for row in classrooms]
    if not ids:
        return {"date": today.isoformat(), "tasks": []}
    students = (await db.execute(select(Student.id, Student.class_id).where(Student.class_id.in_(ids),
        Student.deleted_at.is_(None), Student.status == "ACTIVE"))).all()
    active_ids = [row.id for row in students]
    attendance = dict((await db.execute(select(AttendanceRecord.class_id, func.count(func.distinct(AttendanceRecord.student_id)))
        .where(AttendanceRecord.class_id.in_(ids), AttendanceRecord.student_id.in_(active_ids),
            AttendanceRecord.attendance_date == today, AttendanceRecord.deleted_at.is_(None))
        .group_by(AttendanceRecord.class_id))).all()) if active_ids else {}
    reports = dict((await db.execute(select(DailyDevelopmentReport.class_id, func.count(func.distinct(DailyDevelopmentReport.student_id)))
        .where(DailyDevelopmentReport.class_id.in_(ids), DailyDevelopmentReport.student_id.in_(active_ids), DailyDevelopmentReport.date == today)
        .group_by(DailyDevelopmentReport.class_id))).all()) if active_ids else {}
    tasks = []
    for classroom in classrooms:
        identifier = UUID(classroom["id"])
        total = classroom["student_count"]
        for kind, counts, priority in (("attendance", attendance, "high"), ("daily_report", reports, "medium")):
            remaining = max(0, total - counts.get(identifier, 0))
            if remaining:
                tasks.append({"task_id": f"{kind}_{classroom['id']}", "task_type": kind, "class_id": classroom["id"],
                    "class_name": classroom["name"], "due_date": today.isoformat(), "priority": priority,
                    "student_count": total, "completed_count": total - remaining, "remaining_count": remaining})
    return {"date": today.isoformat(), "tasks": tasks}


async def today_schedule(db, user):
    today = school_today()
    classrooms = {row.id: row for row in (await db.execute(teacher_classes_query(user.id))).scalars() if row is not None}
    if not classrooms:
        return []
    saved = (await db.execute(select(OperationalRecord).where(OperationalRecord.kind == "CLASS_SCHEDULE",
        OperationalRecord.class_id.in_(classrooms)))).scalars()
    schedules, overridden = [], set()
    for record in saved:
        overridden.add(record.class_id)
        if not isinstance(record.data, dict) or not isinstance(record.data.get("schedule", []), list):
            raise ValidationException("Kayıtlı sınıf programının gün listesi geçersiz; sınıf programını yeniden kaydedin")
        for day_index, day in enumerate(record.data.get("schedule", [])):
            if not isinstance(day, dict) or not weekday_matches(day.get("day"), today):
                continue
            if not isinstance(day.get("periods", []), list):
                raise ValidationException("Kayıtlı sınıf programının ders listesi geçersiz; sınıf programını yeniden kaydedin")
            for index, period in enumerate(day.get("periods", [])):
                if not isinstance(period, dict):
                    continue
                clock = str(period.get("time") or "").split(" - ", 1)
                schedules.append({"timetable_id": f"{record.id}:{day_index}:{index}", "day": day.get("day"),
                    "start_time": clock[0], "end_time": clock[-1] if len(clock) > 1 else "",
                    "class_id": str(record.class_id), "class_name": classrooms[record.class_id].name,
                    "room_number": period.get("room_number"), "subject_id": period.get("subject") or "Ders",
                    "subject": period.get("subject") or "Ders",
                    "teacher_name": period.get("teacher_name"), "source": "CLASS_SCHEDULE"})
    rows = (await db.execute(select(Timetable, TimetableSlot, ClassroomAssignment)
        .select_from(Timetable)
        .join(TimetableSlot, TimetableSlot.id == Timetable.slot_id)
        .outerjoin(ClassroomAssignment, ClassroomAssignment.id == Timetable.classroom_assignment_id)
        .where(Timetable.class_id.in_(classrooms), Timetable.is_active.is_(True),
            Timetable.class_id.not_in(overridden) if overridden else True)
        .order_by(TimetableSlot.start_time, Timetable.id))).all()
    for timetable, slot, assignment in rows:
        if not weekday_matches(slot.day, today):
            continue
        if assignment and assignment.class_id != timetable.class_id:
            continue
        schedules.append({"timetable_id": str(timetable.id), "day": slot.day, "start_time": slot.start_time.strftime("%H:%M"),
            "end_time": slot.end_time.strftime("%H:%M"), "class_id": str(timetable.class_id),
            "class_name": classrooms[timetable.class_id].name, "room_number": assignment.room_number if assignment else None,
            "subject_id": str(assignment.subject_id) if assignment and assignment.subject_id else None,
            "subject": "Teneffüs" if slot.is_break else "Ders",
            "source": "TIMETABLE"})
    return sorted(schedules, key=lambda row: (row["start_time"], row["class_name"], row["timetable_id"]))
