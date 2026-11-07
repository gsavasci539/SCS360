from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import or_, select

from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.student_access import accessible_student_ids, require_student_access, uses_relationship_scope
from app.core.teaching import teacher_class_condition
from app.infrastructure.models.models import ClassRoom, ClassTeacher, Homework, HomeworkSubmission, Student
from app.infrastructure.repositories.base import BaseRepository


def class_scope(tenant):
    repo = BaseRepository(None, tenant)
    query = repo._branch_filter(repo._org_filter(select(ClassRoom.id), ClassRoom), ClassRoom)
    if uses_relationship_scope(tenant) and "teacher" in tenant.role_slugs:
        query = query.where(teacher_class_condition(ClassRoom, tenant.user_id))
    return query


async def scoped_query(db, tenant):
    query = BaseRepository(db, tenant)._org_filter(select(Homework), Homework).where(Homework.deleted_at.is_(None))
    if uses_relationship_scope(tenant) and "parent" in tenant.role_slugs:
        ids = await accessible_student_ids(db, tenant)
        query = query.where(Homework.status == "ACTIVE",
            Homework.class_id.in_(select(Student.class_id).where(Student.id.in_(ids or set()))))
    else:
        query = query.where(or_(Homework.class_id.in_(class_scope(tenant)),
            (Homework.class_id.is_(None)) & (Homework.created_by == tenant.user_id)))
    return query


async def get(db, tenant, identifier):
    record = (await db.execute((await scoped_query(db, tenant)).where(Homework.id == identifier))).scalar_one_or_none()
    if record is None:
        raise NotFoundException("Ödev bulunamadı")
    return record


def serialize(record, class_name=None):
    return {"id": str(record.id), "title": record.title, "subject": record.subject,
        "description": record.description, "class_id": str(record.class_id) if record.class_id else None,
        "class_name": class_name, "due_date": record.due_date.isoformat() if record.due_date else None,
        "attachment_url": record.attachment_url, "status": record.status,
        "created_at": record.created_at.isoformat() if record.created_at else None}


async def list_records(db, tenant, class_id=None, search=None):
    query = await scoped_query(db, tenant)
    if class_id:
        query = query.where(Homework.class_id == class_id)
    if search:
        query = query.where(Homework.title.ilike(f"%{search}%") | Homework.subject.ilike(f"%{search}%"))
    records = (await db.execute(query.order_by(Homework.created_at.desc()))).scalars().all()
    ids = {record.class_id for record in records if record.class_id}
    names = {row.id: row.name for row in (await db.execute(select(ClassRoom).where(ClassRoom.id.in_(ids)))).scalars()}
    return [serialize(record, names.get(record.class_id)) for record in records]


async def save(db, tenant, body, record=None):
    values = body.model_dump(exclude_unset=record is not None)
    target = values.get("class_id", record.class_id if record else None)
    if target is not None:
        allowed = (await db.execute(class_scope(tenant).where(ClassRoom.id == target))).scalar_one_or_none()
        if allowed is None:
            raise ForbiddenException("Bu sınıfa ödev atama yetkiniz yok")
    if record is None:
        if not tenant.organization_id:
            raise ForbiddenException("Kurum bilgisi gerekli")
        record = Homework(organization_id=tenant.organization_id, created_by=tenant.user_id, **values)
        db.add(record)
    else:
        for key, value in values.items():
            setattr(record, key, value)
    await db.flush()
    return serialize(record)
