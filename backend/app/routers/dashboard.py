from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.dates import school_today
from app.infrastructure.models.models import ClassRoom as Class
from typing import Optional, Literal
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import UTC, datetime, date

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_tenant_context
from app.core.permissions import require_permission, PermissionChecker
from app.core.responses import success_response
from app.domain.entities.user import User
from app.core.tenant import TenantContext
from app.infrastructure.reports import ReportService

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/summary")
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("dashboard.read", "dashboard.view")),
):
    from sqlalchemy import func
    from app.infrastructure.models.models import Student, StudentStatus, Branch, Debt, DebtStatus, Payment, AttendanceRecord, AttendanceStatus
    from app.infrastructure.repositories.base import BaseRepository
    from datetime import UTC, time
    repo = BaseRepository(db, tenant)
    def scoped(model):
        return repo._branch_filter(repo._org_filter(select(model), model), model)
    async def count(query):
        return (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    students = scoped(Student).where(Student.deleted_at.is_(None))
    classes = scoped(Class).where(Class.deleted_at.is_(None))
    branches = repo._org_filter(select(Branch), Branch).where(Branch.deleted_at.is_(None))
    if tenant.branch_ids and not tenant.is_super_admin:
        branches = branches.where(Branch.id.in_(tenant.branch_ids))
    today = school_today()
    start = datetime.combine(today.replace(day=1), time.min, tzinfo=UTC)
    end = start.replace(year=start.year + (start.month == 12), month=start.month % 12 + 1)
    payments = (await db.execute(scoped(Payment).where(Payment.cancelled_at.is_(None),
        Payment.payment_date >= start, Payment.payment_date < end).with_only_columns(Payment.amount))).all()
    debts = (await db.execute(scoped(Debt).where(Debt.deleted_at.is_(None), Debt.status != DebtStatus.CANCELLED)
        .with_only_columns((Debt.amount - Debt.paid_amount).label("remaining_amount"), Debt.due_date))).all()
    absent = scoped(AttendanceRecord).where(AttendanceRecord.attendance_date == today, AttendanceRecord.status == AttendanceStatus.ABSENT)
    return success_response({"total_students": await count(students),
        "active_students": await count(students.where(Student.status == StudentStatus.ACTIVE)),
        "total_branches": await count(branches), "total_classes": await count(classes),
        "absent_today": await count(absent), "monthly_payments": float(sum(row.amount for row in payments)),
        "pending_debt": float(sum(row.remaining_amount for row in debts if row.remaining_amount > 0 and row.due_date >= today)),
        "overdue_debt": float(sum(row.remaining_amount for row in debts if row.remaining_amount > 0 and row.due_date < today))})


@router.get("/charts")
async def get_dashboard_charts(
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(get_tenant_context),
):
    """Get dashboard chart data"""
    
    from app.repositories import PaymentRepository
    from app.domain.entities.payment import Payment
    from sqlalchemy import func, extract, select
    
    payment_repo = PaymentRepository()
    
    # Get monthly income for last 6 months
    monthly_income = []
    months = ["Oca", "Şub", "Mar", "Nis", "May", "Haz"]
    
    try:
        for i, month_name in enumerate(months):
            # Get actual data from database
            current_year = datetime.utcnow().year
            month_num = i + 1
            
            result = await db.execute(
                select(func.sum(Payment.amount))
                .where(
                    Payment.organization_id == tenant.organization_id,
                    extract('year', Payment.payment_date) == current_year,
                    extract('month', Payment.payment_date) == month_num,
                    Payment.status == "completed"
                )
            )
            amount = result.scalar() or 0
            
            monthly_income.append({
                "month": month_name,
                "amount": float(amount)
            })
    except:
        # Fallback to empty data if query fails
        monthly_income = [{"month": month_name, "amount": 0} for month_name in months]
    
    return success_response({
        "monthly_income": monthly_income
    })


@router.get("/overview")
async def get_dashboard_overview(
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(get_tenant_context),
):
    """Get dashboard overview statistics"""
    
    from app.repositories import (
        StudentRepository,
        ClassRepository,
        DebtRepository,
        PaymentRepository,
        AttendanceRepository
    )
    
    student_repo = StudentRepository()
    class_repo = ClassRepository()
    debt_repo = DebtRepository()
    payment_repo = PaymentRepository()
    attendance_repo = AttendanceRepository()
    
    # Get counts
    total_students = await student_repo.count(db, {"organization_id": tenant.organization_id})
    total_classes = await class_repo.count(db, {"organization_id": tenant.organization_id})
    
    # Get financial summary
    try:
        debts = await debt_repo.get_by_organization(db, tenant.organization_id)
        total_debt = sum(d.remaining_amount for d in debts if d.remaining_amount > 0)
    except:
        total_debt = 0
    
    try:
        payments = await payment_repo.get_by_organization(db, tenant.organization_id)
        total_payments = sum(p.amount for p in payments if p.status == "completed")
    except:
        total_payments = 0
    
    # Get today's attendance
    today = school_today()
    present_today = 0
    absent_today = 0
    try:
        for cls in await class_repo.get_active_classes(db, tenant.organization_id):
            class_attendance = await attendance_repo.get_by_class_and_date(
                db, cls.id, datetime(today.year, today.month, today.day)
            )
            present_today += len([a for a in class_attendance if a.status == "present"])
            absent_today += len([a for a in class_attendance if a.status == "absent"])
    except:
        pass
    
    attendance_rate = round(present_today / (present_today + absent_today) * 100, 1) if (present_today + absent_today) > 0 else 0
    
    return success_response({
        "total_students": total_students,
        "total_classes": total_classes,
        "total_debt": float(total_debt),
        "total_payments": float(total_payments),
        "present_today": present_today,
        "absent_today": absent_today,
        "attendance_rate": attendance_rate
    })


@router.get("/recent-activity")
@require_permission("dashboard.view")
async def get_recent_activity(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user)
):
    """Get recent activity"""
    
    from sqlalchemy import select, desc
    from app.domain.entities.audit_log import AuditLog
    
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.organization_id == current_user.organization_id)
        .order_by(desc(AuditLog.created_at))
        .limit(limit)
    )
    activities = result.scalars().all()
    
    return success_response(activities)


@router.get("/upcoming-events")
@require_permission("dashboard.view")
async def get_upcoming_events(
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user)
):
    """Get upcoming events (announcements, payment due dates, etc.)"""
    
    from sqlalchemy import select, and_
    from app.domain.entities.announcement import Announcement
    from app.domain.entities.debt import Debt
    
    # Get upcoming announcements
    result = await db.execute(
        select(Announcement)
        .where(
            and_(
                Announcement.organization_id == current_user.organization_id,
                Announcement.status == "SCHEDULED",
                Announcement.scheduled_at >= datetime.utcnow()
            )
        )
        .order_by(Announcement.scheduled_at)
        .limit(limit)
    )
    announcements = result.scalars().all()
    
    # Get overdue debts
    result = await db.execute(
        select(Debt)
        .where(
            and_(
                Debt.organization_id == current_user.organization_id,
                Debt.due_date >= datetime.utcnow(),
                Debt.amount > Debt.paid_amount
            )
        )
        .order_by(Debt.due_date)
        .limit(limit)
    )
    upcoming_payments = result.scalars().all()
    
    return success_response({
        "announcements": announcements,
        "upcoming_payments": upcoming_payments
    })


@router.get("/financial-summary")
@require_permission("dashboard.financial")
async def get_financial_summary(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user)
):
    """Get financial summary for dashboard"""
    
    report_service = ReportService(db)
    report = await report_service.get_financial_report(
        current_user.organization_id,
        None,
        start_date,
        end_date
    )
    
    return success_response(report)


@router.get("/attendance-summary")
@require_permission("dashboard.attendance")
async def get_attendance_summary(
    class_id: Optional[UUID] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user)
):
    """Get attendance summary for dashboard"""
    
    report_service = ReportService(db)
    report = await report_service.get_attendance_report(
        current_user.organization_id,
        class_id,
        start_date,
        end_date
    )
    
    return success_response(report)


# ==================== OWNER DASHBOARD ENDPOINTS ====================

@router.get("/owner/dashboard/overview")
@require_permission("branch.view_all")
async def get_owner_dashboard_overview(
    academic_year_id: Optional[UUID] = None,
    date_range: Optional[str] = None,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user)
):
    """Get consolidated dashboard overview for Owner/Kurum Sahibi"""
    
    from app.repositories import (
        StudentRepository,
        ClassRepository,
        DebtRepository,
        PaymentRepository,
        AttendanceRepository
    )
    from app.infrastructure.models.models import Branch
    
    student_repo = StudentRepository()
    class_repo = ClassRepository()
    debt_repo = DebtRepository()
    payment_repo = PaymentRepository()
    attendance_repo = AttendanceRepository()
    
    # Get all branches
    result = await db.execute(
        select(Branch).where(Branch.organization_id == current_user.organization_id)
    )
    branches = result.scalars().all()
    
    # Calculate totals across all branches
    total_students = 0
    total_active_students = 0
    total_classes = 0
    total_staff = 0
    total_capacity = 0
    total_debt = 0
    total_collected = 0
    
    branch_metrics = []
    
    for branch in branches:
        # Branch specific metrics
        branch_students = await student_repo.count(db, {"branch_id": branch.id})
        branch_active_students = await student_repo.count(db, {"branch_id": branch.id, "status": "active"})
        branch_classes = await class_repo.count(db, {"branch_id": branch.id})
        
        # Financial metrics
        try:
            branch_debts = await debt_repo.get_by_branch(db, branch.id)
            branch_debt_total = sum(d.remaining_amount for d in branch_debts if d.remaining_amount > 0)
        except:
            branch_debt_total = 0
        
        try:
            branch_payments = await payment_repo.get_by_branch(db, branch.id)
            branch_collected = sum(p.amount for p in branch_payments if p.status == "completed")
        except:
            branch_collected = 0
        
        # Attendance rate for today
        today = school_today()
        present_count = 0
        absent_count = 0
        try:
            branch_classes_result = await db.execute(
                select(Class).where(Class.branch_id == branch.id)
            )
            branch_classes_list = branch_classes_result.scalars().all()
            
            for cls in branch_classes_list:
                class_attendance = await attendance_repo.get_by_class_and_date(
                    db, cls.id, datetime(today.year, today.month, today.day)
                )
                present_count += len([a for a in class_attendance if a.status == "present"])
                absent_count += len([a for a in class_attendance if a.status == "absent"])
        except:
            pass
        
        attendance_rate = round(present_count / (present_count + absent_count) * 100, 1) if (present_count + absent_count) > 0 else 0
        
        branch_metrics.append({
            "branch_id": str(branch.id),
            "branch_name": branch.name,
            "students": branch_students,
            "active_students": branch_active_students,
            "classes": branch_classes,
            "capacity": branch.capacity,
            "occupancy_rate": round(branch_active_students / branch.capacity * 100, 1) if branch.capacity > 0 else 0,
            "debt_total": float(branch_debt_total),
            "collected": float(branch_collected),
            "attendance_rate": attendance_rate
        })
        
        # Add to totals
        total_students += branch_students
        total_active_students += branch_active_students
        total_classes += branch_classes
        total_capacity += branch.capacity
        total_debt += branch_debt_total
        total_collected += branch_collected
    
    # Calculate collection rate
    collection_rate = round(total_collected / (total_collected + total_debt) * 100, 1) if (total_collected + total_debt) > 0 else 0
    
    return success_response({
        "total_students": total_students,
        "total_active_students": total_active_students,
        "total_branches": len(branches),
        "total_classes": total_classes,
        "total_capacity": total_capacity,
        "occupancy_rate": round(total_active_students / total_capacity * 100, 1) if total_capacity > 0 else 0,
        "total_debt": float(total_debt),
        "total_collected": float(total_collected),
        "collection_rate": collection_rate,
        "branch_metrics": branch_metrics
    })


@router.get("/owner/branches/metrics-comparison")
@require_permission("branch.view_all")
async def get_branches_metrics_comparison(
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user)
):
    """Get metrics comparison across all branches for Owner"""
    
    from app.repositories import (
        StudentRepository,
        ClassRepository,
        DebtRepository,
        PaymentRepository,
        AttendanceRepository
    )
    from app.infrastructure.models.models import Branch
    
    student_repo = StudentRepository()
    class_repo = ClassRepository()
    debt_repo = DebtRepository()
    payment_repo = PaymentRepository()
    attendance_repo = AttendanceRepository()
    
    result = await db.execute(
        select(Branch).where(Branch.organization_id == current_user.organization_id)
    )
    branches = result.scalars().all()
    
    comparison_data = []
    
    for branch in branches:
        # Get student metrics
        students = await student_repo.count(db, {"branch_id": branch.id})
        active_students = await student_repo.count(db, {"branch_id": branch.id, "status": "active"})
        
        # Get class metrics
        classes = await class_repo.count(db, {"branch_id": branch.id})
        
        # Get financial metrics
        try:
            debts = await debt_repo.get_by_branch(db, branch.id)
            debt_total = sum(d.remaining_amount for d in debts if d.remaining_amount > 0)
        except:
            debt_total = 0
        
        try:
            payments = await payment_repo.get_by_branch(db, branch.id)
            collected = sum(p.amount for p in payments if p.status == "completed")
        except:
            collected = 0
        
        # Get attendance metrics for last 30 days
        from datetime import timedelta
        thirty_days_ago = school_today() - timedelta(days=30)
        
        attendance_rate = 0
        try:
            branch_classes_result = await db.execute(
                select(Class).where(Class.branch_id == branch.id)
            )
            branch_classes_list = branch_classes_result.scalars().all()
            
            total_present = 0
            total_absent = 0
            
            for cls in branch_classes_list:
                # Get attendance for this period
                class_attendance = await attendance_repo.get_by_class_and_date_range(
                    db, cls.id, thirty_days_ago, school_today()
                )
                total_present += len([a for a in class_attendance if a.status == "present"])
                total_absent += len([a for a in class_attendance if a.status == "absent"])
            
            attendance_rate = round(total_present / (total_present + total_absent) * 100, 1) if (total_present + total_absent) > 0 else 0
        except:
            pass
        
        comparison_data.append({
            "branch_id": str(branch.id),
            "branch_name": branch.name,
            "students": students,
            "active_students": active_students,
            "classes": classes,
            "debt_total": float(debt_total),
            "collected": float(collected),
            "attendance_rate": attendance_rate,
            "occupancy_rate": round(active_students / branch.capacity * 100, 1) if branch.capacity > 0 else 0
        })
    
    return success_response(comparison_data)


@router.get("/owner/financial-trends")
@require_permission("finance.view_summary")
async def get_owner_financial_trends(
    interval: str = Query("monthly", description="monthly, quarterly, yearly"),
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user)
):
    """Get financial trends across all branches for Owner"""

    from app.repositories import PaymentRepository
    from app.domain.entities.payment import Payment
    from sqlalchemy import func, extract, select
    from app.infrastructure.models.models import Branch

    payment_repo = PaymentRepository()

    # Get all branches
    result = await db.execute(
        select(Branch).where(Branch.organization_id == current_user.organization_id)
    )
    branches = result.scalars().all()
    branch_ids = [b.id for b in branches]

    # Determine date range based on interval
    from datetime import timedelta
    if interval == "monthly":
        months = 12
        date_format = "%Y-%m"
    elif interval == "quarterly":
        months = 24
        date_format = "%Y-Q%q"
    else:  # yearly
        months = 36
        date_format = "%Y"

    trends = []

    for i in range(months):
        # Calculate date for this period
        current_date = datetime.utcnow() - timedelta(days=30 * i)

        if interval == "monthly":
            period_start = current_date.replace(day=1)
            if period_start.month == 12:
                period_end = period_start.replace(year=period_start.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                period_end = period_start.replace(month=period_start.month + 1, day=1) - timedelta(days=1)
            period_label = period_start.strftime("%Y-%m")
        elif interval == "quarterly":
            quarter = (period_start.month - 1) // 3 + 1
            period_start = period_start.replace(month=((quarter - 1) * 3 + 1), day=1)
            if quarter == 4:
                period_end = period_start.replace(year=period_start.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                period_end = period_start.replace(month=(quarter * 3 + 1), day=1) - timedelta(days=1)
            period_label = f"{period_start.year}-Q{quarter}"
        else:  # yearly
            period_start = current_date.replace(month=1, day=1)
            period_end = period_start.replace(year=period_start.year + 1, month=1, day=1) - timedelta(days=1)
            period_label = str(period_start.year)

        # Get payments for this period across all branches
        try:
            result = await db.execute(
                select(func.sum(Payment.amount))
                .where(
                    Payment.organization_id == current_user.organization_id,
                    Payment.payment_date >= period_start,
                    Payment.payment_date <= period_end,
                    Payment.status == "completed"
                )
            )
            amount = result.scalar() or 0
        except:
            amount = 0

        trends.append({
            "period": period_label,
            "amount": float(amount),
            "start_date": period_start.isoformat(),
            "end_date": period_end.isoformat()
        })

    # Reverse to show chronological order
    trends.reverse()

    return success_response({
        "interval": interval,
        "trends": trends
    })


# ==================== ADMIN DASHBOARD ENDPOINTS ====================

@router.get("/branch-summary")
@require_permission("dashboard.view")
async def get_branch_summary(
    branch_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user)
):
    """Get branch summary statistics for Admin"""

    from app.repositories import (
        StudentRepository,
        ClassRepository,
        DebtRepository,
        PaymentRepository,
        AttendanceRepository
    )
    from app.infrastructure.models.models import Branch

    student_repo = StudentRepository()
    class_repo = ClassRepository()
    debt_repo = DebtRepository()
    payment_repo = PaymentRepository()
    attendance_repo = AttendanceRepository()

    # Verify branch access
    result = await db.execute(
        select(Branch).where(Branch.id == branch_id)
    )
    branch = result.scalar_one_or_none()

    if not branch:
        raise HTTPException(status_code=404, detail="Şube bulunamadı")

    # Get counts
    total_students = await student_repo.count(db, {"branch_id": branch_id})
    active_students = await student_repo.count(db, {"branch_id": branch_id, "status": "active"})
    total_classes = await class_repo.count(db, {"branch_id": branch_id})

    # Get financial summary
    try:
        debts = await debt_repo.get_by_branch(db, branch_id)
        total_debt = sum(d.remaining_amount for d in debts if d.remaining_amount > 0)
        pending_debt = sum(d.remaining_amount for d in debts if d.remaining_amount > 0 and d.status == "pending")
        overdue_debt = sum(d.remaining_amount for d in debts if d.remaining_amount > 0 and d.due_date < datetime.utcnow())
    except:
        total_debt = 0
        pending_debt = 0
        overdue_debt = 0

    try:
        payments = await payment_repo.get_by_branch(db, branch_id)
        daily_payments = sum(p.amount for p in payments if p.status == "completed" and p.payment_date and p.payment_date.date() == school_today())
    except:
        daily_payments = 0

    # Get today's attendance
    today = school_today()
    present_today = 0
    absent_today = 0
    excused_today = 0
    late_today = 0

    try:
        for cls in await class_repo.get_active_classes(db, branch_id):
            class_attendance = await attendance_repo.get_by_class_and_date(
                db, cls.id, datetime(today.year, today.month, today.day)
            )
            present_today += len([a for a in class_attendance if a.status == "present"])
            absent_today += len([a for a in class_attendance if a.status == "absent"])
            excused_today += len([a for a in class_attendance if a.status == "excused"])
            late_today += len([a for a in class_attendance if a.status == "late"])
    except:
        pass

    return success_response({
        "branch_id": str(branch_id),
        "branch_name": branch.name,
        "total_students": total_students,
        "active_students": active_students,
        "total_classes": total_classes,
        "present_today": present_today,
        "absent_today": absent_today,
        "excused_today": excused_today,
        "late_today": late_today,
        "attendance_rate": round(present_today / (present_today + absent_today) * 100, 1) if (present_today + absent_today) > 0 else 0,
        "total_debt": float(total_debt),
        "pending_debt": float(pending_debt),
        "overdue_debt": float(overdue_debt),
        "daily_payments": float(daily_payments)
    })


@router.get("/daily-stats")
@require_permission("dashboard.view")
async def get_daily_stats(
    branch_id: UUID,
    date: Optional[date] = None,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import func, cast, String
    from app.infrastructure.models.models import Branch, AttendanceRecord, DailyDevelopmentReport, Student
    branch = (await db.execute(select(Branch).where(Branch.id == branch_id))).scalar_one_or_none()
    if branch is None:
        raise HTTPException(status_code=404, detail="Şube bulunamadı")
    target_date = date or school_today()
    normalized_status = func.upper(cast(AttendanceRecord.status, String))
    rows = (await db.execute(select(normalized_status, func.count()).where(
        AttendanceRecord.branch_id == branch_id, AttendanceRecord.attendance_date == target_date,
        AttendanceRecord.deleted_at.is_(None)).group_by(normalized_status))).all()
    counts = {getattr(status, "value", status): count for status, count in rows}
    total = sum(counts.values())
    meal_rows = (await db.execute(select(DailyDevelopmentReport.meal_status, func.count())
        .join(Student, Student.id == DailyDevelopmentReport.student_id)
        .where(Student.branch_id == branch_id, Student.deleted_at.is_(None),
            DailyDevelopmentReport.date == target_date).group_by(DailyDevelopmentReport.meal_status))).all()
    meals = dict(meal_rows)
    return success_response({"branch_id": str(branch_id), "date": target_date.isoformat(),
        "attendance": {"present": counts.get("PRESENT", 0), "absent": counts.get("ABSENT", 0),
            "excused": counts.get("EXCUSED", 0), "late": counts.get("LATE", 0),
            "half_day": counts.get("HALF_DAY", 0), "total": total,
            "rate": round(counts.get("PRESENT", 0) / total * 100, 1) if total else 0},
        "meals": {"full": meals.get("ALL", 0), "half": meals.get("HALF", 0), "none": meals.get("NONE", 0),
            "total": sum(meals.values())}})


@router.get("/pending-actions")
@require_permission("dashboard.view")
async def get_pending_actions(
    branch_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_tenant_context),
):
    from sqlalchemy import func, or_, cast, String
    from app.domain.entities.health import MedicationSchedule
    from app.infrastructure.models.models import Branch, Debt, Student, OperationalRecord
    from app.application.services.excuse_service import serialize
    branch = (await db.execute(select(Branch).where(Branch.id == branch_id))).scalar_one_or_none()
    if branch is None:
        raise HTTPException(status_code=404, detail="Şube bulunamadı")
    today = school_today()
    medicine_query = select(MedicationSchedule, Student).join(Student, MedicationSchedule.student_id == Student.id).where(
        Student.branch_id == branch_id, Student.deleted_at.is_(None), MedicationSchedule.is_active.is_(True),
        MedicationSchedule.updated_by.is_(None), MedicationSchedule.start_date <= today,
        or_(MedicationSchedule.end_date.is_(None), MedicationSchedule.end_date >= today))
    from app.application.services.infirmary_service import status_expression
    medicine_query = medicine_query.where(status_expression() == "PENDING")
    if not tenant.has_permission("health.read"):
        medicine_query = medicine_query.where(False)
    medicine_count = (await db.execute(medicine_query.with_only_columns(func.count()).order_by(None))).scalar_one()
    medicine_rows = (await db.execute(medicine_query.order_by(MedicationSchedule.created_at.desc()).limit(10))).all()
    medicine = [{"id": str(row.id), "student_id": str(row.student_id),
        "student_name": f"{student.first_name} {student.last_name}", "medicine_name": row.medication_name,
        "dosage": row.dosage, "time_to_give": row.frequency, "created_at": row.created_at.isoformat()}
        for row, student in medicine_rows]
    excuse_query = select(OperationalRecord).where(OperationalRecord.kind == "STUDENT_EXCUSE",
        OperationalRecord.branch_id == branch_id, OperationalRecord.status == "PENDING")
    excuse_count = (await db.execute(excuse_query.with_only_columns(func.count()).select_from(OperationalRecord))).scalar_one()
    excuses = [serialize(row) for row in (await db.execute(excuse_query.order_by(
        OperationalRecord.created_at.desc()).limit(10))).scalars()]
    debt_query = select(Debt).where(Debt.branch_id == branch_id, Debt.deleted_at.is_(None),
        Debt.due_date < today, Debt.amount > Debt.paid_amount)
    debt_count = (await db.execute(debt_query.with_only_columns(func.count()).select_from(Debt))).scalar_one()
    debt_items = debt_query.with_only_columns(cast(Debt.id, String).label("id"),
        cast(Debt.student_id, String).label("student_id"), (Debt.amount - Debt.paid_amount).label("remaining_amount"), Debt.due_date)
    debts = [{"id": str(row.id), "student_id": str(row.student_id), "amount": float(row.remaining_amount),
        "due_date": row.due_date.isoformat(), "days_overdue": (today - row.due_date).days}
        for row in (await db.execute(debt_items.order_by(Debt.due_date).limit(10))).all()]
    return success_response({"branch_id": str(branch_id),
        "medicine_requests": {"count": medicine_count, "items": medicine},
        "excuse_requests": {"count": excuse_count, "items": excuses},
        "overdue_debts": {"count": debt_count, "items": debts},
        "total_pending": medicine_count + excuse_count + debt_count})


class ExcuseReview(BaseModel):
    status: Literal["APPROVED", "REJECTED"]
    comment: str | None = Field(None, max_length=2000)


@router.put("/excuse-requests/{request_id}")
async def review_excuse_request(
    request_id: UUID,
    body: ExcuseReview,
    tenant: TenantContext = Depends(PermissionChecker("students.write")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    from app.application.services import excuse_service
    return success_response(await excuse_service.review(db, tenant, request_id, body.status, body.comment),
        "Mazeret talebi değerlendirildi")
