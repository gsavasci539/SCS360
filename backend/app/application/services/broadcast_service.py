"""Queue broadcasts through the real outbox; provider results determine delivery."""
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select, update

from app.core.config import get_settings
from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.domain.entities.communications import BroadcastJob
from app.infrastructure.models.models import (Branch, ClassRoom, NotificationJob, NotificationRecipient,
    NotificationStatus, NotificationChannel, OperationalRecord, Parent, Student, StudentParent, User, UserRole, Role)
from app.infrastructure.repositories.base import BaseRepository


def now():
    return datetime.now(UTC)


def schedule(value):
    if value is None:
        return now()
    if value.tzinfo is None:
        value = value.replace(tzinfo=ZoneInfo(get_settings().BUSINESS_TIMEZONE))
    return value.astimezone(UTC)


def stored_schedule(value):
    return value.replace(tzinfo=UTC) if value and value.tzinfo is None else value


async def get(db, identifier):
    job = (await db.execute(select(BroadcastJob).where(BroadcastJob.id == identifier))).scalar_one_or_none()
    if job is None:
        raise NotFoundException("Toplu ileti bulunamadı")
    return job


async def configuration(db, job):
    return (await db.execute(select(OperationalRecord).where(OperationalRecord.kind == "BROADCAST_CONFIG",
        OperationalRecord.reference_key == str(job.id)))).scalar_one_or_none()


async def validate(db, tenant, values):
    if not tenant.organization_id:
        raise ValidationException("Toplu ileti için kurum bağlamı gerekli")
    repo = BaseRepository(db, tenant)
    branch = await repo.get_by_id(values.target_branch_id, Branch) if values.target_branch_id else None
    classroom = await repo.get_by_id(values.target_class_id, ClassRoom) if values.target_class_id else None
    if any(row.organization_id != tenant.organization_id for row in (branch, classroom) if row):
        raise ValidationException("Hedef bu kuruma ait değil")
    if branch and classroom and classroom.branch_id != branch.id:
        raise ValidationException("Sınıf ve şube eşleşmiyor")
    if values.target_audience == "CLASS_PARENTS" and classroom is None:
        raise ValidationException("Sınıf seçilmeli")
    if values.target_audience == "BRANCH_PARENTS" and branch is None:
        raise ValidationException("Şube seçilmeli")
    if not values.title.strip() or not values.message_content.strip():
        raise ValidationException("Başlık ve ileti metni gerekli")
    if "{" in values.message_content or "}" in values.message_content:
        raise ValidationException("Toplu ileti metnindeki değişkenleri gönderimden önce doldurun")
    if values.target_role and (values.target_audience.endswith("PARENTS") or
        (values.target_audience == "ALL_TEACHERS" and values.target_role != "TEACHER")):
        raise ValidationException("Hedef rol seçilen kitleyle eşleşmiyor")


async def recipients(db, organization_id, values):
    if values.target_audience.endswith("PARENTS"):
        query = select(Parent).join(StudentParent, StudentParent.parent_id == Parent.id).join(Student,
            Student.id == StudentParent.student_id).where(Parent.organization_id == organization_id,
            Student.organization_id == organization_id, Parent.deleted_at.is_(None), Student.deleted_at.is_(None),
            Parent.receive_notifications.is_(True))
        if values.target_branch_id:
            query = query.where(Student.branch_id == values.target_branch_id)
        if values.target_class_id:
            query = query.where(Student.class_id == values.target_class_id)
        rows = (await db.execute(query)).scalars().unique().all()
        people = [(row, row.id, row.user_id) for row in rows]
    else:
        query = select(User).join(UserRole, UserRole.user_id == User.id).join(Role, Role.id == UserRole.role_id).where(
            User.organization_id == organization_id, User.deleted_at.is_(None), Role.deleted_at.is_(None),
            or_(Role.organization_id.is_(None), Role.organization_id == organization_id), Role.slug != "parent")
        role = getattr(values, "target_role", None)
        if values.target_audience == "ALL_TEACHERS":
            query = query.where(Role.slug == "teacher")
        elif role:
            aliases = {"ADMIN": "org_admin", "OWNER": "owner", "TEACHER": "teacher", "STAFF": "staff"}
            query = query.where(Role.slug == aliases.get(role.upper(), role.lower()))
        if values.target_branch_id:
            from app.infrastructure.models.models import UserBranch
            query = query.where(or_(User.id.in_(select(UserBranch.user_id).where(UserBranch.branch_id == values.target_branch_id)),
                User.id.in_(select(ClassRoom.teacher_id).where(ClassRoom.branch_id == values.target_branch_id))))
        rows = (await db.execute(query)).scalars().unique().all()
        people = [(row, None, row.id) for row in rows]
    unique = {}
    for person, parent_id, user_id in people:
        if values.channel == "EMAIL":
            address = person.email
        elif values.channel == "WHATSAPP":
            address = getattr(person, "whatsapp_phone", None) or person.phone
        else:
            address = getattr(person, "sms_phone", None) or person.phone
        if not address or not address.strip():
            continue
        address = address.strip()
        unique.setdefault(address.lower() if values.channel == "EMAIL" else address,
            dict(recipient_address=address, recipient_name=f"{person.first_name} {person.last_name}",
                parent_id=parent_id, user_id=user_id))
    return list(unique.values())


async def notification(db, job_id):
    return (await db.execute(select(NotificationJob).where(NotificationJob.reference_type == "BROADCAST",
        NotificationJob.reference_id == job_id))).scalar_one_or_none()


async def delivery_rows(db, job_id):
    return (await db.execute(select(NotificationRecipient).join(NotificationJob,
        NotificationJob.id == NotificationRecipient.notification_job_id).where(NotificationJob.reference_type == "BROADCAST",
        NotificationJob.reference_id == job_id))).scalars().all()


async def serialize(db, job, preloaded=None):
    if preloaded is None:
        delivery = await notification(db, job.id)
        rows = await delivery_rows(db, job.id) if delivery else []
    else:
        delivery, rows = preloaded
    sent = sum(row.status == NotificationStatus.SENT for row in rows)
    failed = sum(row.status == NotificationStatus.FAILED for row in rows)
    state = job.status
    if delivery:
        state = {NotificationStatus.SENT: "COMPLETED", NotificationStatus.PENDING: "QUEUED",
            NotificationStatus.FAILED: "FAILED", NotificationStatus.CANCELLED: "CANCELLED"}[delivery.status]
    return {"id": str(job.id), "title": job.title, "message_content": job.message_content,
        "target_audience": job.target_audience, "target_class_id": str(job.target_class_id) if job.target_class_id else None,
        "target_branch_id": str(job.target_branch_id) if job.target_branch_id else None,
        "channel": job.channel, "status": state, "total_recipients": len(rows) if delivery else job.total_recipients,
        "sent_count": sent, "failed_count": failed, "created_by": str(job.created_by) if job.created_by else None,
        "created_at": job.created_at.isoformat(), "scheduled_for": stored_schedule(job.scheduled_for).isoformat() if job.scheduled_for else None,
        "sent_at": delivery.processed_at.isoformat() if delivery and delivery.status == NotificationStatus.SENT and delivery.processed_at else None}


async def records(db, status=None, created_by=None, start_date=None, end_date=None, limit=100, offset=0):
    from collections import defaultdict
    from datetime import time, timedelta
    query = select(BroadcastJob).outerjoin(NotificationJob,
        (NotificationJob.reference_type == "BROADCAST") & (NotificationJob.reference_id == BroadcastJob.id))
    if status:
        requested = status.upper()
        equivalent = {"COMPLETED": NotificationStatus.SENT, "QUEUED": NotificationStatus.PENDING,
            "FAILED": NotificationStatus.FAILED, "CANCELLED": NotificationStatus.CANCELLED}.get(requested)
        condition = (NotificationJob.id.is_(None) & (BroadcastJob.status == requested))
        if equivalent:
            condition = or_(condition, NotificationJob.status == equivalent)
        query = query.where(condition)
    query = query.order_by(BroadcastJob.created_at.desc()).limit(limit).offset(offset)
    if created_by:
        query = query.where(BroadcastJob.created_by == created_by)
    if start_date and end_date and end_date < start_date:
        raise ValidationException("Tarih aralığı geçersiz")
    if start_date:
        query = query.where(BroadcastJob.created_at >= schedule(datetime.combine(start_date, time.min)))
    if end_date:
        query = query.where(BroadcastJob.created_at < schedule(datetime.combine(end_date + timedelta(days=1), time.min)))
    jobs = (await db.execute(query)).scalars().all()
    ids = [job.id for job in jobs]
    deliveries = (await db.execute(select(NotificationJob).where(NotificationJob.reference_type == "BROADCAST",
        NotificationJob.reference_id.in_(ids)))).scalars().all() if ids else []
    by_id = {row.reference_id: row for row in deliveries}
    recipient_rows = (await db.execute(select(NotificationRecipient).where(NotificationRecipient.notification_job_id.in_(
        [row.id for row in deliveries])))).scalars().all() if deliveries else []
    targets = defaultdict(list)
    for row in recipient_rows:
        targets[row.notification_job_id].append(row)
    result = []
    for job in jobs:
        delivery = by_id.get(job.id)
        row = await serialize(db, job, (delivery, targets[delivery.id] if delivery else []))
        if not status or row["status"] == status.upper():
            result.append(row)
    return result


async def edit(db, tenant, job, values):
    await validate(db, tenant, values)
    config = await configuration(db, job)
    if config is None:
        raise ValidationException("Eski toplu ileti için yeni bir taslak oluşturun")
    targets = await recipients(db, config.organization_id, values)
    fields = {key: getattr(values, key) for key in ("title", "message_content", "target_audience",
        "target_class_id", "target_branch_id", "channel")}
    fields.update(scheduled_for=schedule(values.scheduled_for), total_recipients=len(targets))
    changed = await db.execute(update(BroadcastJob).where(BroadcastJob.id == job.id, BroadcastJob.status == "DRAFT").values(**fields))
    if changed.rowcount != 1:
        raise ConflictException("Yalnız taslak ileti düzenlenebilir")
    config.data = {"target_role": values.target_role}
    config.branch_id, config.class_id = values.target_branch_id, values.target_class_id
    await db.flush()
    return await serialize(db, job)


async def create(db, tenant, values):
    await validate(db, tenant, values)
    targets = await recipients(db, tenant.organization_id, values)
    job = BroadcastJob(title=values.title.strip(), message_content=values.message_content.strip(),
        target_audience=values.target_audience, target_class_id=values.target_class_id,
        target_branch_id=values.target_branch_id, channel=values.channel,
        scheduled_for=schedule(values.scheduled_for), status="DRAFT", total_recipients=len(targets),
        sent_count=0, failed_count=0, created_by=tenant.user_id)
    db.add(job)
    await db.flush()
    db.add(OperationalRecord(organization_id=tenant.organization_id, branch_id=values.target_branch_id,
        class_id=values.target_class_id, created_by=tenant.user_id, kind="BROADCAST_CONFIG",
        reference_key=str(job.id), data={"target_role": values.target_role}))
    await db.flush()
    return await serialize(db, job)


async def send(db, tenant, job_id):
    from types import SimpleNamespace
    job = await get(db, job_id)
    config = await configuration(db, job)
    if config is None:
        raise ValidationException("Eski toplu ileti doğrulanamıyor; yeni bir taslak oluşturun")
    values = SimpleNamespace(**{key: getattr(job, key) for key in ("title", "message_content", "target_audience",
        "target_class_id", "target_branch_id", "channel", "scheduled_for")}, **config.data)
    await validate(db, tenant, values)
    targets = await recipients(db, config.organization_id, values)
    if not targets:
        raise ValidationException("Seçilen hedefte bu kanal için iletişim adresi bulunamadı")
    changed = await db.execute(update(BroadcastJob).where(BroadcastJob.id == job.id, BroadcastJob.status == "DRAFT")
        .values(status="QUEUED", total_recipients=len(targets)))
    if changed.rowcount != 1:
        raise ConflictException("Bu toplu ileti daha önce kuyruğa alındı veya iptal edildi")
    delivery = NotificationJob(organization_id=config.organization_id, branch_id=job.target_branch_id,
        channel=NotificationChannel(job.channel), subject=job.title, body=job.message_content,
        status=NotificationStatus.PENDING, scheduled_at=stored_schedule(job.scheduled_for) or now(), reference_type="BROADCAST",
        reference_id=job.id, created_by=tenant.user_id)
    db.add(delivery)
    await db.flush()
    db.add_all([NotificationRecipient(notification_job_id=delivery.id, **target) for target in targets])
    await db.flush()
    return await serialize(db, job)


async def cancel(db, job_id):
    job = await get(db, job_id)
    delivery = await notification(db, job_id)
    if delivery:
        updated = await db.execute(update(NotificationJob).where(NotificationJob.id == delivery.id,
            NotificationJob.status.in_([NotificationStatus.PENDING, NotificationStatus.FAILED]),
            or_(NotificationJob.locked_until.is_(None), NotificationJob.locked_until <= now()))
            .values(status=NotificationStatus.CANCELLED))
        if updated.rowcount != 1:
            raise ConflictException("İşlenmekte olan veya tamamlanan ileti iptal edilemez")
        await db.execute(update(NotificationRecipient).where(NotificationRecipient.notification_job_id == delivery.id,
            NotificationRecipient.status != NotificationStatus.SENT).values(status=NotificationStatus.CANCELLED))
    job.status = "CANCELLED"
    await db.flush()
    return await serialize(db, job)
