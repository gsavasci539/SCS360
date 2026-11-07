from calendar import monthrange
from datetime import date, timedelta

from sqlalchemy import exists, func, or_, select

from app.core.dates import school_today
from app.core.exceptions import ForbiddenException
from app.core.tenant_guard import scope_filters, staff_scope
from app.domain.entities.payroll import StaffTimesheet, AdditionalCourseHours, PayrollRecord
from app.infrastructure.models.models import User, Role, UserRole, UserStatus, Organization


async def options(db, tenant, search="", staff_id=None):
    users, roles, assignments, organizations = User.__table__, Role.__table__, UserRole.__table__, Organization.__table__
    assigned = select(assignments.c.user_id).join(roles, roles.c.id == assignments.c.role_id).where(assignments.c.user_id == users.c.id,
        roles.c.deleted_at.is_(None), or_(roles.c.organization_id.is_(None), roles.c.organization_id == users.c.organization_id)).correlate(users)
    # Parent-only accounts are not staff. Keep legacy staff without a role
    # available; never change their roles or account data as part of payroll.
    staff_roles = assigned.where(roles.c.slug != "parent")
    query = select(users.c.id, users.c.first_name, users.c.last_name, organizations.c.name.label("organization_name"))
    query = query.join(organizations, organizations.c.id == users.c.organization_id).where(users.c.status == UserStatus.ACTIVE,
        users.c.deleted_at.is_(None), organizations.c.deleted_at.is_(None), organizations.c.is_active.is_(True),
        or_(exists(staff_roles), ~exists(assigned)))
    if not tenant.is_super_admin:
        if tenant.organization_id is None:
            raise ForbiddenException()
        branches, _, _, allowed = scope_filters(tenant, db.info.get("accessible_student_ids"))
        query = query.where(users.c.id.in_(staff_scope(tenant, branches, allowed)))
    filtered = query.where(or_(users.c.first_name.ilike(f"%{search}%"), users.c.last_name.ilike(f"%{search}%"))) if search else query
    rows = (await db.execute(filtered.order_by(users.c.first_name, users.c.id).limit(101))).all()
    choices = rows[:100]
    if staff_id and not any(row.id == staff_id for row in choices):
        selected = (await db.execute(query.where(users.c.id == staff_id))).one_or_none()
        if selected:
            choices = [*choices, selected]
    return {"staff": [{"id": str(row.id), "name": f"{row.first_name} {row.last_name}", "organization_name": row.organization_name} for row in choices],
        "more_staff": len(rows) > 100, "today": school_today().isoformat()}


async def summary(db, year=None, month=None, period=None, staff_id=None):
    if month and year is None:
        year = school_today().year
    query = select(func.count(PayrollRecord.id), func.coalesce(func.sum(PayrollRecord.net_salary), 0))
    hours = select(func.count(StaffTimesheet.id), func.coalesce(func.avg(StaffTimesheet.work_hours), 0))
    extra = select(func.coalesce(func.sum(AdditionalCourseHours.total_amount), 0))
    drafts = select(func.count(PayrollRecord.id)).where(PayrollRecord.status == "DRAFT")
    if year:
        for model, key in ((PayrollRecord, "records"), (AdditionalCourseHours, "extra")):
            if key == "records":
                query = query.where(model.year == year); drafts = drafts.where(model.year == year)
            else:
                extra = extra.where(model.year == year)
        start = date(year, month or 1, 1)
        if month and period == "QUARTERLY":
            index = year * 12 + month - 1 + 3
            end = date(index // 12, index % 12 + 1, 1) - timedelta(days=1)
        else:
            end = date(year, month or 12, monthrange(year, month or 12)[1])
        hours = hours.where(StaffTimesheet.date >= start, StaffTimesheet.date <= end)
    if month:
        query = query.where(PayrollRecord.month == month); drafts = drafts.where(PayrollRecord.month == month)
        extra = extra.where(AdditionalCourseHours.month == month)
    if period:
        query = query.where(PayrollRecord.period == period); drafts = drafts.where(PayrollRecord.period == period)
        extra = extra.where(AdditionalCourseHours.period == period)
    if staff_id:
        query = query.where(PayrollRecord.staff_id == staff_id); drafts = drafts.where(PayrollRecord.staff_id == staff_id)
        hours = hours.where(StaffTimesheet.staff_id == staff_id); extra = extra.where(AdditionalCourseHours.staff_id == staff_id)
    count, net = (await db.execute(query)).one()
    timesheets, average = (await db.execute(hours)).one()
    return {"total_timesheets": timesheets, "total_payroll": count, "net_salary_total": float(net),
        "pending_approvals": (await db.execute(drafts)).scalar() or 0, "average_hours": round(float(average), 2),
        "additional_course_total": float((await db.execute(extra)).scalar() or 0)}
