from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.schemas.common import AnnouncementCreate
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import ForbiddenException, NotFoundException, ValidationException
from app.core.permissions import PermissionChecker
from app.core.responses import success_response
from app.core.tenant import TenantContext
from app.infrastructure.models.models import (
    Announcement,
    AnnouncementAudience,
    AnnouncementStatus,
    AppSetting,
    AttendanceRecord,
    AttendanceStatus,
    Branch,
    ClassRoom,
    Debt,
    DebtStatus,
    IntegrationSetting,
    MessageTemplate,
    NotificationChannel,
    NotificationJob,
    NotificationRecipient,
    NotificationStatus,
    Parent,
    Payment,
    Student,
    StudentParent,
    StudentStatus,
    User,
)
from app.infrastructure.repositories.base import BaseRepository

router = APIRouter(tags=["Dashboard & Reports"])


@router.get("/api/dashboard/summary")
async def dashboard_summary(
    tenant: TenantContext = Depends(PermissionChecker("dashboard.read")),
    db: AsyncSession = Depends(get_db),
):
    today = date.today()
    month_start = today.replace(day=1)

    student_q = select(func.count()).select_from(Student).where(Student.deleted_at.is_(None))
    active_student_q = student_q.where(Student.status == StudentStatus.ACTIVE)
    branch_q = (
        select(func.count())
        .select_from(Branch)
        .where(Branch.deleted_at.is_(None), Branch.is_active.is_(True))
    )
    class_q = (
        select(func.count())
        .select_from(ClassRoom)
        .where(ClassRoom.deleted_at.is_(None), ClassRoom.is_active.is_(True))
    )
    absent_q = (
        select(func.count())
        .select_from(AttendanceRecord)
        .where(
            AttendanceRecord.attendance_date == today,
            AttendanceRecord.status == AttendanceStatus.ABSENT,
            AttendanceRecord.deleted_at.is_(None),
        )
    )
    payment_q = select(func.coalesce(func.sum(Payment.amount), 0)).where(
        Payment.payment_date
        >= datetime.combine(month_start, datetime.min.time()).replace(tzinfo=UTC),
        Payment.cancelled_at.is_(None),
    )
    debt_q = select(func.coalesce(func.sum(Debt.amount - Debt.paid_amount), 0)).where(
        Debt.deleted_at.is_(None),
        Debt.status.in_([DebtStatus.UNPAID, DebtStatus.PARTIALLY_PAID, DebtStatus.OVERDUE]),
    )
    overdue_q = select(func.coalesce(func.sum(Debt.amount - Debt.paid_amount), 0)).where(
        Debt.status == DebtStatus.OVERDUE,
        Debt.deleted_at.is_(None),
    )

    if not tenant.is_super_admin and tenant.organization_id:
        student_q = student_q.where(Student.organization_id == tenant.organization_id)
        active_student_q = active_student_q.where(Student.organization_id == tenant.organization_id)
        branch_q = branch_q.where(Branch.organization_id == tenant.organization_id)
        class_q = class_q.where(ClassRoom.organization_id == tenant.organization_id)
        absent_q = absent_q.where(AttendanceRecord.organization_id == tenant.organization_id)
        payment_q = payment_q.where(Payment.organization_id == tenant.organization_id)
        debt_q = debt_q.where(Debt.organization_id == tenant.organization_id)
        overdue_q = overdue_q.where(Debt.organization_id == tenant.organization_id)
    if tenant.branch_ids:
        student_q = student_q.where(Student.branch_id.in_(tenant.branch_ids))
        active_student_q = active_student_q.where(Student.branch_id.in_(tenant.branch_ids))
        branch_q = branch_q.where(Branch.id.in_(tenant.branch_ids))
        class_q = class_q.where(ClassRoom.branch_id.in_(tenant.branch_ids))
        absent_q = absent_q.where(AttendanceRecord.branch_id.in_(tenant.branch_ids))
        payment_q = payment_q.where(Payment.branch_id.in_(tenant.branch_ids))
        debt_q = debt_q.where(Debt.branch_id.in_(tenant.branch_ids))
        overdue_q = overdue_q.where(Debt.branch_id.in_(tenant.branch_ids))

    return success_response(
        {
            "total_students": (await db.execute(student_q)).scalar() or 0,
            "active_students": (await db.execute(active_student_q)).scalar() or 0,
            "total_branches": (await db.execute(branch_q)).scalar() or 0,
            "total_classes": (await db.execute(class_q)).scalar() or 0,
            "today_absent": (await db.execute(absent_q)).scalar() or 0,
            "monthly_collection": str((await db.execute(payment_q)).scalar() or 0),
            "pending_debt": str((await db.execute(debt_q)).scalar() or 0),
            "overdue_debt": str((await db.execute(overdue_q)).scalar() or 0),
        }
    )


@router.get("/api/dashboard/charts")
async def dashboard_charts(
    tenant: TenantContext = Depends(PermissionChecker("dashboard.read")),
    db: AsyncSession = Depends(get_db),
):
    repo = BaseRepository(db, tenant)
    classes_query = select(ClassRoom).where(ClassRoom.deleted_at.is_(None))
    classes_query = repo._org_filter(classes_query, ClassRoom)
    classes_query = repo._branch_filter(classes_query, ClassRoom)
    classes = (await db.execute(classes_query.limit(10))).scalars().all()
    occupancy = []
    for c in classes:
        count = (
            await db.execute(
                select(func.count())
                .select_from(Student)
                .where(Student.class_id == c.id, Student.deleted_at.is_(None))
            )
        ).scalar() or 0
        occupancy.append({"name": c.name, "count": count, "capacity": c.capacity})

    month_start = date.today().replace(day=1)
    collection_query = select(func.coalesce(func.sum(Payment.amount), 0)).where(
        Payment.payment_date
        >= datetime.combine(month_start, datetime.min.time()).replace(tzinfo=UTC),
        Payment.cancelled_at.is_(None),
    )
    collection_query = repo._org_filter(collection_query, Payment)
    collection_query = repo._branch_filter(collection_query, Payment)
    collection = (await db.execute(collection_query)).scalar() or 0
    pending_query = select(func.coalesce(func.sum(Debt.amount - Debt.paid_amount), 0)).where(
        Debt.deleted_at.is_(None),
        Debt.status.in_([DebtStatus.UNPAID, DebtStatus.PARTIALLY_PAID, DebtStatus.OVERDUE]),
    )
    pending_query = repo._org_filter(pending_query, Debt)
    pending_query = repo._branch_filter(pending_query, Debt)
    pending = (await db.execute(pending_query)).scalar() or 0

    return success_response(
        {
            "class_occupancy": occupancy,
            "monthly_income": [
                {"month": date.today().strftime("%Y-%m"), "amount": str(collection)}
            ],
            "debt_vs_collection": {"debt": str(pending), "collection": str(collection)},
        }
    )


@router.get("/api/reports/monthly-payments")
async def monthly_payments_report(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    branch_id: UUID | None = None,
    tenant: TenantContext = Depends(PermissionChecker("report.read")),
    db: AsyncSession = Depends(get_db),
):
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    query = (
        select(
            Branch.id,
            Branch.name,
            func.coalesce(func.sum(Payment.amount), 0),
            func.count(Payment.id),
        )
        .join(Branch, Branch.id == Payment.branch_id)
        .where(
            func.date(Payment.payment_date) >= start,
            func.date(Payment.payment_date) < end,
            Payment.cancelled_at.is_(None),
        )
        .group_by(Branch.id, Branch.name)
    )
    if branch_id:
        query = query.where(Payment.branch_id == branch_id)
    if not tenant.is_super_admin and tenant.organization_id:
        query = query.where(Payment.organization_id == tenant.organization_id)
    if tenant.branch_ids:
        query = query.where(Payment.branch_id.in_(tenant.branch_ids))

    rows = (await db.execute(query)).all()
    return success_response(
        [
            {
                "month": f"{year}-{month:02d}",
                "year": str(year),
                "branch_id": str(row[0]),
                "branch_name": row[1],
                "total_amount": str(row[2]),
                "payment_count": row[3],
            }
            for row in rows
        ]
    )


@router.get("/api/reports/debts")
async def debts_report(
    start_date: date | None = None,
    end_date: date | None = None,
    branch_id: UUID | None = None,
    status: DebtStatus | None = None,
    type: str | None = None,
    tenant: TenantContext = Depends(PermissionChecker("report.read")),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Debt, Student, Branch)
        .join(Student, Student.id == Debt.student_id)
        .join(Branch, Branch.id == Debt.branch_id)
        .where(Debt.deleted_at.is_(None), Student.deleted_at.is_(None))
        .order_by(Debt.due_date.desc())
    )
    if start_date:
        query = query.where(Debt.due_date >= start_date)
    if end_date:
        query = query.where(Debt.due_date <= end_date)
    if branch_id:
        query = query.where(Debt.branch_id == branch_id)
    if status:
        query = query.where(Debt.status == status)
    if type:
        query = query.where(Debt.debt_type == type.upper())
    if not tenant.is_super_admin and tenant.organization_id:
        query = query.where(Debt.organization_id == tenant.organization_id)
    if tenant.branch_ids:
        query = query.where(Debt.branch_id.in_(tenant.branch_ids))

    rows = (await db.execute(query)).all()
    return success_response(
        [
            {
                "id": str(debt.id),
                "student_id": str(student.id),
                "student_name": f"{student.first_name} {student.last_name}",
                "branch_name": branch.name,
                "debt_type": debt.debt_type.value,
                "type": debt.debt_type.value,
                "description": debt.description,
                "amount": str(debt.amount),
                "paid_amount": str(debt.paid_amount),
                "remaining_amount": str(debt.remaining_amount),
                "due_date": debt.due_date.isoformat(),
                "status": debt.status.value,
            }
            for debt, student, branch in rows
        ]
    )


@router.get("/api/reports/overdue-debts")
async def overdue_debts_report(
    days_overdue: int = Query(0, ge=0),
    branch_id: UUID | None = None,
    tenant: TenantContext = Depends(PermissionChecker("report.read")),
    db: AsyncSession = Depends(get_db),
):
    cutoff = date.today() - timedelta(days=days_overdue)
    query = (
        select(Debt, Student, Branch)
        .join(Student, Student.id == Debt.student_id)
        .join(Branch, Branch.id == Debt.branch_id)
        .where(
            Debt.due_date <= cutoff,
            Debt.status.in_([DebtStatus.UNPAID, DebtStatus.PARTIALLY_PAID, DebtStatus.OVERDUE]),
            Debt.deleted_at.is_(None),
            Student.deleted_at.is_(None),
        )
        .order_by(Debt.due_date)
    )
    if branch_id:
        query = query.where(Debt.branch_id == branch_id)
    if not tenant.is_super_admin and tenant.organization_id:
        query = query.where(Debt.organization_id == tenant.organization_id)
    if tenant.branch_ids:
        query = query.where(Debt.branch_id.in_(tenant.branch_ids))

    rows = (await db.execute(query)).all()
    data = []
    for debt, student, branch in rows:
        parent = (
            await db.execute(
                select(Parent)
                .join(StudentParent, StudentParent.parent_id == Parent.id)
                .where(StudentParent.student_id == student.id, Parent.deleted_at.is_(None))
                .order_by(StudentParent.is_primary.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        data.append(
            {
                "id": str(debt.id),
                "student_id": str(student.id),
                "student_name": f"{student.first_name} {student.last_name}",
                "branch_name": branch.name,
                "amount": str(debt.amount),
                "remaining_amount": str(debt.remaining_amount),
                "remaining": str(debt.remaining_amount),
                "due_date": debt.due_date.isoformat(),
                "days_overdue": (date.today() - debt.due_date).days,
                "parent_phone": (parent.sms_phone or parent.phone) if parent else None,
                "parent_email": parent.email if parent else None,
            }
        )
    return success_response(data)


@router.post("/api/reports/overdue-debts/remind")
async def remind_overdue_debts(
    body: dict,
    tenant: TenantContext = Depends(PermissionChecker("notification.write")),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    raw_ids = body.get("debt_ids", [])
    debt_ids = [UUID(str(value)) for value in raw_ids]
    if not debt_ids:
        return success_response(
            {"jobs_created": 0, "recipients": 0}, "Hatırlatılacak borç bulunamadı"
        )

    query = (
        select(Debt, Student, Parent)
        .join(Student, Student.id == Debt.student_id)
        .join(StudentParent, StudentParent.student_id == Student.id)
        .join(Parent, Parent.id == StudentParent.parent_id)
        .where(
            Debt.id.in_(debt_ids),
            Debt.deleted_at.is_(None),
            Parent.deleted_at.is_(None),
            Parent.receive_notifications.is_(True),
        )
        .order_by(StudentParent.is_primary.desc())
    )
    if not tenant.is_super_admin and tenant.organization_id:
        query = query.where(Debt.organization_id == tenant.organization_id)
    if tenant.branch_ids:
        query = query.where(Debt.branch_id.in_(tenant.branch_ids))

    rows = (await db.execute(query)).all()
    seen_debts: set[UUID] = set()
    jobs_created = 0
    for debt, student, parent in rows:
        if debt.id in seen_debts:
            continue
        address = parent.sms_phone or parent.phone
        if not address:
            continue
        seen_debts.add(debt.id)
        job = NotificationJob(
            organization_id=debt.organization_id,
            branch_id=debt.branch_id,
            channel=NotificationChannel.SMS,
            subject="Gecikmiş ödeme hatırlatması",
            body=(
                f"{student.first_name} {student.last_name} için "
                f"{debt.remaining_amount} TL tutarındaki ödemenin vadesi "
                f"{debt.due_date.isoformat()} tarihinde dolmuştur."
            ),
            reference_type="debt",
            reference_id=debt.id,
            created_by=user.id,
        )
        db.add(job)
        await db.flush()
        db.add(
            NotificationRecipient(
                notification_job_id=job.id,
                parent_id=parent.id,
                recipient_name=f"{parent.first_name} {parent.last_name}",
                recipient_address=address,
            )
        )
        jobs_created += 1

    return success_response(
        {"jobs_created": jobs_created, "recipients": jobs_created},
        "Borç hatırlatmaları kuyruğa alındı",
    )


@router.get("/api/reports/class-occupancy")
async def class_occupancy_report(
    branch_id: UUID | None = None,
    academic_year: str | None = None,
    tenant: TenantContext = Depends(PermissionChecker("report.read")),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(ClassRoom, Branch)
        .join(Branch, Branch.id == ClassRoom.branch_id)
        .where(ClassRoom.deleted_at.is_(None), Branch.deleted_at.is_(None))
    )
    if branch_id:
        query = query.where(ClassRoom.branch_id == branch_id)
    if academic_year:
        query = query.where(ClassRoom.academic_year == academic_year)
    if not tenant.is_super_admin and tenant.organization_id:
        query = query.where(ClassRoom.organization_id == tenant.organization_id)
    if tenant.branch_ids:
        query = query.where(ClassRoom.branch_id.in_(tenant.branch_ids))
    classes = (await db.execute(query)).all()
    data = []
    for c, branch in classes:
        count = (
            await db.execute(
                select(func.count())
                .select_from(Student)
                .where(Student.class_id == c.id, Student.deleted_at.is_(None))
            )
        ).scalar() or 0
        data.append(
            {
                "id": str(c.id),
                "class_name": c.name,
                "class_code": c.code,
                "branch_name": branch.name,
                "capacity": c.capacity,
                "count": count,
                "rate": round((count / c.capacity) * 100, 2) if c.capacity else 0,
                "student_count": count,
                "occupancy_rate": round((count / c.capacity) * 100, 2) if c.capacity else 0,
                "academic_year": c.academic_year,
            }
        )
    return success_response(data)


@router.get("/api/reports/branch-performance")
async def branch_performance_report(
    start_date: date | None = None,
    end_date: date | None = None,
    tenant: TenantContext = Depends(PermissionChecker("report.read")),
    db: AsyncSession = Depends(get_db),
):
    query = select(Branch).where(Branch.deleted_at.is_(None))
    if not tenant.is_super_admin and tenant.organization_id:
        query = query.where(Branch.organization_id == tenant.organization_id)
    if tenant.branch_ids:
        query = query.where(Branch.id.in_(tenant.branch_ids))
    branches = (await db.execute(query)).scalars().all()
    data = []
    for b in branches:
        students = (
            await db.execute(
                select(func.count())
                .select_from(Student)
                .where(Student.branch_id == b.id, Student.deleted_at.is_(None))
            )
        ).scalar() or 0
        payment_q = select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.branch_id == b.id, Payment.cancelled_at.is_(None)
        )
        new_students_q = (
            select(func.count())
            .select_from(Student)
            .where(Student.branch_id == b.id, Student.deleted_at.is_(None))
        )
        attendance_q = select(
            func.count().filter(AttendanceRecord.status == AttendanceStatus.PRESENT),
            func.count(AttendanceRecord.id),
        ).where(AttendanceRecord.branch_id == b.id, AttendanceRecord.deleted_at.is_(None))
        if start_date:
            payment_q = payment_q.where(func.date(Payment.payment_date) >= start_date)
            new_students_q = new_students_q.where(Student.enrollment_date >= start_date)
            attendance_q = attendance_q.where(AttendanceRecord.attendance_date >= start_date)
        if end_date:
            payment_q = payment_q.where(func.date(Payment.payment_date) <= end_date)
            new_students_q = new_students_q.where(Student.enrollment_date <= end_date)
            attendance_q = attendance_q.where(AttendanceRecord.attendance_date <= end_date)
        collection = (await db.execute(payment_q)).scalar() or 0
        new_students = (await db.execute(new_students_q)).scalar() or 0
        present, attendance_total = (await db.execute(attendance_q)).one()
        attendance_rate = round((present / attendance_total) * 100, 2) if attendance_total else 0
        data.append(
            {
                "branch_id": str(b.id),
                "branch_name": b.name,
                "branch": b.name,
                "total_students": students,
                "students": students,
                "new_students": new_students,
                "total_revenue": str(collection),
                "collection": str(collection),
                "attendance_rate": attendance_rate,
                "period_start": start_date.isoformat() if start_date else None,
                "period_end": end_date.isoformat() if end_date else None,
            }
        )
    return success_response(data)


@router.get("/api/reports/export/csv")
async def export_csv(
    report_type: str = Query("debts"),
    tenant: TenantContext = Depends(PermissionChecker("report.read")),
    db: AsyncSession = Depends(get_db),
):
    from app.infrastructure.reports.csv_export import export_debts_csv

    if report_type == "debts":
        query = select(Debt).where(Debt.deleted_at.is_(None))
        repo = BaseRepository(db, tenant)
        query = repo._org_filter(query, Debt)
        query = repo._branch_filter(query, Debt)
        result = await db.execute(query)
        csv_content = export_debts_csv(result.scalars().all())
        return success_response({"content": csv_content, "filename": "debts.csv"})
    return success_response({"content": "", "filename": "report.csv"})


@router.get("/api/reports/attendance")
async def attendance_report(
    year: int | None = None,
    month: int | None = Query(None, ge=1, le=12),
    start_date: date | None = None,
    end_date: date | None = None,
    class_id: UUID | None = None,
    student_id: UUID | None = None,
    tenant: TenantContext = Depends(PermissionChecker("report.read")),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(AttendanceRecord, Student, ClassRoom, Branch)
        .join(Student, Student.id == AttendanceRecord.student_id)
        .join(ClassRoom, ClassRoom.id == AttendanceRecord.class_id)
        .join(Branch, Branch.id == AttendanceRecord.branch_id)
        .where(AttendanceRecord.deleted_at.is_(None))
        .order_by(AttendanceRecord.attendance_date.desc(), Student.first_name, Student.last_name)
    )
    if year and month:
        period_start = date(year, month, 1)
        period_end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
        query = query.where(
            AttendanceRecord.attendance_date >= period_start,
            AttendanceRecord.attendance_date < period_end,
        )
    if start_date:
        query = query.where(AttendanceRecord.attendance_date >= start_date)
    if end_date:
        query = query.where(AttendanceRecord.attendance_date <= end_date)
    if class_id:
        query = query.where(AttendanceRecord.class_id == class_id)
    if student_id:
        query = query.where(AttendanceRecord.student_id == student_id)
    if not tenant.is_super_admin and tenant.organization_id:
        query = query.where(AttendanceRecord.organization_id == tenant.organization_id)
    if tenant.branch_ids:
        query = query.where(AttendanceRecord.branch_id.in_(tenant.branch_ids))
    rows = (await db.execute(query)).all()
    return success_response(
        [
            {
                "id": str(record.id),
                "date": record.attendance_date.isoformat(),
                "student_id": str(student.id),
                "student_name": f"{student.first_name} {student.last_name}",
                "class_name": class_room.name,
                "branch_name": branch.name,
                "status": record.status.value,
                "check_in_time": record.check_in_time.isoformat() if record.check_in_time else None,
                "notes": record.notes,
            }
            for record, student, class_room, branch in rows
        ]
    )


@router.get("/api/reports/export/excel")
async def export_excel(
    report_type: str = Query("debts"),
    tenant: TenantContext = Depends(PermissionChecker("report.read")),
    db: AsyncSession = Depends(get_db),
):
    from app.infrastructure.reports.excel_export import export_debts_excel

    if report_type == "debts":
        query = select(Debt).where(Debt.deleted_at.is_(None))
        repo = BaseRepository(db, tenant)
        query = repo._org_filter(query, Debt)
        query = repo._branch_filter(query, Debt)
        result = await db.execute(query)
        excel_bytes = export_debts_excel(result.scalars().all())
        import base64

        return success_response(
            {
                "content": base64.b64encode(excel_bytes).decode(),
                "filename": "debts.xlsx",
                "encoding": "base64",
            }
        )
    return success_response({"content": "", "filename": "report.xlsx"})


@router.get("/api/announcements/{announcement_id}")
async def get_announcement(
    announcement_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("announcement.read")),
    db: AsyncSession = Depends(get_db),
):
    announcement = await BaseRepository(db, tenant).get_by_id(announcement_id, Announcement)
    jobs = (
        (
            await db.execute(
                select(NotificationJob).where(
                    NotificationJob.reference_type == "announcement",
                    NotificationJob.reference_id == announcement.id,
                )
            )
        )
        .scalars()
        .all()
    )
    job_ids = [job.id for job in jobs]
    recipients = []
    if job_ids:
        recipients = (
            (
                await db.execute(
                    select(NotificationRecipient).where(
                        NotificationRecipient.notification_job_id.in_(job_ids)
                    )
                )
            )
            .scalars()
            .all()
        )
    return success_response(
        {
            "id": str(announcement.id),
            "title": announcement.title,
            "content": announcement.content,
            "audience": announcement.audience.value,
            "channels": announcement.channels,
            "status": announcement.status.value,
            "scheduled_at": (
                announcement.scheduled_at.isoformat() if announcement.scheduled_at else None
            ),
            "sent_at": announcement.sent_at.isoformat() if announcement.sent_at else None,
            "recipient_count": len(recipients),
            "sent_count": sum(r.status == NotificationStatus.SENT for r in recipients),
            "failed_count": sum(r.status == NotificationStatus.FAILED for r in recipients),
            "created_at": announcement.created_at.isoformat(),
        }
    )


@router.get("/api/announcements/{announcement_id}/results")
async def announcement_results(
    announcement_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("announcement.read")),
    db: AsyncSession = Depends(get_db),
):
    await BaseRepository(db, tenant).get_by_id(announcement_id, Announcement)
    jobs = (
        (
            await db.execute(
                select(NotificationJob).where(
                    NotificationJob.reference_type == "announcement",
                    NotificationJob.reference_id == announcement_id,
                )
            )
        )
        .scalars()
        .all()
    )
    results = []
    for job in jobs:
        job_recipients = (
            (
                await db.execute(
                    select(NotificationRecipient).where(
                        NotificationRecipient.notification_job_id == job.id
                    )
                )
            )
            .scalars()
            .all()
        )
        results.append(
            {
                "channel": job.channel.value,
                "sent": sum(r.status == NotificationStatus.SENT for r in job_recipients),
                "failed": sum(r.status == NotificationStatus.FAILED for r in job_recipients),
                "pending": sum(r.status == NotificationStatus.PENDING for r in job_recipients),
                "error": next((r.error_message for r in job_recipients if r.error_message), None),
            }
        )
    return success_response(results)


@router.post("/api/announcements/{announcement_id}/retry")
async def retry_announcement(
    announcement_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("announcement.write")),
    db: AsyncSession = Depends(get_db),
):
    await BaseRepository(db, tenant).get_by_id(announcement_id, Announcement)
    jobs = (
        (
            await db.execute(
                select(NotificationJob).where(
                    NotificationJob.reference_type == "announcement",
                    NotificationJob.reference_id == announcement_id,
                )
            )
        )
        .scalars()
        .all()
    )
    retried = 0
    for job in jobs:
        failed = (
            (
                await db.execute(
                    select(NotificationRecipient).where(
                        NotificationRecipient.notification_job_id == job.id,
                        NotificationRecipient.status == NotificationStatus.FAILED,
                    )
                )
            )
            .scalars()
            .all()
        )
        if not failed:
            continue
        for recipient in failed:
            recipient.status = NotificationStatus.PENDING
            recipient.error_message = None
            recipient.provider_response = None
            retried += 1
        job.status = NotificationStatus.PENDING
        job.processed_at = None
    return success_response(
        {"recipients_retried": retried}, "Başarısız gönderimler yeniden kuyruğa alındı"
    )


@router.put("/api/announcements/{announcement_id}")
async def update_announcement(
    announcement_id: UUID,
    body: AnnouncementCreate,
    tenant: TenantContext = Depends(PermissionChecker("announcement.write")),
    db: AsyncSession = Depends(get_db),
):
    announcement = await BaseRepository(db, tenant).get_by_id(announcement_id, Announcement)
    if announcement.status == AnnouncementStatus.SENT:
        from app.core.exceptions import ValidationException

        raise ValidationException("Gönderilmiş duyuru düzenlenemez")
    announcement.title = body.title
    announcement.content = body.content
    announcement.audience = AnnouncementAudience(body.audience)
    announcement.channels = body.channels
    return success_response(message="Duyuru güncellendi")


@router.delete("/api/announcements/{announcement_id}")
async def delete_announcement(
    announcement_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("announcement.write")),
    db: AsyncSession = Depends(get_db),
):
    announcement = await BaseRepository(db, tenant).get_by_id(announcement_id, Announcement)
    announcement.deleted_at = datetime.now(UTC)
    return success_response(message="Duyuru silindi")


@router.post("/api/notifications/send")
async def send_notification(
    body: dict,
    tenant: TenantContext = Depends(PermissionChecker("notification.write")),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    channel = body.get("channel", "EMAIL")
    job = NotificationJob(
        organization_id=tenant.organization_id,
        branch_id=UUID(body["branch_id"]) if body.get("branch_id") else None,
        channel=NotificationChannel(channel),
        subject=body.get("subject", ""),
        body=body.get("body", ""),
        created_by=user.id,
    )
    db.add(job)
    await db.flush()
    for recipient in body.get("recipients", []):
        db.add(
            NotificationRecipient(
                notification_job_id=job.id,
                recipient_name=recipient.get("name", ""),
                recipient_address=recipient["address"],
            )
        )
    return success_response({"id": str(job.id)}, "Bildirim kuyruğa alındı")


@router.post("/api/notifications/templates")
async def create_template(
    body: dict,
    tenant: TenantContext = Depends(PermissionChecker("notification.write")),
    db: AsyncSession = Depends(get_db),
):
    template = MessageTemplate(
        organization_id=tenant.organization_id,
        code=body["code"],
        name=body["name"],
        channel=NotificationChannel(body["channel"]),
        subject=body.get("subject"),
        body_template=body["body_template"],
    )
    db.add(template)
    await db.flush()
    return success_response({"id": str(template.id)}, "Şablon oluşturuldu")


@router.put("/api/notifications/templates/{template_id}")
async def update_template(
    template_id: UUID,
    body: dict,
    tenant: TenantContext = Depends(PermissionChecker("notification.write")),
    db: AsyncSession = Depends(get_db),
):
    query = select(MessageTemplate).where(
        MessageTemplate.id == template_id,
        MessageTemplate.deleted_at.is_(None),
    )
    if not tenant.is_super_admin:
        query = query.where(MessageTemplate.organization_id == tenant.organization_id)
    template = (await db.execute(query)).scalar_one_or_none()
    if not template:
        raise NotFoundException()
    for key in ("name", "subject", "body_template", "is_active"):
        if key in body:
            setattr(template, key, body[key])
    return success_response(message="Şablon güncellendi")


@router.get("/api/notifications/templates/{template_id}")
async def get_template(
    template_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("notification.read")),
    db: AsyncSession = Depends(get_db),
):
    template = (
        await db.execute(
            select(MessageTemplate).where(
                MessageTemplate.id == template_id,
                MessageTemplate.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if not template:
        raise NotFoundException()
    if (
        not tenant.is_super_admin
        and template.organization_id is not None
        and template.organization_id != tenant.organization_id
    ):
        raise NotFoundException()
    return success_response(
        {
            "id": str(template.id),
            "code": template.code,
            "name": template.name,
            "channel": template.channel.value,
            "subject": template.subject,
            "body_template": template.body_template,
            "is_active": template.is_active,
        }
    )


@router.put("/api/settings/integrations")
async def update_integrations(
    body: dict,
    tenant: TenantContext = Depends(PermissionChecker("settings.write")),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.infrastructure.models.models import IntegrationProvider

    provider = body.get("provider")
    config = body.get("config", {})
    result = await db.execute(
        select(IntegrationSetting).where(
            IntegrationSetting.organization_id == tenant.organization_id,
            IntegrationSetting.provider == IntegrationProvider(provider),
        )
    )
    integration = result.scalar_one_or_none()
    if integration:
        integration.config = config
        integration.is_active = body.get("is_active", True)
        integration.updated_by = user.id
    else:
        db.add(
            IntegrationSetting(
                organization_id=tenant.organization_id,
                provider=IntegrationProvider(provider),
                config=config,
                is_active=body.get("is_active", True),
                updated_by=user.id,
            )
        )
    return success_response(message="Entegrasyon ayarları güncellendi")


@router.get("/api/announcements")
async def list_announcements(
    tenant: TenantContext = Depends(PermissionChecker("announcement.read")),
    db: AsyncSession = Depends(get_db),
):
    query = select(Announcement).where(Announcement.deleted_at.is_(None))
    repo = BaseRepository(db, tenant)
    query = repo._org_filter(query, Announcement)
    query = repo._branch_filter(query, Announcement)
    result = await db.execute(query.order_by(Announcement.created_at.desc()))
    items = result.scalars().all()
    return success_response(
        [
            {
                "id": str(a.id),
                "title": a.title,
                "audience": a.audience.value,
                "status": a.status.value,
                "created_at": a.created_at.isoformat(),
            }
            for a in items
        ]
    )


@router.post("/api/announcements")
async def create_announcement(
    body: AnnouncementCreate,
    tenant: TenantContext = Depends(PermissionChecker("announcement.write")),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = tenant.organization_id
    if not org_id:
        raise ForbiddenException()
    repo = BaseRepository(db, tenant)
    branch = await repo.require_related(UUID(body.branch_id), Branch) if body.branch_id else None
    classroom = (
        await repo.require_related(UUID(body.class_id), ClassRoom) if body.class_id else None
    )
    student = (
        await repo.require_related(UUID(body.student_id), Student) if body.student_id else None
    )
    audience = AnnouncementAudience(body.audience)
    if audience == AnnouncementAudience.BRANCH_PARENTS and not branch:
        raise ValidationException("Şube hedefi zorunludur")
    if audience == AnnouncementAudience.CLASS_PARENTS and not classroom:
        raise ValidationException("Sınıf hedefi zorunludur")
    if audience == AnnouncementAudience.SINGLE_STUDENT and not student:
        raise ValidationException("Öğrenci hedefi zorunludur")
    if branch and branch.organization_id != org_id:
        raise ValidationException("Şube duyuru organizasyonuna ait değil")
    if classroom and (
        classroom.organization_id != org_id or (branch and classroom.branch_id != branch.id)
    ):
        raise ValidationException("Sınıf duyuru kapsamıyla eşleşmiyor")
    if student and (
        student.organization_id != org_id
        or (branch and student.branch_id != branch.id)
        or (classroom and student.class_id != classroom.id)
    ):
        raise ValidationException("Öğrenci duyuru kapsamıyla eşleşmiyor")
    announcement = Announcement(
        organization_id=org_id,
        branch_id=branch.id if branch else None,
        class_id=classroom.id if classroom else None,
        student_id=student.id if student else None,
        title=body.title,
        content=body.content,
        audience=audience,
        channels=body.channels,
        status=AnnouncementStatus.DRAFT,
        created_by=user.id,
    )
    db.add(announcement)
    await db.flush()
    return success_response({"id": str(announcement.id)}, "Duyuru oluşturuldu")


@router.post("/api/announcements/{announcement_id}/send")
async def send_announcement(
    announcement_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("announcement.write")),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    announcement = await BaseRepository(db, tenant).get_by_id(announcement_id, Announcement)
    parents_q = (
        select(Parent)
        .join(StudentParent)
        .join(Student, Student.id == StudentParent.student_id)
        .where(
            Parent.organization_id == announcement.organization_id,
            Student.organization_id == announcement.organization_id,
            Student.deleted_at.is_(None),
            Parent.deleted_at.is_(None),
            Parent.receive_notifications.is_(True),
        )
    )
    if announcement.audience.value == "BRANCH_PARENTS" and announcement.branch_id:
        parents_q = parents_q.where(Student.branch_id == announcement.branch_id)
    elif announcement.audience.value == "CLASS_PARENTS" and announcement.class_id:
        parents_q = parents_q.where(Student.class_id == announcement.class_id)
    elif announcement.audience.value == "SINGLE_STUDENT" and announcement.student_id:
        parents_q = parents_q.where(Student.id == announcement.student_id)
    result = await db.execute(parents_q.distinct())
    parents = result.scalars().all()
    jobs_created = 0
    for channel in announcement.channels:
        job = NotificationJob(
            organization_id=announcement.organization_id,
            branch_id=announcement.branch_id,
            channel=NotificationChannel(channel),
            subject=announcement.title,
            body=announcement.content,
            reference_type="announcement",
            reference_id=announcement.id,
            created_by=user.id,
        )
        db.add(job)
        await db.flush()
        for parent in parents:
            address = parent.email if channel == "EMAIL" else (parent.sms_phone or parent.phone)
            if address:
                from app.infrastructure.models.models import NotificationRecipient

                db.add(
                    NotificationRecipient(
                        notification_job_id=job.id,
                        parent_id=parent.id,
                        recipient_name=f"{parent.first_name} {parent.last_name}",
                        recipient_address=address,
                    )
                )
        jobs_created += 1
    announcement.status = AnnouncementStatus.SENT
    announcement.sent_at = datetime.now(UTC)
    return success_response({"jobs_created": jobs_created}, "Duyuru gönderim kuyruğuna alındı")


@router.get("/api/notifications")
async def list_notifications(
    tenant: TenantContext = Depends(PermissionChecker("notification.read")),
    db: AsyncSession = Depends(get_db),
):
    query = select(NotificationJob)
    repo = BaseRepository(db, tenant)
    query = repo._org_filter(query, NotificationJob)
    query = repo._branch_filter(query, NotificationJob)
    result = await db.execute(query.order_by(NotificationJob.created_at.desc()).limit(50))
    jobs = result.scalars().all()
    return success_response(
        [
            {
                "id": str(j.id),
                "channel": j.channel.value,
                "status": j.status.value,
                "retry_count": j.retry_count,
                "created_at": j.created_at.isoformat(),
            }
            for j in jobs
        ]
    )


@router.post("/api/notifications/{job_id}/retry")
async def retry_notification(
    job_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("notification.write")),
    db: AsyncSession = Depends(get_db),
):
    job = await BaseRepository(db, tenant).get_by_id(job_id, NotificationJob)
    job.status = NotificationStatus.PENDING
    job.retry_count += 1
    return success_response(message="Bildirim tekrar kuyruğa alındı")


@router.get("/api/notifications/templates")
async def list_templates(
    tenant: TenantContext = Depends(PermissionChecker("notification.read")),
    db: AsyncSession = Depends(get_db),
):
    query = select(MessageTemplate).where(MessageTemplate.deleted_at.is_(None))
    if not tenant.is_super_admin:
        query = query.where(
            (MessageTemplate.organization_id == tenant.organization_id)
            | MessageTemplate.organization_id.is_(None)
        )
    result = await db.execute(query)
    templates = result.scalars().all()
    return success_response(
        [
            {
                "id": str(t.id),
                "code": t.code,
                "name": t.name,
                "channel": t.channel.value,
            }
            for t in templates
        ]
    )


@router.get("/api/notifications/{job_id}")
async def get_notification(
    job_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("notification.read")),
    db: AsyncSession = Depends(get_db),
):
    job = await BaseRepository(db, tenant).get_by_id(job_id, NotificationJob)
    recipients = (
        (
            await db.execute(
                select(NotificationRecipient).where(
                    NotificationRecipient.notification_job_id == job_id
                )
            )
        )
        .scalars()
        .all()
    )
    return success_response(
        {
            "id": str(job.id),
            "channel": job.channel.value,
            "status": job.status.value,
            "retry_count": job.retry_count,
            "body": job.body,
            "recipients": [
                {
                    "address": recipient.recipient_address,
                    "status": recipient.status.value,
                    "error": recipient.error_message,
                }
                for recipient in recipients
            ],
        }
    )


@router.get("/api/settings")
async def get_settings(
    tenant: TenantContext = Depends(PermissionChecker("settings.read")),
    db: AsyncSession = Depends(get_db),
):
    query = select(AppSetting)
    if tenant.organization_id:
        query = query.where(AppSetting.organization_id == tenant.organization_id)
    result = await db.execute(query)
    settings = result.scalars().all()
    return success_response({s.setting_key: s.setting_value for s in settings})


@router.put("/api/settings")
async def update_settings(
    body: dict,
    tenant: TenantContext = Depends(PermissionChecker("settings.write")),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    for key, value in body.items():
        result = await db.execute(
            select(AppSetting).where(
                AppSetting.setting_key == key,
                AppSetting.organization_id == tenant.organization_id,
            )
        )
        setting = result.scalar_one_or_none()
        if setting:
            setting.setting_value = value
            setting.updated_by = user.id
        else:
            db.add(
                AppSetting(
                    organization_id=tenant.organization_id,
                    setting_key=key,
                    setting_value=value,
                    updated_by=user.id,
                )
            )
    return success_response(message="Ayarlar güncellendi")


@router.get("/api/settings/integrations")
async def get_integrations(
    tenant: TenantContext = Depends(PermissionChecker("settings.read")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(IntegrationSetting).where(
            IntegrationSetting.organization_id == tenant.organization_id
        )
    )
    integrations = result.scalars().all()
    return success_response(
        [
            {
                "id": str(i.id),
                "provider": i.provider.value,
                "is_active": i.is_active,
                "config": {
                    k: "***" if "password" in k.lower() or "token" in k.lower() else v
                    for k, v in i.config.items()
                },
            }
            for i in integrations
        ]
    )
