"""The same recipient policy for discoverable contacts and direct sends."""
from uuid import UUID

from sqlalchemy import and_, or_, select, union
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.student_access import accessible_student_ids, parent_student_ids, uses_relationship_scope
from app.core.tenant import TenantContext
from app.infrastructure.models.models import (
    Branch, ClassRoom, ClassTeacher, ClassroomAssignment, Parent, Student, StudentParent,
    StudentTeacherAssignment, User, UserBranch,
)
from app.infrastructure.repositories.base import BaseRepository


async def message_branches(db: AsyncSession, tenant: TenantContext, branch_id: UUID | None) -> list[UUID]:
    if tenant.organization_id is None or tenant.is_super_admin:
        raise ForbiddenException("Mesajlaşmadan önce kurum seçin")
    if branch_id is not None:
        await BaseRepository(db, tenant).get_by_id(branch_id, Branch)
        return [branch_id]
    return [] if tenant.is_organization_owner else tenant.branch_ids


async def recipient_query(db: AsyncSession, tenant: TenantContext, branch_id: UUID | None, *, for_history: bool = False):
    branch_ids = await message_branches(db, tenant, branch_id)
    organization = tenant.organization_id
    # Each join names its tenant boundary explicitly because branch assignment
    # and a student's guardian or teacher relationship are separate access paths.
    users, pupils, rooms, parents, links, class_teachers, lessons, assignments, branches, user_branches = (
        model.__table__.c for model in (User, Student, ClassRoom, Parent, StudentParent, ClassTeacher,
                                      ClassroomAssignment, StudentTeacherAssignment, Branch, UserBranch)
    )
    query = select(users.id, users.first_name, users.last_name).where(
        users.organization_id == organization, users.id != tenant.user_id,
        users.is_super_admin.is_(False), users.deleted_at.is_(None),
    )
    if not for_history:
        query = query.where(users.status == "ACTIVE")
    relationship_scope = not for_history and uses_relationship_scope(tenant)
    is_parent = relationship_scope and "parent" in tenant.role_slugs
    if not relationship_scope and not branch_ids:
        return query

    students = select(pupils.id, pupils.class_id, pupils.branch_id).where(
        pupils.organization_id == organization, pupils.deleted_at.is_(None),
    )
    if branch_ids:
        students = students.where(pupils.branch_id.in_(branch_ids))
    if relationship_scope:
        allowed = await (parent_student_ids(db, tenant.user_id, organization) if is_parent
                         else accessible_student_ids(db, tenant))
        students = students.where(pupils.id.in_(allowed or ()))
    students = students.subquery()

    guardians = select(parents.user_id).join(StudentParent.__table__, links.parent_id == parents.id).where(
        parents.organization_id == organization, parents.deleted_at.is_(None),
        links.student_id.in_(select(students.c.id)),
    )
    if relationship_scope and not is_parent:
        return query.where(users.id.in_(guardians))

    classes = select(rooms.id, rooms.teacher_id).join(
        students, and_(students.c.class_id == rooms.id, students.c.branch_id == rooms.branch_id),
    ).where(rooms.organization_id == organization, rooms.deleted_at.is_(None)).subquery()
    teachers = union(
        select(classes.c.teacher_id),
        select(class_teachers.user_id).where(class_teachers.class_id.in_(select(classes.c.id))),
        select(lessons.teacher_id).where(lessons.class_id.in_(select(classes.c.id))),
        select(assignments.teacher_id).where(
            assignments.student_id.in_(select(students.c.id)),
        ),
    )
    if is_parent:
        return query.where(users.id.in_(teachers))

    assigned_users = select(user_branches.user_id).join(Branch.__table__, branches.id == user_branches.branch_id).where(
        branches.id.in_(branch_ids), branches.organization_id == organization, branches.deleted_at.is_(None),
    )
    return query.where(or_(
        users.id.in_(assigned_users), users.id.in_(guardians), users.id.in_(teachers),
    ))


async def require_recipient(db: AsyncSession, tenant: TenantContext, recipient_id: UUID, branch_id: UUID | None) -> None:
    query = await recipient_query(db, tenant, branch_id)
    recipient = await db.scalar(query.where(User.__table__.c.id == recipient_id))
    if recipient is None:
        raise NotFoundException("Mesaj alıcısı bulunamadı")
