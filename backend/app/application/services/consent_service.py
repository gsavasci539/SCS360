"""Institution-owned documents and authenticated guardian decisions."""
from datetime import UTC, datetime
from hashlib import sha256

from sqlalchemy import exists, func, or_, select, update

from app.core.dates import school_today
from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException, ValidationException
from app.domain.entities.consents import ConsentDocument, StudentConsent
from app.infrastructure.models.models import AuditAction, AuditLog, Organization, Parent, Student, StudentParent
from app.application.services.parent_data_service import child


async def form_organization(db, tenant, requested=None):
    identifier = requested or tenant.organization_id
    if identifier is None:
        raise ValidationException("Belgenin kurumu seçilmelidir")
    if not tenant.is_super_admin and identifier != tenant.organization_id:
        raise ForbiddenException("Başka kurum için belge oluşturulamaz")
    organization = (await db.execute(select(Organization).where(Organization.id == identifier,
        Organization.deleted_at.is_(None), Organization.is_active.is_(True)))).scalar_one_or_none()
    if organization is None:
        raise NotFoundException("Aktif kurum bulunamadı")
    return identifier


def utc_iso(value):
    return value.replace(tzinfo=UTC).isoformat() if value and value.tzinfo is None else value.isoformat() if value else None


def document_data(doc):
    return {"id": str(doc.id), "organization_id": str(doc.organization_id) if doc.organization_id else None,
        "title": doc.title, "document_type": doc.document_type, "content": doc.content,
        "version": doc.version, "content_sha256": sha256((doc.content or "").encode("utf-8")).hexdigest(),
        "effective_date": doc.effective_date.isoformat(), "is_active": doc.is_active,
        "created_by": str(doc.created_by), "created_at": utc_iso(doc.created_at)}


async def lock_document(db, identifier):
    # All decisions and edits share this write lock, including the first decision.
    # A no-op UPDATE serializes on SQLite as well as PostgreSQL.
    result = await db.execute(update(ConsentDocument).where(ConsentDocument.id == identifier)
        .values(is_active=ConsentDocument.is_active).execution_options(synchronize_session=False))
    if result.rowcount != 1:
        raise NotFoundException("Belge bulunamadı")
    return (await db.execute(select(ConsentDocument).where(ConsentDocument.id == identifier)
        .execution_options(populate_existing=True))).scalar_one()


async def edit_document(db, identifier, payload):
    doc = await lock_document(db, identifier)
    # An institution-wide document stays frozen even when this operator cannot
    # read the branch/student that supplied an earlier decision.
    if (await db.execute(select(exists().where(StudentConsent.__table__.c.consent_document_id == doc.id)))).scalar():
        raise ConflictException("Karar verilmiş belgenin metni değiştirilemez; yeni sürüm için yeni belge oluşturun")
    if payload.organization_id and payload.organization_id != doc.organization_id:
        raise ValidationException("Belgenin kurumu değiştirilemez")
    for field in ("title", "document_type", "content", "version", "effective_date"):
        setattr(doc, field, getattr(payload, field))
    await db.flush()
    await db.refresh(doc)
    return document_data(doc)


async def decide(db, *, actor_id, student_id, document_id, parent_id, status, method,
                 signature=None, notes=None, ip=None, user_agent=None, expected_version=None, expected_hash=None):
    doc = await lock_document(db, document_id)
    if expected_version is not None and (expected_version != doc.version or expected_hash != sha256((doc.content or "").encode("utf-8")).hexdigest()):
        raise ConflictException("Belge değişti; güncel metni okuyarak yeniden karar verin")
    if not doc.is_active or doc.effective_date > school_today() or not (doc.content or "").strip():
        raise ConflictException("Belge şu anda karara açık değil")
    student = (await db.execute(select(Student).where(Student.id == student_id,
        Student.deleted_at.is_(None), Student.organization_id == doc.organization_id))).scalar_one_or_none()
    if student is None or doc.organization_id is None:
        raise NotFoundException("Bu belge için öğrenci bulunamadı")
    guardian = (await db.execute(select(Parent).join(StudentParent, StudentParent.parent_id == Parent.id)
        .where(Parent.id == parent_id, Parent.organization_id == student.organization_id,
            Parent.deleted_at.is_(None), StudentParent.student_id == student.id))).scalar_one_or_none()
    if guardian is None:
        raise ValidationException("Seçilen veli bu öğrencinin kayıtlı velisi değil")
    if method == "PARENT_PORTAL" and guardian.user_id != actor_id:
        raise ForbiddenException("Yalnız kendi veli kararınızı kaydedebilirsiniz")
    rows = (await db.execute(select(StudentConsent).where(StudentConsent.student_id == student.id,
        StudentConsent.consent_document_id == doc.id))).scalars().all()
    if len(rows) > 1:
        raise ConflictException("Bu belge için birden fazla eski karar var; kayıtlar incelenmeli")
    record = rows[0] if rows else StudentConsent(student_id=student.id, consent_document_id=doc.id)
    if rows and record.consent_status == status and record.parent_id == parent_id and record.consent_method == method and record.signature_data == signature and record.notes == notes:
        return record
    old = {"status": record.consent_status, "parent_id": str(record.parent_id) if record.parent_id else None} if rows else None
    record.parent_id, record.consent_status, record.consent_method = parent_id, status, method
    record.signature_data, record.notes = signature, notes
    record.consented_at, record.ip_address, record.user_agent = datetime.now(UTC), ip, user_agent
    db.add(record)
    await db.flush()
    db.add(AuditLog(organization_id=student.organization_id, branch_id=student.branch_id, user_id=actor_id,
        action=AuditAction.UPDATE if rows else AuditAction.CREATE, entity_type="student_consent", entity_id=record.id,
        old_values=old, new_values={"status": status, "method": method, "parent_id": str(parent_id),
            "student_id": str(student.id), "document_id": str(doc.id), "version": doc.version,
            "content_sha256": sha256((doc.content or "").encode("utf-8")).hexdigest()}, ip_address=ip, user_agent=user_agent))
    await db.flush()
    return record


async def parent_documents(db, user, student_id, limit, offset):
    _, student = await child(db, user, student_id)
    previous = exists().where(StudentConsent.student_id == student.id, StudentConsent.consent_document_id == ConsentDocument.id)
    docs = (await db.execute(select(ConsentDocument).where(ConsentDocument.organization_id == student.organization_id,
        or_((ConsentDocument.is_active.is_(True)) & (ConsentDocument.effective_date <= school_today()), previous))
        .order_by(ConsentDocument.effective_date.desc(), ConsentDocument.id).limit(limit).offset(offset))).scalars().all()
    records = (await db.execute(select(StudentConsent).where(StudentConsent.student_id == student.id,
        StudentConsent.consent_document_id.in_([doc.id for doc in docs])))).scalars().all() if docs else []
    grouped = {}
    for row in records:
        grouped.setdefault(row.consent_document_id, []).append(row)
    result = []
    for doc in docs:
        entries = grouped.get(doc.id, [])
        row = entries[0] if len(entries) == 1 else None
        result.append({**document_data(doc), "consent_status": row.consent_status if row else "REVIEW_REQUIRED" if entries else "PENDING",
            "consented_at": utc_iso(row.consented_at) if row else None,
            "can_decide": doc.is_active and doc.effective_date <= school_today() and len(entries) <= 1 and bool((doc.content or "").strip())})
    return result


async def options(db, tenant, organization_id=None, search="", student_id=None):
    organization_id = organization_id or tenant.organization_id
    if organization_id and not tenant.is_super_admin and organization_id != tenant.organization_id:
        raise ForbiddenException("Başka kurumun öğrencileri görüntülenemez")
    organizations = (await db.execute(select(Organization).where(Organization.deleted_at.is_(None), Organization.is_active.is_(True))
        .order_by(Organization.name).limit(100))).scalars().all()
    students, guardians = [], []
    if organization_id:
        query = select(Student).where(Student.organization_id == organization_id, Student.deleted_at.is_(None))
        if search:
            query = query.where(or_(Student.first_name.ilike(f"%{search}%"), Student.last_name.ilike(f"%{search}%")))
        students = (await db.execute(query.order_by(Student.first_name, Student.id).limit(101))).scalars().all()
        if student_id:
            guardians = (await db.execute(select(Parent).join(StudentParent, StudentParent.parent_id == Parent.id)
                .join(Student, Student.id == StudentParent.student_id).where(Student.id == student_id,
                    Student.organization_id == organization_id, Student.deleted_at.is_(None),
                    Parent.organization_id == organization_id, Parent.deleted_at.is_(None)))).scalars().all()
    return {"organizations": [{"id": str(row.id), "name": row.name} for row in organizations],
        "students": [{"id": str(row.id), "name": f"{row.first_name} {row.last_name}"} for row in students[:100]],
        "more_students": len(students) > 100,
        "parents": [{"id": str(row.id), "name": f"{row.first_name} {row.last_name}"} for row in guardians]}


async def list_decisions(db, student_id, document_id, status, limit, offset):
    query = select(StudentConsent)
    if student_id:
        query = query.where(StudentConsent.student_id == student_id)
    if document_id:
        query = query.where(StudentConsent.consent_document_id == document_id)
    if status:
        query = query.where(StudentConsent.consent_status == status.upper())
    rows = (await db.execute(query.order_by(StudentConsent.created_at.desc(), StudentConsent.id).limit(limit).offset(offset))).scalars().all()
    students = {row.id: f"{row.first_name} {row.last_name}" for row in (await db.execute(select(Student).where(Student.id.in_([row.student_id for row in rows])))).scalars()} if rows else {}
    parents = {row.id: f"{row.first_name} {row.last_name}" for row in (await db.execute(select(Parent).where(Parent.id.in_([row.parent_id for row in rows if row.parent_id])))).scalars()} if rows else {}
    docs = {row.id: row for row in (await db.execute(select(ConsentDocument).where(ConsentDocument.id.in_([row.consent_document_id for row in rows])))).scalars()} if rows else {}
    return [{"id": str(row.id), "student_id": str(row.student_id), "student_name": students.get(row.student_id),
        "consent_document_id": str(row.consent_document_id), "document_title": docs[row.consent_document_id].title if row.consent_document_id in docs else None,
        "document_version": docs[row.consent_document_id].version if row.consent_document_id in docs else None,
        "parent_id": str(row.parent_id) if row.parent_id else None, "parent_name": parents.get(row.parent_id),
        "consent_status": row.consent_status, "consent_method": row.consent_method,
        "consented_at": utc_iso(row.consented_at),
        "notes": row.notes, "created_at": utc_iso(row.created_at)} for row in rows]


async def summary(db, document_id):
    query = select(StudentConsent.consent_status, func.count(StudentConsent.id)).group_by(StudentConsent.consent_status)
    if document_id:
        query = query.where(StudentConsent.consent_document_id == document_id)
    counts = dict((await db.execute(query)).all())
    total = sum(counts.values())
    return {"total": total, "approved": counts.get("APPROVED", 0), "pending": counts.get("PENDING", 0),
        "rejected": counts.get("REJECTED", 0), "approval_rate": counts.get("APPROVED", 0) * 100 / total if total else 0}
