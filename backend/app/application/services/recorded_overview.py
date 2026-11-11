"""Shared recorded measures for the overview and operational capacity panels."""
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.application.services import academic_summary, financial_summary, recorded_attendance
from app.core.exceptions import ForbiddenException
from app.core.tenant import effective_roles
from app.infrastructure.models.models import ClassRoom, Student, StudentStatus, User, UserStatus


async def insights(db, tenant, days=30):
    academic = await academic_summary.summary(db, tenant, days)
    attendance = await recorded_attendance.summary(db, tenant, days)
    financial = await financial_summary.summary(db, tenant, months=1)
    actions = []
    if not academic["valid_grade_count"]:
        actions.append("Seçili dönemde geçerli not kaydı yok.")
    elif academic["at_risk_count"]:
        actions.append(f'{academic["at_risk_count"]} öğrencinin kayıtlı not ortalaması 60/100 izleme eşiğinin altında.')
    if not attendance["total_records"]:
        actions.append("Seçili dönemde yoklama kaydı yok.")
    elif attendance["total_risk_students"]:
        actions.append(f'{attendance["total_risk_students"]} öğrencinin kayıtlı devam oranı %80 izleme eşiğinin altında.')
    if financial["requires_review"]:
        actions.append("Finans kayıtlarında incelenmesi gereken tutar veya tarih bilgisi var.")
    elif financial["overdue_debts_count"]:
        actions.append(f'{financial["overdue_debts_count"]} borç kaydının vadesi geçmiş.')
    return {"analysis_kind": "RECORDED_OVERVIEW", "ai_model": None, "prediction_available": False,
        "period_start": academic["period_start"], "period_end": academic["period_end"],
        "financial_scope": "ALL_ACTIVE_DEBTS", "requires_review": financial["requires_review"] or attendance["requires_review"],
        "insights": {
            "academic_performance": {"overall_trend": academic["trend"], "average_grade": academic["average_grade"],
                "at_risk_students": academic["at_risk_count"], "valid_grade_count": academic["valid_grade_count"]},
            "attendance": {"overall_rate": attendance["current_rate"], "trend": attendance["trend"], "record_count": attendance["total_records"]},
            "financial": {"collection_rate": financial["collection_rate"], "forecast_trend": None,
                "debt_count": financial["debt_count"], "forecast_available": False},
            "parent_satisfaction": {"score": None, "sentiment": None},
        }, "priority_actions": actions}


async def operations(db, tenant):
    if not tenant.organization_id:
        raise ForbiddenException("Önce kurum çalışma alanını seçin")
    classes = (await db.execute(select(ClassRoom).where(ClassRoom.organization_id == tenant.organization_id,
        ClassRoom.deleted_at.is_(None)))).scalars().all()
    active_classes = [row for row in classes if row.is_active]
    students = (await db.execute(select(Student).where(Student.organization_id == tenant.organization_id,
        Student.deleted_at.is_(None)))).scalars().all()
    active_students = [row for row in students if row.status == StudentStatus.ACTIVE]
    users = (await db.execute(select(User).options(selectinload(User.roles)).where(User.organization_id == tenant.organization_id,
        User.deleted_at.is_(None), User.status == UserStatus.ACTIVE, User.is_super_admin.is_(False)))).scalars().all()
    staff = [row for row in users if any(role.slug != "parent" for role in effective_roles(row))]
    enrollment = Counter(row.class_id for row in active_students)
    known = [row for row in active_classes if row.capacity is not None and row.capacity > 0]
    unknown = len(active_classes) - len(known)
    capacity = sum(row.capacity for row in known)
    assigned = sum(enrollment[row.id] for row in active_classes)
    utilization = round(assigned / capacity * 100, 1) if capacity and not unknown else None
    over = [{"class_id": str(row.id), "class_name": row.name, "capacity": row.capacity,
        "active_student_count": enrollment[row.id]} for row in known if enrollment[row.id] > row.capacity]
    actions = []
    if unknown:
        actions.append(f"{unknown} etkin sınıfın kapasitesi tanımlanmamış; toplam doluluk hesaplanamıyor.")
    if over:
        actions.append(f"{len(over)} sınıfta kayıtlı etkin öğrenci sayısı kapasitenin üzerinde.")
    unassigned = len(active_students) - assigned
    if unassigned:
        actions.append(f"{unassigned} etkin öğrenci etkin bir sınıfa bağlı değil.")
    return {"analysis_kind": "RECORDED_OPERATIONS", "ai_model": None, "prediction_available": False,
        "optimization_scores": {"overall_score": None, "classroom_utilization": utilization, "staff_efficiency": None},
        "optimization_potential": None, "counts": {"class_count": len(active_classes), "inactive_class_count": len(classes) - len(active_classes),
            "active_students": len(active_students), "total_students": len(students), "assigned_active_students": assigned,
            "unassigned_active_students": unassigned, "known_capacity": capacity, "classes_without_capacity": unknown,
            "staff_count": len(staff)}, "over_capacity_classes": over,
        "resource_allocation": {"recommended_actions": actions}, "recommendations": [],
        "data_source": ["classes", "students", "users", "roles"]}
