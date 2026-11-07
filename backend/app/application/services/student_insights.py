"""Permission-scoped summaries of recorded data; never sample scores or diagnoses."""
from typing import Literal

from sqlalchemy import select

from app.core.exceptions import ForbiddenException, ValidationException
from app.core.student_access import require_student_access
from app.infrastructure.models.models import AttendanceRecord, DailyDevelopmentReport, Debt, DebtStatus, Student
from app.infrastructure.repositories.base import BaseRepository

InsightContext = Literal["dashboard", "children", "attendance", "finances", "health", "academic", "schedule",
    "homework", "materials", "communication", "announcements", "activities", "reports", "chat"]

TITLES = {"dashboard": "Kayıtlara dayalı öğrenci özeti", "children": "Güncel gelişim özeti", "attendance": "Devam kayıtları özeti",
    "finances": "Borç ve tahsilat özeti", "health": "Günlük gelişim kaydı", "academic": "Ders notları özeti",
    "schedule": "Ders hazırlığı özeti", "homework": "Ödev değerlendirmeleri", "materials": "Ders çalışma özeti",
    "communication": "Görüşme hazırlığı", "announcements": "Duyuru takibi", "activities": "Etkinlik hazırlığı",
    "reports": "Gelişim raporları özeti", "chat": "Görüşme hazırlığı"}


def enum_value(value):
    return value.value if hasattr(value, "value") else value


async def for_student(db, tenant, student_id, context="dashboard"):
    if context not in TITLES:
        raise ValidationException("Geçersiz öğrenci özeti bağlamı")
    student = await BaseRepository(db, tenant).get_by_id(student_id, Student)
    await require_student_access(db, tenant, student.id)
    parent = tenant.parent_portal or tenant.role_slugs == {"parent"}
    academic = tenant.has_permission("parent.view_children" if parent else "academic.read")
    attendance = tenant.has_permission("parent.view_attendance") if parent else tenant.has_any_permission(["attendance.read", "teacher.view_attendance"])
    finance = tenant.has_permission("parent.view_finances" if parent else "finance.read")
    reports = tenant.has_permission("parent.view_children" if parent else "daily_reports.read")
    health = tenant.has_permission("parent.view_children" if parent else "health.read")
    if (context == "finances" and not finance) or (context == "attendance" and not attendance) or (context == "academic" and not academic) or (context == "health" and not health):
        raise ForbiddenException("Bu özet alanını görüntüleme yetkiniz yok")

    result = {"student_id": str(student.id), "analysis_type": context, "analysis_kind": "RECORDED_DATA", "title": TITLES[context],
        "metrics": [], "recommendations": [], "current_grade": None, "current_average": None, "predicted_grade": None,
        "confidence": None, "attendance_rate": None, "subject_performance": {},
        "available": {"academic": academic, "attendance": attendance, "finance": finance, "reports": reports}}
    metrics = result["metrics"]
    if academic and context != "finances":
        from app.application.services.academic_records import records, normalized_score
        rows = await records(db, student.organization_id, [student.id], limit=20)
        by_subject, grades = {}, []
        for row in rows:
            normalized = normalized_score(row)
            if normalized is None:
                continue
            if context == "homework" and enum_value(row.grade_type) not in {"HOMEWORK", "PROJECT"}:
                continue
            grades.append(normalized); by_subject.setdefault(enum_value(row.subject), []).append(normalized)
        average = round(sum(grades) / len(grades), 1) if grades else None
        result.update(current_grade=average, current_average=average, grade_count=len(grades),
            subject_performance={subject: round(sum(scores) / len(scores), 1) for subject, scores in by_subject.items()})
        metrics.extend([{"label": "Son değerlendirme sayısı", "value": str(len(grades))},
            {"label": "Not ortalaması (100 üzerinden)", "value": str(average) if average is not None else "Henüz değerlendirme kaydı yok"}])
    if attendance and context not in {"finances", "health"}:
        rows = (await db.execute(select(AttendanceRecord).where(AttendanceRecord.student_id == student.id,
            AttendanceRecord.deleted_at.is_(None)).order_by(AttendanceRecord.attendance_date.desc(), AttendanceRecord.id).limit(30))).scalars().all()
        rate = round(sum(enum_value(row.status) == "PRESENT" for row in rows) / len(rows) * 100, 1) if rows else None
        result.update(attendance_rate=rate, attendance_count=len(rows))
        metrics.extend([{"label": "Son yoklama sayısı", "value": str(len(rows))},
            {"label": "Tam gün mevcut oranı", "value": f"%{rate}" if rate is not None else "Henüz yoklama kaydı yok"}])
    if context == "finances":
        debts = (await db.execute(select(Debt).where(Debt.student_id == student.id, Debt.deleted_at.is_(None), Debt.status != DebtStatus.CANCELLED))).scalars().all()
        remaining = sum((row.amount - row.paid_amount for row in debts), 0)
        result["remaining_debt"] = float(remaining)
        metrics.extend([{"label": "Açık borç kaydı", "value": str(sum(row.amount > row.paid_amount for row in debts))},
            {"label": "Kalan tutar", "value": f"₺{remaining:,.2f}"}])
    if reports and context in {"children", "reports", "health"}:
        rows = (await db.execute(select(DailyDevelopmentReport).where(DailyDevelopmentReport.student_id == student.id)
            .order_by(DailyDevelopmentReport.date.desc(), DailyDevelopmentReport.id).limit(7))).scalars().all()
        metrics.append({"label": "Son gelişim raporu", "value": rows[0].date.isoformat() if rows else "Henüz rapor kaydı yok"})
        if context == "health" and rows:
            for label, value in [("Ruh hâli", rows[0].mood), ("Uyku", rows[0].sleep_status)]:
                if value:
                    metrics.append({"label": label, "value": str(enum_value(value))})
    result["summary"] = "Yetkiniz kapsamındaki kayıtlar gösterilir. Notlar son 20 değerlendirmeyi, devam oranı son 30 yoklama kaydını kapsar."
    if not metrics:
        result["summary"] = "Bu bağlam için görüntülenebilir değerlendirme kaydı bulunmuyor."
    return result
