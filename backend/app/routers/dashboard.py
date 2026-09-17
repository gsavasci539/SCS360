from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from datetime import datetime, date

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
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("dashboard.view"))
):
    """Get dashboard summary statistics"""
    
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
    active_students = await student_repo.count(db, {"organization_id": tenant.organization_id, "status": "active"})
    total_classes = await class_repo.count(db, {"organization_id": tenant.organization_id})
    
    # Get financial summary
    try:
        debts = await debt_repo.get_by_organization(db, tenant.organization_id)
        total_debt = sum(d.remaining_amount for d in debts if d.remaining_amount > 0)
        pending_debt = sum(d.remaining_amount for d in debts if d.remaining_amount > 0 and d.status == "pending")
        overdue_debt = sum(d.remaining_amount for d in debts if d.remaining_amount > 0 and d.due_date < datetime.utcnow())
    except:
        total_debt = 0
        pending_debt = 0
        overdue_debt = 0
    
    try:
        payments = await payment_repo.get_by_organization(db, tenant.organization_id)
        monthly_payments = sum(p.amount for p in payments if p.status == "completed" and p.payment_date and p.payment_date.month == datetime.utcnow().month)
    except:
        monthly_payments = 0
    
    # Get today's attendance
    today = datetime.utcnow().date()
    absent_today = 0
    try:
        for cls in await class_repo.get_active_classes(db, tenant.organization_id):
            class_attendance = await attendance_repo.get_by_class_and_date(
                db, cls.id, datetime(today.year, today.month, today.day)
            )
            absent_today += len([a for a in class_attendance if a.status == "absent"])
    except:
        pass
    
    return success_response({
        "total_students": total_students,
        "active_students": active_students,
        "total_branches": 1,  # Placeholder
        "total_classes": total_classes,
        "absent_today": absent_today,
        "monthly_payments": monthly_payments,
        "pending_debt": pending_debt,
        "overdue_debt": overdue_debt
    })


@router.get("/charts")
async def get_dashboard_charts(
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("dashboard.view"))
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
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("dashboard.view"))
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
    today = datetime.utcnow().date()
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
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
                Announcement.status == "scheduled",
                Announcement.scheduled_for >= datetime.utcnow()
            )
        )
        .order_by(Announcement.scheduled_for)
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
                Debt.remaining_amount > 0
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
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
        today = datetime.utcnow().date()
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
    db: AsyncSession = Depends(get_db),
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
        thirty_days_ago = datetime.utcnow().date() - timedelta(days=30)
        
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
                    db, cls.id, thirty_days_ago, datetime.utcnow().date()
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
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
        daily_payments = sum(p.amount for p in payments if p.status == "completed" and p.payment_date and p.payment_date.date() == datetime.utcnow().date())
    except:
        daily_payments = 0

    # Get today's attendance
    today = datetime.utcnow().date()
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get daily statistics for Admin"""

    from app.repositories import (
        StudentRepository,
        ClassRepository,
        AttendanceRepository,
        DailyDevelopmentReport
    )
    from app.infrastructure.models.models import Branch

    student_repo = StudentRepository()
    class_repo = ClassRepository()
    attendance_repo = AttendanceRepository()

    # Verify branch access
    result = await db.execute(
        select(Branch).where(Branch.id == branch_id)
    )
    branch = result.scalar_one_or_none()

    if not branch:
        raise HTTPException(status_code=404, detail="Şube bulunamadı")

    target_date = date or datetime.utcnow().date()

    # Get attendance stats
    present_count = 0
    absent_count = 0
    excused_count = 0
    late_count = 0

    try:
        for cls in await class_repo.get_active_classes(db, branch_id):
            class_attendance = await attendance_repo.get_by_class_and_date(
                db, cls.id, datetime(target_date.year, target_date.month, target_date.day)
            )
            present_count += len([a for a in class_attendance if a.status == "present"])
            absent_count += len([a for a in class_attendance if a.status == "absent"])
            excused_count += len([a for a in class_attendance if a.status == "excused"])
            late_count += len([a for a in class_attendance if a.status == "late"])
    except:
        pass

    # Get meal stats from daily reports
    meal_full = 0
    meal_half = 0
    meal_none = 0

    try:
        from app.infrastructure.models.models import DailyDevelopmentReport as DailyReport
        report_result = await db.execute(
            select(DailyReport).where(DailyReport.date == target_date)
        )
        reports = report_result.scalars().all()

        for report in reports:
            if report.meal_status == "ALL":
                meal_full += 1
            elif report.meal_status == "HALF":
                meal_half += 1
            elif report.meal_status == "NONE":
                meal_none += 1
    except:
        pass

    return success_response({
        "branch_id": str(branch_id),
        "date": target_date.isoformat(),
        "attendance": {
            "present": present_count,
            "absent": absent_count,
            "excused": excused_count,
            "late": late_count,
            "total": present_count + absent_count + excused_count + late_count,
            "rate": round(present_count / (present_count + absent_count + excused_count + late_count) * 100, 1) if (present_count + absent_count + excused_count + late_count) > 0 else 0
        },
        "meals": {
            "full": meal_full,
            "half": meal_half,
            "none": meal_none,
            "total": meal_full + meal_half + meal_none
        }
    })


@router.get("/pending-actions")
@require_permission("dashboard.view")
async def get_pending_actions(
    branch_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get pending actions for Admin"""

    from app.infrastructure.models.models import Branch, MedicineRequest, ExcuseRequest, Debt

    # Verify branch access
    result = await db.execute(
        select(Branch).where(Branch.id == branch_id)
    )
    branch = result.scalar_one_or_none()

    if not branch:
        raise HTTPException(status_code=404, detail="Şube bulunamadı")

    # Get pending medicine requests
    medicine_requests = []
    try:
        result = await db.execute(
            select(MedicineRequest).where(
                MedicineRequest.status == "PENDING"
            ).limit(10)
        )
        for req in result.scalars().all():
            medicine_requests.append({
                "id": str(req.id),
                "student_id": str(req.student_id),
                "medicine_name": req.medicine_name,
                "dosage": req.dosage,
                "time_to_give": req.time_to_give,
                "created_at": req.created_at.isoformat()
            })
    except:
        pass

    # Get pending excuse requests
    excuse_requests = []
    try:
        result = await db.execute(
            select(ExcuseRequest).where(
                ExcuseRequest.status == "PENDING"
            ).limit(10)
        )
        for req in result.scalars().all():
            excuse_requests.append({
                "id": str(req.id),
                "student_id": str(req.student_id),
                "start_date": req.start_date.isoformat(),
                "end_date": req.end_date.isoformat(),
                "reason_type": req.reason_type,
                "created_at": req.created_at.isoformat()
            })
    except:
        pass

    # Get overdue debts
    overdue_debts = []
    try:
        result = await db.execute(
            select(Debt).where(
                Debt.due_date < datetime.utcnow().date(),
                Debt.remaining_amount > 0
            ).limit(10)
        )
        for debt in result.scalars().all():
            overdue_debts.append({
                "id": str(debt.id),
                "student_id": str(debt.student_id),
                "amount": float(debt.remaining_amount),
                "due_date": debt.due_date.isoformat(),
                "days_overdue": (datetime.utcnow().date() - debt.due_date).days
            })
    except:
        pass

    return success_response({
        "branch_id": str(branch_id),
        "medicine_requests": {
            "count": len(medicine_requests),
            "items": medicine_requests
        },
        "excuse_requests": {
            "count": len(excuse_requests),
            "items": excuse_requests
        },
        "overdue_debts": {
            "count": len(overdue_debts),
            "items": overdue_debts
        },
        "total_pending": len(medicine_requests) + len(excuse_requests) + len(overdue_debts)
    })
