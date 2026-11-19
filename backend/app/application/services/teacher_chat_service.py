"""Teacher replies use the same student/parent conversation as the parent portal."""
from dataclasses import replace

from sqlalchemy import func, or_, select

from app.application.services import student_chat_messages
from app.application.services.message_contacts import message_branches
from app.core.exceptions import ForbiddenException, NotFoundException, ValidationException
from app.core.student_access import (
    accessible_student_ids,
    require_teacher_for_student,
    uses_relationship_scope,
)
from app.core.tenant_guard import scope_filters
from app.infrastructure.models.models import (
    ChatConversation,
    ClassRoom,
    Parent,
    Student,
    StudentParent,
    User,
)
from app.infrastructure.repositories.base import BaseRepository

_LEGACY_TEACHER_ROLES = {"teacher1", "teacher2", "teacher3"}


def _relationship_tenant(tenant):
    if tenant.role_slugs & _LEGACY_TEACHER_ROLES:
        return replace(tenant, role_slugs=tenant.role_slugs | {"teacher"})
    return tenant


async def contact_query(db, tenant, branch_id=None):
    tenant = _relationship_tenant(tenant)
    branch_ids = await message_branches(db, tenant, branch_id)
    student_ids = await accessible_student_ids(db, tenant)
    _, allowed_students, allowed_classes, _ = scope_filters(replace(tenant, branch_ids=branch_ids), student_ids)
    students, links, parents, accounts, classes = [
        model.__table__.c for model in (Student, StudentParent, Parent, User, ClassRoom)
    ]
    student_name = (students.first_name + " " + students.last_name).label("student_name")
    parent_name = (accounts.first_name + " " + accounts.last_name).label("parent_name")
    return (select(students.id.label("student_id"), students.branch_id, student_name,
        accounts.id.label("parent_id"), parent_name, classes.name.label("class_name"))
        .select_from(Student.__table__)
        .join(StudentParent.__table__, links.student_id == students.id)
        .join(Parent.__table__, parents.id == links.parent_id)
        .join(User.__table__, accounts.id == parents.user_id)
        .outerjoin(ClassRoom.__table__, (classes.id == students.class_id) & classes.id.in_(allowed_classes))
        .where(students.id.in_(allowed_students), parents.organization_id == students.organization_id,
            parents.deleted_at.is_(None), accounts.organization_id == students.organization_id,
            accounts.deleted_at.is_(None), accounts.status == "ACTIVE", accounts.id != tenant.user_id)
        .distinct())


async def contact_branches(db, tenant):
    from app.infrastructure.models.models import Branch

    contacts = (await contact_query(db, tenant)).subquery()
    branches = Branch.__table__.c
    rows = (await db.execute(select(branches.id, branches.name)
        .where(branches.id.in_(select(contacts.c.branch_id))).order_by(branches.name, branches.id))).all()
    return [{"id": str(row.id), "name": row.name} for row in rows]


async def contacts(db, tenant, branch_id, page, page_size, search):
    query = await contact_query(db, tenant, branch_id)
    columns = query.selected_columns
    if search.strip():
        term = search.strip().lower()
        query = query.where(or_(func.lower(columns.student_name).contains(term, autoescape=True),
            func.lower(columns.parent_name).contains(term, autoescape=True),
            func.lower(columns.class_name).contains(term, autoescape=True)))
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    rows = (await db.execute(query.order_by(columns.student_name, columns.student_id, columns.parent_name, columns.parent_id)
        .offset((page - 1) * page_size).limit(page_size))).all()
    return [{"student_id": str(row.student_id), "student_name": row.student_name,
        "parent_id": str(row.parent_id), "parent_name": row.parent_name, "class_name": row.class_name,
        "branch_id": str(row.branch_id)} for row in rows], total


async def participants(db, tenant, student_id, parent_id=None):
    if tenant.is_super_admin or tenant.organization_id is None:
        raise ForbiddenException("Mesajlaşmadan önce kurum seçin")
    student = await BaseRepository(db, tenant).get_by_id(student_id, Student)
    if uses_relationship_scope(_relationship_tenant(tenant)):
        await require_teacher_for_student(db, student, tenant.user_id)
    query = select(Parent, StudentParent).join(StudentParent, StudentParent.parent_id == Parent.id).where(
        StudentParent.student_id == student.id, Parent.organization_id == student.organization_id,
        Parent.deleted_at.is_(None), Parent.user_id.is_not(None))
    if parent_id:
        query = query.where(Parent.user_id == parent_id)
    row = (await db.execute(query.order_by(StudentParent.is_primary.desc(), Parent.id).limit(1))).first()
    if row is None:
        raise NotFoundException("Öğrenciye bağlı veli hesabı bulunamadı")
    parent = row[0]
    account = (await db.execute(select(User).where(User.id == parent.user_id,
        User.organization_id == student.organization_id, User.deleted_at.is_(None)))).scalar_one_or_none()
    if account is None:
        raise ForbiddenException("Veli hesabına erişilemiyor")
    return student, account


async def thread(db, tenant, student_id, parent_id=None, *, create=False, branch_id=None):
    student, parent = await participants(db, tenant, student_id, parent_id)
    if branch_id is not None and student.branch_id != branch_id:
        raise NotFoundException("Öğrenci seçili şubede bulunamadı")
    if create:
        await student_chat_messages.lock_student(db, student)
    conversation = (await db.execute(select(ChatConversation).where(
        ChatConversation.student_id == student.id, ChatConversation.parent_id == parent.id,
        ChatConversation.teacher_id == tenant.user_id, ChatConversation.is_active.is_(True))
        .order_by(ChatConversation.created_at).limit(1))).scalar_one_or_none()
    if conversation is None and create:
        conversation = ChatConversation(student_id=student.id, parent_id=parent.id,
            teacher_id=tenant.user_id, subject_context="Veli-öğretmen iletişimi", created_via="DIRECT")
        db.add(conversation)
        await db.flush()
    return student, parent, conversation


async def history(db, tenant, student_id, parent_id=None, branch_id=None, *, limit=None, before_id=None):
    _, _, conversation = await thread(db, tenant, student_id, parent_id, branch_id=branch_id)
    return await student_chat_messages.history(db, conversation, tenant.user_id, limit=limit, before_id=before_id)


async def send(db, tenant, student_id, content, parent_id=None, request_id=None, upload=None, *, branch_id=None):
    content = content.strip()
    if (not content and upload is None) or len(content) > 10000:
        raise ValidationException("Mesaj 1–10000 karakter olmalı")
    student, _, conversation = await thread(db, tenant, student_id, parent_id, create=True, branch_id=branch_id)
    sender_role = "TEACHER" if "teacher" in _relationship_tenant(tenant).role_slugs else "STAFF"
    return await student_chat_messages.record(db, student, conversation, tenant.user_id, sender_role,
        content, request_id, upload)
