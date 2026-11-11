"""Recorded school measures; no calibrated organization score or prediction exists."""
from collections import Counter, defaultdict
from datetime import timedelta

from sqlalchemy import String, cast, select

from app.application.services import academic_summary, financial_summary
from app.application.services.academic_records import normalized_score, records
from app.core.dates import school_today
from app.core.exceptions import ForbiddenException
from app.infrastructure.models.models import AttendanceRecord, Parent, Student


def period(tenant, days):
    if not tenant.organization_id:
        raise ForbiddenException("Önce kurum çalışma alanını seçin")
    end = school_today()
    return end - timedelta(days=days - 1), end


async def performance_trends(db, tenant, days=90):
    start, end = period(tenant, days)
    rows = await records(db, tenant.organization_id, start=start, end=end)
    weeks = defaultdict(list)
    ignored = 0
    for row in rows:
        value = normalized_score(row)
        if value is None:
            ignored += 1
            continue
        monday = row.exam_date - timedelta(days=row.exam_date.weekday())
        weeks[monday].append(value)
    trends = [{"week": monday.strftime("%d/%m"), "week_start": monday.isoformat(),
        "average_grade": round(sum(values) / len(values), 1), "grade_count": len(values)}
        for monday, values in sorted(weeks.items())]
    direction, relative, change = "insufficient_data", None, None
    if len(trends) >= 2:
        first, last = trends[0]["average_grade"], trends[-1]["average_grade"]
        change = round(last - first, 1)
        direction = "improving" if change > 0 else "declining" if change < 0 else "stable"
        relative = round(change / first * 100, 1) if first > 0 else None
    return {"analysis_kind": "RECORDED_GRADES", "ai_model": None, "prediction_available": False,
        "data_source": ["grades", "exam_results"], "period_start": start.isoformat(), "period_end": end.isoformat(),
        "trends": trends, "trend_direction": direction, "trend_percentage": relative,
        "change_percentage_points": change, "total_weeks": len(trends),
        "total_grades_analyzed": sum(row["grade_count"] for row in trends), "ignored_grade_count": ignored}


async def organization_health(db, tenant, days=30):
    start, end = period(tenant, days)
    academic = await academic_summary.summary(db, tenant, days)
    financial = await financial_summary.summary(db, tenant, months=1)
    attendance = (await db.execute(select(cast(AttendanceRecord.status, String))
        .join(Student, Student.id == AttendanceRecord.student_id).where(
            AttendanceRecord.organization_id == tenant.organization_id, Student.organization_id == tenant.organization_id,
            Student.deleted_at.is_(None), AttendanceRecord.deleted_at.is_(None),
            AttendanceRecord.attendance_date >= start, AttendanceRecord.attendance_date <= end))).scalars().all()
    counts = Counter(attendance)
    unknown = sum(count for status, count in counts.items() if status not in {"PRESENT", "LATE", "HALF_DAY", "ABSENT", "EXCUSED"})
    denominator = sum(counts[status] for status in ("PRESENT", "LATE", "HALF_DAY", "ABSENT"))
    attended = counts["PRESENT"] + counts["LATE"] + counts["HALF_DAY"] * 0.5
    rate = round(attended / denominator * 100, 1) if denominator and not unknown else None
    parents = (await db.execute(select(Parent.receive_notifications).where(
        Parent.organization_id == tenant.organization_id, Parent.deleted_at.is_(None)))).scalars().all()
    return {"analysis_kind": "RECORDED_SCHOOL_METRICS", "ai_model": None, "prediction_available": False,
        "period_start": start.isoformat(), "period_end": end.isoformat(),
        "financial_scope": "ALL_ACTIVE_DEBTS", "overall_health": None, "health_status": "not_calculated",
        "status_color": "#6b7280", "scores": {"academic": academic["average_grade"],
            "attendance": rate, "financial": financial["collection_rate"], "engagement": None},
        "score_measures": {"academic": "normalized_grade_average", "attendance": "recorded_attendance_rate",
            "financial": "debt_collection_rate", "engagement": "not_measured"},
        "metrics": {"total_students": academic["total_students"], "total_parents": len(parents),
            "total_grades": academic["valid_grade_count"], "ignored_grade_count": academic["ignored_grade_count"],
            "total_attendance_records": len(attendance), "attendance_denominator": denominator,
            "attendance_excused_count": counts["EXCUSED"], "attendance_half_day_count": counts["HALF_DAY"],
            "invalid_attendance_count": unknown,
            "attendance_measure": "100 * (PRESENT + LATE + 0.5 * HALF_DAY) / (PRESENT + LATE + HALF_DAY + ABSENT)",
            "total_debts": financial["debt_count"],
            "notification_opt_in_rate": round(sum(value is True for value in parents) / len(parents) * 100, 1) if parents else None},
        "requires_review": financial["requires_review"] or bool(unknown),
        "data_source": ["grades", "exam_results", "attendance_records", "debts", "payments", "parents"],
        "recommendations": ["Toplam kurum sağlığı ve veli katılımı için doğrulanmış ölçüm bulunmuyor; yalnız kayıtlı göstergeler gösterilir."]}
