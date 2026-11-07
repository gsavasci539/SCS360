from sqlalchemy import func, or_, select

from app.core.dates import school_today
from app.domain.entities.guidance import GuidanceSession, BehavioralIncident, GuidanceNote
from app.infrastructure.models.models import Student, User, UserStatus, Role, UserRole, RolePermission, Permission


async def options(db, tenant, student_id=None, search="", counselor_search=""):
    query = select(Student).where(Student.deleted_at.is_(None))
    if search:
        query = query.where(or_(Student.first_name.ilike(f"%{search}%"), Student.last_name.ilike(f"%{search}%")))
    students = (await db.execute(query.order_by(Student.first_name, Student.id).limit(101))).scalars().all()
    selected = (await db.execute(select(Student).where(Student.id == student_id, Student.deleted_at.is_(None)))).scalar_one_or_none() if student_id else None
    choices = students[:100]
    if selected and not any(row.id == selected.id for row in choices):
        choices = [*choices, selected]
    counselors = []
    more_counselors = False
    if tenant.has_permission("guidance.write") and student_id:
        student = selected
        if student:
            roles, assignments, permissions, links = Role.__table__, UserRole.__table__, Permission.__table__, RolePermission.__table__
            allowed = select(assignments.c.user_id).join(roles, roles.c.id == assignments.c.role_id)
            allowed = allowed.join(links, links.c.role_id == roles.c.id).join(permissions, permissions.c.id == links.c.permission_id)
            allowed = allowed.where(roles.c.deleted_at.is_(None), or_(roles.c.organization_id.is_(None), roles.c.organization_id == student.organization_id), permissions.c.code == "guidance.write")
            query = select(User).where(User.organization_id == student.organization_id, User.status == UserStatus.ACTIVE,
                User.deleted_at.is_(None), or_(User.is_super_admin.is_(True), User.id.in_(allowed)))
            if not tenant.has_permission("guidance.read_confidential"):
                query = query.where(User.id == tenant.user_id)
            if counselor_search:
                query = query.where(or_(User.first_name.ilike(f"%{counselor_search}%"), User.last_name.ilike(f"%{counselor_search}%")))
            counselors = (await db.execute(query.order_by(User.first_name, User.id).limit(101))).scalars().all()
            more_counselors = len(counselors) > 100
    return {"students": [{"id": str(row.id), "name": f"{row.first_name} {row.last_name}"} for row in choices],
        "counselors": [{"id": str(row.id), "name": f"{row.first_name} {row.last_name}"} for row in counselors[:100]],
        "more_students": len(students) > 100, "more_counselors": more_counselors, "today": school_today().isoformat()}


async def summary(db, student_id=None):
    async def count(model, *conditions):
        query = select(func.count(model.id)).where(*conditions)
        if student_id:
            query = query.where(model.student_id == student_id)
        return (await db.execute(query)).scalar() or 0
    sessions = await count(GuidanceSession)
    incidents = await count(BehavioralIncident)
    resolved = await count(BehavioralIncident, BehavioralIncident.resolved.is_(True))
    return {"total_sessions": sessions, "total_incidents": incidents, "active_cases": incidents - resolved,
        "total_notes": await count(GuidanceNote), "resolution_rate": round(resolved * 100 / incidents, 2) if incidents else 0}
