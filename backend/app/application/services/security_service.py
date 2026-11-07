"""Student credentials and operator-authenticated gate records."""
from datetime import UTC, datetime
from hashlib import sha256
import json

from fastapi import HTTPException
from sqlalchemy import func, or_, select, update

from app.application.services.consent_service import utc_iso
from app.core.dates import school_day_bounds
from app.core.tenant_guard import criteria
from app.domain.entities.security import DigitalIdToken, GateLog
from app.infrastructure.models.models import AuditAction, AuditLog, Branch, ClassRoom, Student, User


def utc(value):
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def active(token):
    return token.status == "ACTIVE" and (token.expires_at is None or utc(token.expires_at) > datetime.now(UTC))


def token_data(token, child=None):
    status = "EXPIRED" if token and token.status == "ACTIVE" and not active(token) else token.status if token else "NOT_ISSUED"
    if token and status == "ACTIVE" and child is not None and child.status != "ACTIVE":
        status = "BLOCKED"
    return {"id": str(token.id) if token else None, "student_id": str(child.id if child else token.student_id),
        "student_name": f"{child.first_name} {child.last_name}" if child else None,
        "student_number": child.student_number if child else None, "token": token.token if token else None,
        "barcode_number": token.barcode_number if token else None, "status": status, "stored_status": token.status if token else None,
        "qr_code_url": f"/api/security/digital-ids/{token.id}/qr-code" if token and status == "ACTIVE" else None,
        "expires_at": utc_iso(token.expires_at) if token else None, "issued_at": utc_iso(token.issued_at) if token else None,
        "last_used_at": utc_iso(token.last_used_at) if token else None}


async def student(db, identifier):
    child = (await db.execute(select(Student).where(Student.id == identifier, Student.deleted_at.is_(None)))).scalar_one_or_none()
    if child is None:
        raise HTTPException(404, "Öğrenci bulunamadı veya erişim kapsamı dışında")
    return child


async def lock_student(db, identifier):
    changed = await db.execute(update(Student).where(Student.id == identifier, Student.deleted_at.is_(None))
        .values(updated_at=Student.updated_at).execution_options(synchronize_session=False))
    if changed.rowcount != 1:
        raise HTTPException(404, "Öğrenci erişim kapsamı dışında")
    return (await db.execute(select(Student).where(Student.id == identifier).execution_options(populate_existing=True))).scalar_one()


async def latest(db, child):
    # Multiple active legacy rows are preserved; reading chooses the newest valid
    # credential and never issues or revokes a credential as a side effect.
    query = select(DigitalIdToken).where(DigitalIdToken.student_id == child.id)
    valid = query.where(DigitalIdToken.status == "ACTIVE", or_(DigitalIdToken.expires_at.is_(None), DigitalIdToken.expires_at > datetime.now(UTC)))
    order = (DigitalIdToken.issued_at.desc(), DigitalIdToken.id.desc())
    token = (await db.execute(valid.order_by(*order).limit(1))).scalar_one_or_none()
    return token or (await db.execute(query.order_by(*order).limit(1))).scalar_one_or_none()


def audit(db, tenant, child, identifier, action, values):
    db.add(AuditLog(organization_id=child.organization_id, branch_id=child.branch_id, user_id=tenant.user_id,
        action=AuditAction.CREATE if action == "STUDENT_ID_ISSUED" else AuditAction.UPDATE,
        entity_type=action, entity_id=identifier, new_values=values))


async def token_details(db, token, child):
    result = token_data(token, child)
    result["class_name"] = (await db.execute(select(ClassRoom.name).where(ClassRoom.id == child.class_id))).scalar_one_or_none() if child.class_id else None
    result["branch_name"] = (await db.execute(select(Branch.name).where(Branch.id == child.branch_id))).scalar_one_or_none() if child.branch_id else None
    return result


async def options(db, student_id=None, search=""):
    from app.application.services.student_choices import options as choices
    return await choices(db, student_id, search)


def same_issue(token, body):
    return (token.student_id == body.student_id and token.expires_at is not None
        and (utc(token.expires_at) - utc(token.issued_at)).total_seconds() == body.expires_hours * 3600)


def fingerprint(tenant, token, body):
    encoded = json.dumps({"token_id": str(token.id), "actor": str(tenant.user_id), "direction": body.direction,
        "location": body.gate_location, "method": body.verification_method, "notes": body.notes}, sort_keys=True, ensure_ascii=False)
    return sha256(encoded.encode("utf-8")).hexdigest()


def recorded(log, child, repeated=False):
    return {"authorized": True, "status": "AUTHORIZED", "message": "Öğrenci kimliği ve kapı kaydı doğrulandı",
        "student_id": str(child.id), "student_name": f"{child.first_name} {child.last_name}", "student_photo": getattr(child, "photo_url", None),
        "branch_id": str(log.branch_id) if log.branch_id else None, "verified_by": str(log.verified_by) if log.verified_by else None,
        "parent_pickup_permission": log.parent_pickup_permission, "service_permission": log.service_permission,
        "verification_scope": "STUDENT_ID_ONLY", "gate_log_id": str(log.id), "timestamp": utc_iso(log.created_at), "repeated_request": repeated}


def unauthorized():
    return {"authorized": False, "status": "UNAUTHORIZED", "message": "Geçerli ve erişilebilir öğrenci kimliğiyle eşleşmedi",
        "student_id": None, "student_name": None, "student_photo": None, "parent_pickup_permission": False,
        "service_permission": False, "gate_log_id": None, "timestamp": datetime.now(UTC).isoformat(), "verification_scope": "STUDENT_ID_ONLY"}


async def replay(db, tenant, child, token, body):
    log = (await db.execute(select(GateLog).where(GateLog.id == body.request_id))).scalar_one_or_none()
    if log is None:
        # Do not disclose a colliding request UUID from another scope.
        exists = (await db.execute(select(GateLog.__table__.c.id).where(GateLog.__table__.c.id == body.request_id))).first()
        if exists:
            raise HTTPException(409, "İstek kimliği kullanılamıyor; yeni işlem başlatın")
        return None
    event = (await db.execute(select(AuditLog).where(AuditLog.entity_id == log.id,
        AuditLog.entity_type == "STUDENT_GATE_VERIFIED"))).scalars().first()
    if (log.student_id != child.id or log.verified_by != tenant.user_id or not event
        or (event.new_values or {}).get("request_sha256") != fingerprint(tenant, token, body)):
        raise HTTPException(409, "İstek kimliği farklı bir kapı işlemi için kullanılmış")
    return recorded(log, child, True)


async def logs_data(db, logs):
    async def names(model, ids):
        return {row.id: f"{row.first_name} {row.last_name}" for row in (await db.execute(
            select(model.id, model.first_name, model.last_name).where(model.id.in_(ids)))).all()} if ids else {}
    children = await names(Student, {row.student_id for row in logs if row.student_id})
    people = await names(User, {identifier for row in logs for identifier in (row.user_id, row.verified_by) if identifier})
    branches = {row.id: row.name for row in (await db.execute(select(Branch.id, Branch.name).where(Branch.id.in_(
        {row.branch_id for row in logs if row.branch_id})))).all()} if logs else {}
    return [{"id": str(row.id), "student_id": str(row.student_id) if row.student_id else None, "student_name": children.get(row.student_id),
        "user_id": str(row.user_id) if row.user_id else None, "user_name": people.get(row.user_id),
        "branch_id": str(row.branch_id) if row.branch_id else None, "branch_name": branches.get(row.branch_id),
        "verified_by": str(row.verified_by) if row.verified_by else None, "verified_by_name": people.get(row.verified_by),
        "direction": row.direction, "status": row.status, "gate_location": row.gate_location,
        "verification_method": row.verification_method, "parent_pickup_permission": row.parent_pickup_permission,
        "service_permission": row.service_permission, "notes": row.notes, "created_at": utc_iso(row.created_at)} for row in logs]


async def stats(db, tenant, day, student_id=None):
    start, end = school_day_bounds(day)
    daily = select(GateLog).where(GateLog.created_at >= start, GateLog.created_at < end)
    if student_id:
        daily = daily.where(GateLog.student_id == student_id)
    authorized = daily.where(GateLog.status == "AUTHORIZED")
    async def count(query):
        return (await db.execute(query.with_only_columns(func.count(GateLog.id)).order_by(None))).scalar() or 0
    entries = await count(authorized.where(GateLog.direction == "IN"))
    exits = await count(authorized.where(GateLog.direction == "OUT"))
    statuses = (await db.execute(daily.with_only_columns(GateLog.status, func.count(GateLog.id)).group_by(GateLog.status))).all()
    table = GateLog.__table__
    query = select(table.c.student_id.label("student_id"), table.c.direction.label("direction"),
        func.dense_rank().over(partition_by=table.c.student_id, order_by=table.c.created_at.desc()).label("rank")).where(
        table.c.student_id.is_not(None), table.c.created_at < end, table.c.status == "AUTHORIZED")
    if student_id:
        query = query.where(table.c.student_id == student_id)
    if not tenant.is_super_admin:
        # The window is a Core subquery. Apply scope explicitly rather than
        # assuming ORM loader criteria will survive the subquery boundary.
        query = query.where(criteria(GateLog, tenant, db.info.get("accessible_student_ids")))
    ranked = query.subquery()
    last = select(ranked.c.student_id, func.min(ranked.c.direction).label("low"), func.max(ranked.c.direction).label("high"))
    last = last.where(ranked.c.rank == 1).group_by(ranked.c.student_id).subquery()
    inside = (await db.execute(select(func.count()).select_from(last).where(last.c.low == "IN", last.c.high == "IN"))).scalar() or 0
    unknown = (await db.execute(select(func.count()).select_from(last).where(last.c.low != last.c.high))).scalar() or 0
    return {"total_entries": entries, "total_exits": exits, "currently_in_school": inside, "presence_review_required": unknown,
        "date": day.isoformat(), "by_status": dict(statuses)}
