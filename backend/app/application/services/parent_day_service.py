"""A child's day is assembled from persisted, relationship-scoped records."""
from sqlalchemy import select

from app.application.services.parent_data_service import child, enum_value, schedule
from app.core.dates import school_datetime, school_day_bounds, school_today
from app.infrastructure.models.models import AttendanceRecord, DailyDevelopmentReport


def event(kind, row, title, status, detail_url, *, clock=None, instant=None, details=None):
    local = school_datetime(instant) if instant else None
    return {"id": f"{kind}:{row.id}", "type": kind, "title": title, "status": enum_value(status),
        "time": clock.strftime("%H:%M") if clock else local.strftime("%H:%M") if local else None,
        "timestamp": local.isoformat() if local else None, "details": details or {}, "detail_url": detail_url}


async def day_records(db, user, student_id, target_date):
    _, student = await child(db, user, student_id)
    attendance = (await db.execute(select(AttendanceRecord).where(AttendanceRecord.student_id == student.id,
        AttendanceRecord.organization_id == student.organization_id, AttendanceRecord.attendance_date == target_date,
        AttendanceRecord.deleted_at.is_(None)))).scalar_one_or_none()
    report = (await db.execute(select(DailyDevelopmentReport).where(DailyDevelopmentReport.student_id == student.id,
        DailyDevelopmentReport.date == target_date))).scalar_one_or_none()
    return student, attendance, report


def weekday_matches(value, day):
    names = ("MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY")
    turkish = ("PAZARTESİ", "SALI", "ÇARŞAMBA", "PERŞEMBE", "CUMA", "CUMARTESİ", "PAZAR")
    normalized = str(value).strip().upper()
    index = day.weekday()
    return normalized in {names[index], turkish[index], turkish[index].translate(str.maketrans("İŞÇ", "ISC")), str(index + 1)}


async def today_status(db, user, student_id):
    target_date = school_today()
    student, attendance, report = await day_records(db, user, student_id, target_date)
    days = await schedule(db, user, student_id)
    lessons = [lesson for day in days if weekday_matches(day.get("day_of_week"), target_date) for lesson in day.get("lessons", [])]
    return {"student_id": str(student.id), "student_name": f"{student.first_name} {student.last_name}",
        "date": target_date.isoformat(), "attendance": {"status": enum_value(attendance.status),
            "check_in_time": attendance.check_in_time.strftime("%H:%M") if attendance.check_in_time else None} if attendance else None,
        "daily_report": {"meal_status": report.meal_status, "sleep_status": report.sleep_status, "mood": report.mood,
            "activities": report.activities, "teacher_notes": report.teacher_notes} if report else None,
        "today_schedule": lessons}


async def timeline(db, user, student_id, target_date=None):
    from app.domain.entities.health import MedicationLog, MedicationSchedule, InfirmaryVisit
    from app.domain.entities.bus import BusAttendance
    from app.domain.entities.pickup import PickupLog
    target_date = target_date or school_today()
    student, attendance, report = await day_records(db, user, student_id, target_date)
    events = []
    if attendance:
        events.append(event("ATTENDANCE", attendance, "Yoklama kaydı", attendance.status, "/parent/attendance",
            clock=attendance.check_in_time, details={"notes": attendance.notes}))
    if report:
        recorded = school_datetime(report.updated_at) if report.updated_at else None
        events.append(event("DAILY_REPORT", report, "Öğretmen günlük raporu", "RECORDED", "/parent/reports",
            instant=recorded if recorded and recorded.date() == target_date else None,
            details={"meal_status": report.meal_status, "sleep_status": report.sleep_status, "mood": report.mood,
                "activities": report.activities, "teacher_notes": report.teacher_notes}))
    start, end = school_day_bounds(target_date)
    medication = (await db.execute(select(MedicationLog, MedicationSchedule).join(MedicationSchedule,
        MedicationSchedule.id == MedicationLog.schedule_id).where(MedicationLog.student_id == student.id,
            MedicationSchedule.student_id == student.id, MedicationLog.given_time >= start, MedicationLog.given_time < end))).all()
    for log, prescription in medication:
        events.append(event("MEDICATION", log, "İlaç takip kaydı", log.status, "/parent/health", instant=log.given_time,
            details={"medicine_name": prescription.medication_name, "dosage": prescription.dosage, "notes": log.notes}))
    visits = (await db.execute(select(InfirmaryVisit).where(InfirmaryVisit.student_id == student.id,
        InfirmaryVisit.visit_date == target_date))).scalars()
    for visit in visits:
        events.append(event("INFIRMARY", visit, "Revir ziyareti", visit.severity, "/parent/health", clock=visit.visit_time,
            details={"complaint": visit.complaint, "treatment_given": visit.treatment_given}))
    bus_records = (await db.execute(select(BusAttendance).where(BusAttendance.student_id == student.id,
        BusAttendance.date == target_date))).scalars()
    for record in bus_records:
        for kind, clock, title in (("BUS_PICKUP", record.pickup_time, "Servise biniş"),
            ("BUS_DROPOFF", record.dropoff_time, "Servisten iniş")):
            if clock is not None:
                events.append(event(kind, record, title, record.status, "/parent/children", clock=clock))
    pickups = (await db.execute(select(PickupLog).where(PickupLog.student_id == student.id,
        PickupLog.pickup_time >= start, PickupLog.pickup_time < end))).scalars()
    for pickup in pickups:
        events.append(event("PICKUP", pickup, "Okuldan teslim", "RECORDED", "/parent/children", instant=pickup.pickup_time,
            details={"pickup_person_name": pickup.pickup_person_name}))
    events.sort(key=lambda row: (row["time"] is None, row["time"] or "", row["id"]))
    return {"student_id": str(student.id), "student_name": f"{student.first_name} {student.last_name}",
        "date": target_date.isoformat(), "events": events}
