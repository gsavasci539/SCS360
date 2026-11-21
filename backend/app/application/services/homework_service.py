from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import or_, select, update

from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.core.student_access import accessible_student_ids, require_student_access, uses_relationship_scope
from app.core.teaching import teacher_class_condition
from app.infrastructure.models.models import ClassRoom, ClassTeacher, Homework, HomeworkSubmission, Organization, Student
from app.infrastructure.repositories.base import BaseRepository


def class_scope(tenant, branch_id=None):
    repo = BaseRepository(None, tenant)
    query = repo._branch_filter(repo._org_filter(select(ClassRoom.id), ClassRoom), ClassRoom)
    if branch_id is not None:
        query = query.where(ClassRoom.branch_id == branch_id)
    if uses_relationship_scope(tenant) and tenant.has_teacher_role:
        query = query.where(teacher_class_condition(ClassRoom, tenant.user_id))
    return query


async def scoped_query(db, tenant, branch_id=None):
    query = BaseRepository(db, tenant)._org_filter(select(Homework), Homework).where(Homework.deleted_at.is_(None))
    if uses_relationship_scope(tenant) and "parent" in tenant.role_slugs:
        ids = await accessible_student_ids(db, tenant)
        query = query.where(Homework.status == "ACTIVE",
            Homework.class_id.in_(select(Student.class_id).where(Student.id.in_(ids or set()))))
    else:
        query = query.where(or_(Homework.class_id.in_(class_scope(tenant)),
            (Homework.class_id.is_(None)) & (Homework.created_by == tenant.user_id)))
    if branch_id is not None:
        query = query.where(Homework.class_id.in_(select(ClassRoom.id).where(ClassRoom.branch_id == branch_id)))
    return query


async def get(db, tenant, identifier, branch_id=None):
    record = (await db.execute((await scoped_query(db, tenant, branch_id)).where(Homework.id == identifier))).scalar_one_or_none()
    if record is None:
        raise NotFoundException("Ödev bulunamadı")
    return record


def serialize(record, class_name=None):
    return {"id": str(record.id), "title": record.title, "subject": record.subject,
        "description": record.description, "class_id": str(record.class_id) if record.class_id else None,
        "class_name": class_name, "due_date": record.due_date.isoformat() if record.due_date else None,
        "attachment_url": record.attachment_url, "status": record.status,
        "created_at": record.created_at.isoformat() if record.created_at else None}


async def list_records(db, tenant, class_id=None, search=None, *, branch_id=None):
    query = await scoped_query(db, tenant, branch_id)
    if class_id:
        query = query.where(Homework.class_id == class_id)
    if search:
        query = query.where(Homework.title.ilike(f"%{search}%") | Homework.subject.ilike(f"%{search}%"))
    records = (await db.execute(query.order_by(Homework.created_at.desc(), Homework.id))).scalars().all()
    ids = {record.class_id for record in records if record.class_id}
    names = {row.id: row.name for row in (await db.execute(select(ClassRoom).where(ClassRoom.id.in_(ids)))).scalars()}
    return [serialize(record, names.get(record.class_id)) for record in records]


async def save(db, tenant, body, record=None, *, branch_id=None):
    values = body.model_dump(exclude_unset=record is not None, exclude={"request_id"})
    target = values.get("class_id", record.class_id if record else None)
    if target is not None:
        allowed = (await db.execute(class_scope(tenant, branch_id).where(ClassRoom.id == target))).scalar_one_or_none()
        if allowed is None:
            raise ForbiddenException("Bu sınıfa ödev atama yetkiniz yok")
    elif branch_id is not None:
        raise ForbiddenException("Seçili şubede bir sınıf seçin")
    if record is None:
        if not tenant.organization_id:
            raise ForbiddenException("Kurum bilgisi gerekli")
        request_id = getattr(body, "request_id", None)
        if request_id is not None:
            await db.execute(update(Organization).where(Organization.id == tenant.organization_id)
                .values(updated_at=Organization.updated_at))
            previous = (await db.execute((await scoped_query(db, tenant, branch_id)).where(Homework.id == request_id))).scalar_one_or_none()
            if previous is not None:
                if previous.created_by != tenant.user_id or any(getattr(previous, key) != value for key, value in values.items()):
                    raise ConflictException("İstek kimliği başka ödeve ait")
                return serialize(previous)
            if (await db.execute(select(Homework.__table__.c.id).where(Homework.__table__.c.id == request_id))).first():
                raise ConflictException("Ödev işlem kimliği kullanılamıyor")
            values["id"] = request_id
        record = Homework(organization_id=tenant.organization_id, created_by=tenant.user_id, **values)
        db.add(record)
    else:
        for key, value in values.items():
            setattr(record, key, value)
    await db.flush()
    return serialize(record)
