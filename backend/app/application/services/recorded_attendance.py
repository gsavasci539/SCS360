"""Measured attendance for visible pupils; no prediction model is claimed."""
from collections import Counter, defaultdict
from datetime import timedelta

from sqlalchemy import String, cast, select

from app.core.dates import school_today
from app.core.exceptions import ForbiddenException
from app.infrastructure.models.models import AttendanceRecord, Student

STATES = ("PRESENT", "LATE", "HALF_DAY", "ABSENT", "EXCUSED")
MEASURE = "100 * (PRESENT + LATE + 0.5 * HALF_DAY) / (PRESENT + LATE + HALF_DAY + ABSENT)"
DAY_NAMES = ("Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar")
MONITORING_THRESHOLD = 80


def measurement(counts):
    invalid = sum(count for status, count in counts.items() if status not in STATES)
    denominator = sum(counts[status] for status in STATES if status != "EXCUSED")
    attended = counts["PRESENT"] + counts["LATE"] + counts["HALF_DAY"] * 0.5
    rate = round(attended / denominator * 100, 1) if denominator and not invalid else None
    return rate, denominator, invalid


def recorded_trend(rows):
    dates = defaultdict(Counter)
    for row in rows:
        dates[row.attendance_date][row.status] += 1
    days = sorted(dates)
    if len(days) < 6:
        return "veri yetersiz"
    previous, recent = Counter(), Counter()
    for day in days[-6:-3]:
        previous.update(dates[day])
    for day in days[-3:]:
        recent.update(dates[day])
    before, after = measurement(previous)[0], measurement(recent)[0]
    if before is None or after is None:
        return "veri yetersiz"
    return "artıyor" if after > before else "azalıyor" if after < before else "stabil"


async def summary(db, tenant, days=30):
    if not tenant.organization_id:
        raise ForbiddenException("Önce kurum çalışma alanını seçin")
    end = school_today()
    start = end - timedelta(days=days - 1)
    students = (await db.execute(select(Student.id, Student.first_name, Student.last_name).where(
        Student.organization_id == tenant.organization_id, Student.deleted_at.is_(None)))).all()
    names = {row.id: f"{row.first_name} {row.last_name}" for row in students}
    rows = (await db.execute(select(AttendanceRecord.student_id, AttendanceRecord.attendance_date,
        cast(AttendanceRecord.status, String).label("status"))
        .join(Student, Student.id == AttendanceRecord.student_id).where(
            AttendanceRecord.organization_id == tenant.organization_id, Student.organization_id == tenant.organization_id,
            Student.deleted_at.is_(None), AttendanceRecord.deleted_at.is_(None),
            AttendanceRecord.attendance_date >= start, AttendanceRecord.attendance_date <= end)
        .order_by(AttendanceRecord.attendance_date, AttendanceRecord.student_id))).all()
    counts = Counter(row.status for row in rows)
    rate, denominator, invalid = measurement(counts)
    by_student = defaultdict(list)
    for row in rows:
        if row.student_id in names:
            by_student[row.student_id].append(row)
    alerts = []
    for student_id, observations in by_student.items():
        current, pupil_denominator, _ = measurement(Counter(row.status for row in observations))
        if current is None or current >= MONITORING_THRESHOLD:
            continue
        alerts.append({"student_id": str(student_id), "student_name": names[student_id],
            "current_rate": current, "attendance_rate": current, "predicted_rate": None,
            "record_count": len(observations), "attendance_denominator": pupil_denominator,
            "trend": recorded_trend(observations),
            "risk_level": "kritik" if current < 60 else "yüksek" if current < 70 else "orta"})
    alerts.sort(key=lambda row: (row["current_rate"], row["student_id"]))
    patterns = []
    for alert in alerts[:10]:
        weekdays = defaultdict(Counter)
        for row in by_student[next(identifier for identifier in names if str(identifier) == alert["student_id"])]:
            weekdays[row.attendance_date.weekday()][row.status] += 1
        pupil_patterns = []
        for day, day_counts in sorted(weekdays.items()):
            _, day_denominator, unknown = measurement(day_counts)
            if not day_denominator or unknown:
                continue
            absence = round(day_counts["ABSENT"] / day_denominator * 100, 1)
            if absence > 10:
                pupil_patterns.append({"day": DAY_NAMES[day], "rate": absence,
                    "record_count": day_denominator, "severity": "high" if absence > 20 else "medium"})
        if pupil_patterns:
            patterns.append({"student_id": alert["student_id"], "student_name": alert["student_name"], "patterns": pupil_patterns})
    if not rows:
        recommendations = ["Seçili dönemde yoklama kaydı yok; devam oranı hesaplanamıyor."]
    elif invalid:
        recommendations = ["Tanınmayan yoklama durumları incelenmeli; eksik oranlar gösterilmez."]
    elif rate is None:
        recommendations = ["Oran hesabına giren yoklama kaydı yok; izinli kayıtlar paydanın dışındadır."]
    elif alerts:
        recommendations = [f"{len(alerts)} öğrencinin kayıtlı devam oranı %{MONITORING_THRESHOLD} izleme eşiğinin altında."]
    else:
        recommendations = [f"Oranı hesaplanabilen öğrencilerde %{MONITORING_THRESHOLD} izleme eşiğinin altında kayıt yok."]
    return {"analysis_kind": "RECORDED_ATTENDANCE", "data_source": ["attendance_records"],
        "ai_model": None, "prediction_available": False, "predicted_rate": None,
        "current_rate": rate, "trend": recorded_trend(rows),
        "trend_comparison": "last_3_recorded_dates_vs_previous_3", "analysis_period_days": days,
        "period_start": start.isoformat(), "period_end": end.isoformat(),
        "status_counts": {status: counts[status] for status in STATES}, "attendance_measure": MEASURE,
        "total_records": len(rows), "attendance_denominator": denominator, "invalid_attendance_count": invalid,
        "requires_review": bool(invalid), "total_students": len(students), "total_analyzed": len(by_student),
        "total_students_analyzed": len(by_student), "students_without_records": len(students) - len(by_student),
        "monitoring_threshold": MONITORING_THRESHOLD, "total_risk_students": len(alerts),
        "risk_results_limited": len(alerts) > 10, "risk_alerts": alerts[:10], "risk_students": alerts[:10],
        "patterns": patterns, "recommendations": recommendations}
