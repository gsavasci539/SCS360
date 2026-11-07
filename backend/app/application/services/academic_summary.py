"""Measured academic results; no trained prediction or confidence is implied."""
from collections import defaultdict
from datetime import timedelta

from sqlalchemy import select

from app.application.services.academic_records import normalized_score, records
from app.core.dates import school_today
from app.infrastructure.models.models import Student


async def summary(db, tenant, days=30):
    end = school_today()
    start = end - timedelta(days=days - 1)
    students = (await db.execute(select(Student).where(Student.organization_id == tenant.organization_id,
        Student.deleted_at.is_(None)))).scalars().all()
    rows = await records(db, tenant.organization_id, [row.id for row in students], start=start, end=end)
    scores, subjects, valid, ignored = defaultdict(list), defaultdict(list), [], 0
    for row in sorted(rows, key=lambda row: (row.exam_date, str(row.id))):
        score = normalized_score(row)
        if score is None:
            ignored += 1
        else:
            scores[row.student_id].append((row.exam_date, score))
            subjects[row.subject].append(score)
            valid.append((row.exam_date, score))
    risks = []
    for student in students:
        values = scores.get(student.id, [])
        if not values:
            continue
        average = sum(value for _, value in values) / len(values)
        if average >= 70:
            continue
        trend = "veri yetersiz"
        if len(values) >= 6 and values[-3][0] > values[-4][0]:
            recent, previous = sum(value for _, value in values[-3:]) / 3, sum(value for _, value in values[-6:-3]) / 3
            trend = "artıyor" if recent > previous else "azalıyor" if recent < previous else "stabil"
        risks.append({"student_id": str(student.id), "student_name": f"{student.first_name} {student.last_name}",
            "current_average": round(average, 1), "grade_count": len(values), "trend": trend,
            "predicted_grade": None, "confidence": None, "risk_level": "yüksek" if average < 60 else "orta"})
    risks.sort(key=lambda row: (row["current_average"], row["student_id"]))
    overall_trend, improvement = "insufficient_data", None
    if len(valid) >= 6 and valid[-3][0] > valid[-4][0]:
        improvement = round(sum(value for _, value in valid[-3:]) / 3 - sum(value for _, value in valid[-6:-3]) / 3, 1)
        overall_trend = "improving" if improvement > 0 else "declining" if improvement < 0 else "stable"
    values = [value for _, value in valid]
    below = [row for row in risks if row["current_average"] < 60]
    missing = len(students) - len(scores)
    recommendations = []
    if not scores:
        recommendations.append("Seçili dönemde geçerli değerlendirme kaydı yok; performans yorumu yapılamıyor.")
    elif risks:
        recommendations.append(f"{len(risks)} öğrencinin kayıtlı not ortalaması 70/100 izleme eşiğinin altında.")
    else:
        recommendations.append("Not kaydı bulunan öğrenciler arasında 70/100 izleme eşiğinin altında ortalama yok.")
    if missing:
        recommendations.append(f"{missing} öğrenci için seçili dönemde değerlendirme kaydı yok.")
    return {"analysis_kind": "RECORDED_GRADES", "ai_model": None, "prediction_available": False,
        "confidence_threshold": None, "risk_threshold": 70, "period_start": start.isoformat(), "period_end": end.isoformat(),
        "total_students": len(students), "total_analyzed": len(scores), "students_without_grades": missing,
        "valid_grade_count": sum(len(values) for values in scores.values()), "ignored_grade_count": ignored,
        "total_risk_students": len(risks), "risk_students": risks[:10], "recommendations": recommendations,
        "average_grade": round(sum(values) / len(values), 1) if values else None,
        "passing_rate": round(sum(value >= 60 for value in values) / len(values) * 100, 1) if values else None,
        "total_grades": len(values), "at_risk_count": len(below),
        "at_risk_students": [{"student_id": row["student_id"], "name": row["student_name"], "average": row["current_average"]} for row in below[:10]],
        "subject_averages": {subject: round(sum(items) / len(items), 1) for subject, items in subjects.items()},
        "grade_distribution": {"excellent": sum(value >= 90 for value in values), "good": sum(70 <= value < 90 for value in values),
            "average": sum(60 <= value < 70 for value in values), "below_average": sum(value < 60 for value in values)},
        "trend": overall_trend, "improvement_rate": improvement, "improvement_unit": "percentage_points"}
