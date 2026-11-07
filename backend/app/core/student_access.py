"""Relationship-based student access checks.

Role permissions grant access to a feature; these helpers additionally limit
parents and teachers to the students with whom they have an explicit database
relationship.  Keeping the rule here prevents endpoints from accidentally
comparing a ``users.id`` to a ``parents.id``.
"""

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException
from app.core.tenant import TenantContext
from app.core.teaching import teacher_class_condition
from app.infrastructure.models.models import ClassRoom, ClassTeacher, Parent, Student, StudentParent, StudentTeacherAssignment, User


_UNSCOPED_ROLES = {"admin", "administrator", "school_admin", "manager", "principal", "org_admin", "branch_manager", "owner"}


def parent_contacts_query(user_id, organization_id=None):
    query = select(Parent).join(User, User.id == Parent.user_id).where(
        Parent.user_id == user_id, Parent.deleted_at.is_(None),
        User.organization_id == Parent.organization_id, User.deleted_at.is_(None), User.status == "ACTIVE")
    if organization_id is not None:
        query = query.where(Parent.organization_id == organization_id)
    return query


async def parent_student_ids(db, user_id, organization_id):
    """Own guardian links across branches, independent of the staff workspace.

    Core columns intentionally avoid a previously bound staff branch filter;
    every actor, institution and soft-delete boundary is explicit instead.
    Multiple historical contacts are read without changing or merging them.
    """
    if organization_id is None:
        return set()
    parents, links, students, users = [model.__table__ for model in (Parent, StudentParent, Student, User)]
    query = select(students.c.id).select_from(students).join(links, links.c.student_id == students.c.id)
    query = query.join(parents, parents.c.id == links.c.parent_id).join(users, users.c.id == parents.c.user_id).where(
        users.c.id == user_id, users.c.organization_id == organization_id, users.c.deleted_at.is_(None), users.c.status == "ACTIVE",
        parents.c.organization_id == organization_id, parents.c.deleted_at.is_(None),
        students.c.organization_id == organization_id, students.c.deleted_at.is_(None))
    return {UUID(str(identifier)) for identifier in (await db.execute(query)).scalars()}


def uses_relationship_scope(tenant: TenantContext) -> bool:
    """Whether this user's student access must be restricted by relationships."""
    return (
        not tenant.is_super_admin
        and bool(tenant.role_slugs & {"parent", "teacher"})
        and not bool(tenant.role_slugs & _UNSCOPED_ROLES)
    )


async def accessible_student_ids(db: AsyncSession, tenant: TenantContext) -> set[UUID] | None:
    """Return allowed student ids, or ``None`` when the role is not scoped."""
    if not uses_relationship_scope(tenant):
        return None

    ids: set[UUID] = set()
    if "parent" in tenant.role_slugs:
        ids.update(await parent_student_ids(db, tenant.user_id, tenant.organization_id))

    if "teacher" in tenant.role_slugs:
        result = await db.execute(
            select(Student.id).where(
                Student.organization_id == tenant.organization_id,
                Student.deleted_at.is_(None),
                or_(Student.id.in_(select(StudentTeacherAssignment.student_id).where(
                    StudentTeacherAssignment.teacher_id == tenant.user_id)), Student.class_id.in_(
                    select(ClassRoom.id).where(
                        ClassRoom.organization_id == tenant.organization_id,
                        ClassRoom.branch_id == Student.branch_id,
                        ClassRoom.deleted_at.is_(None), teacher_class_condition(ClassRoom, tenant.user_id),
                    )
                )),
            )
        )
        ids.update(UUID(str(student_id)) for student_id in result.scalars())
    return ids


async def require_student_access(db: AsyncSession, tenant: TenantContext, student_id: UUID) -> None:
    """Raise 403 unless a relationship-scoped user may access this student."""
    ids = await accessible_student_ids(db, tenant)
    if ids is not None and student_id not in ids:
        raise ForbiddenException("Bu öğrenciye erişim yetkiniz yok")


async def require_parent_child_access(db: AsyncSession, user_id: UUID, student_id: UUID) -> Parent:
    """Resolve the parent's domain record and verify the child link."""
    parent = (
        await db.execute(
            parent_contacts_query(user_id)
            .join(StudentParent, StudentParent.parent_id == Parent.id)
            .join(Student, Student.id == StudentParent.student_id)
            .where(Student.id == student_id, Student.organization_id == Parent.organization_id, Student.deleted_at.is_(None))
            .order_by(StudentParent.is_primary.desc(), Parent.created_at, Parent.id)
        )
    ).scalars().first()
    if parent is None:
        raise ForbiddenException("Bu öğrenciye erişiminiz yok")
    return parent


async def require_teacher_for_student(
    db: AsyncSession, student: Student, teacher_id: UUID
) -> None:
    """Only permit parent messaging to a teacher assigned to the child's class."""
    teacher = (await db.execute(select(User).where(User.id == teacher_id, User.organization_id == student.organization_id,
        User.deleted_at.is_(None), User.status == "ACTIVE"))).scalar_one_or_none()
    if teacher is None:
        raise ForbiddenException("Aktif ve aynı kuruma bağlı öğretmen gerekli")
    direct = (await db.execute(select(StudentTeacherAssignment.id).where(
        StudentTeacherAssignment.student_id == student.id,
        StudentTeacherAssignment.teacher_id == teacher_id))).first()
    if direct is not None:
        return
    if student.class_id is None:
        raise ForbiddenException("Öğrencinin atanmış bir sınıfı yok")
    assigned = (
        await db.execute(
            select(ClassRoom.id).where(
                ClassRoom.id == student.class_id,
                ClassRoom.deleted_at.is_(None), teacher_class_condition(ClassRoom, teacher_id),
            )
        )
    ).scalar_one_or_none()
    if assigned is None:
        raise ForbiddenException("Öğretmen öğrencinin sınıfına atanmamış")
