from hashlib import sha256
import json

from fastapi import HTTPException
from sqlalchemy import func, or_, select

from app.application.services.consent_service import utc_iso
from app.core.dates import school_day_bounds, school_today
from app.domain.entities.pickup import PickupAuthorization, PickupLog
from app.infrastructure.models.models import AuditAction, AuditLog, Student


def effective_status(row, child):
    if row.status != "ACTIVE":
        return row.status
    if child is None or child.status != "ACTIVE" or child.deleted_at is not None:
        return "BLOCKED"
    if not (row.authorized_person_id or "").strip():
        return "REVIEW_REQUIRED"
    today = school_today()
    return "FUTURE" if row.valid_from > today else "EXPIRED" if row.valid_until and row.valid_until < today else "ACTIVE"


def authorization_data(row, child):
    return {"id": str(row.id), "student_id": str(row.student_id), "authorized_person_name": row.authorized_person_name,
        "authorized_person_id": row.authorized_person_id, "relationship": row.relationship, "phone": row.phone,
        "photo_url": row.photo_url, "valid_from": row.valid_from.isoformat(), "valid_until": row.valid_until.isoformat() if row.valid_until else None,
        "notes": row.notes, "status": row.status, "effective_status": effective_status(row, child),
        "created_by": str(row.created_by) if row.created_by else None, "created_at": utc_iso(row.created_at), "updated_at": utc_iso(row.updated_at)}


def fingerprint(tenant, body):
    value = {"actor": str(tenant.user_id), **body.model_dump(mode="json", exclude={"request_id"})}
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def audit(db, tenant, child, row, action, values):
    db.add(AuditLog(organization_id=child.organization_id, branch_id=child.branch_id, user_id=tenant.user_id,
        action=AuditAction.CREATE if action == "PICKUP_AUTHORIZATION_CREATED" else AuditAction.UPDATE,
        entity_type=action, entity_id=row.id, new_values=values))


async def replay(db, tenant, body):
    row = (await db.execute(select(PickupAuthorization).where(PickupAuthorization.id == body.request_id))).scalar_one_or_none()
    if row is None:
        exists = (await db.execute(select(PickupAuthorization.__table__.c.id).where(PickupAuthorization.__table__.c.id == body.request_id))).first()
        if exists:
            raise HTTPException(409, "İstek kimliği kullanılamıyor; yeni işlem başlatın")
        return None
    event = (await db.execute(select(AuditLog).where(AuditLog.entity_id == row.id, AuditLog.entity_type == "PICKUP_AUTHORIZATION_CREATED"))).scalars().first()
    if row.student_id != body.student_id or row.created_by != tenant.user_id or not event or (event.new_values or {}).get("request_sha256") != fingerprint(tenant, body):
        raise HTTPException(409, "İstek kimliği farklı bir teslim yetkisi için kullanılmış")
    return row


async def check_overlap(db, body, exclude=None):
    query = select(PickupAuthorization.id).where(PickupAuthorization.student_id == body.student_id,
        PickupAuthorization.authorized_person_id == body.authorized_person_id, PickupAuthorization.status == "ACTIVE",
        or_(PickupAuthorization.valid_until.is_(None), PickupAuthorization.valid_until >= body.valid_from))
    if body.valid_until:
        query = query.where(PickupAuthorization.valid_from <= body.valid_until)
    if exclude:
        query = query.where(PickupAuthorization.id != exclude)
    if (await db.execute(query.limit(1))).first():
        raise HTTPException(409, "Aynı öğrenci ve kimlik için çakışan etkin teslim yetkisi var")


async def summary(db, day=None, student_id=None):
    day = day or school_today(); today = school_today(); start, end = school_day_bounds(day)
    total = select(func.count(PickupAuthorization.id))
    current = select(PickupAuthorization).join(Student, Student.id == PickupAuthorization.student_id).where(
        Student.status == "ACTIVE", Student.deleted_at.is_(None), PickupAuthorization.status == "ACTIVE",
        PickupAuthorization.authorized_person_id.is_not(None), func.length(func.trim(PickupAuthorization.authorized_person_id)) > 0,
        PickupAuthorization.valid_from <= today, or_(PickupAuthorization.valid_until.is_(None), PickupAuthorization.valid_until >= today))
    logs = select(func.count(PickupLog.id), func.count(func.distinct(PickupLog.student_id))).where(PickupLog.pickup_time >= start, PickupLog.pickup_time < end)
    if student_id:
        total = total.where(PickupAuthorization.student_id == student_id); current = current.where(PickupAuthorization.student_id == student_id)
        logs = logs.where(PickupLog.student_id == student_id)
    count, unique = (await db.execute(logs)).one()
    groups = (await db.execute(current.with_only_columns(PickupAuthorization.student_id, PickupAuthorization.authorized_person_id)
        .group_by(PickupAuthorization.student_id, PickupAuthorization.authorized_person_id).having(func.count(PickupAuthorization.id) > 1))).all()
    return {"date": day.isoformat(), "total_pickups": count, "unique_students": unique,
        "total_authorizations": (await db.execute(total)).scalar() or 0,
        "valid_authorizations": (await db.execute(current.with_only_columns(func.count(PickupAuthorization.id)))).scalar() or 0,
        "duplicate_identity_groups": len(groups)}
