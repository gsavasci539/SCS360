"""Server-selected guardian workspace, restricted to the actor's own children."""
from dataclasses import replace

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.student_access import parent_student_ids
from app.core.tenant import effective_roles
from app.infrastructure.models.models import Student, User


async def activate_parent_scope(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db, scope="function")):
    # Installed only by the parent router; no request header/body can activate it
    # for staff or finance endpoints. The authenticated User is never modified.
    tenant = db.info.get("tenant_context")
    if user.is_super_admin or tenant is None or tenant.platform_admin:
        return
    if not any(role.slug == "parent" for role in effective_roles(user)):
        return
    identifiers = await parent_student_ids(db, user.id, user.organization_id)
    students = Student.__table__
    branch_ids = set((await db.execute(select(students.c.branch_id).where(
        students.c.id.in_(identifiers), students.c.organization_id == user.organization_id,
        students.c.deleted_at.is_(None), students.c.branch_id.is_not(None),
    ))).scalars()) if identifiers else set()
    db.info["tenant_context"] = replace(tenant, branch_ids=list(branch_ids), role_slugs={"parent"},
        permissions={code for code in tenant.permissions if code.startswith("parent.")}, parent_portal=True)
    db.info["accessible_student_ids"] = identifiers
