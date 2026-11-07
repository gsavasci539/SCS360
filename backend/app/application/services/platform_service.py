from calendar import monthrange
from datetime import UTC, datetime
import hashlib
import hmac
import json
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.application.services.subscription_access import evaluate, utc
from app.core.config import get_settings
from app.core.exceptions import AppException, ConflictException, NotFoundException
from app.core.role_catalog import default_permissions, institution_roles
from app.core.security import hash_password
from app.domain.entities.saas import OrganizationSubscription, SubscriptionPlan
from app.infrastructure.models.models import AuditAction, AuditLog, Branch, Organization, Permission, Role, Student, User


def plan_data(plan):
    return {"id": str(plan.id), "code": plan.code, "name": plan.name, "branch_limit": plan.branch_limit,
        "student_limit": plan.student_limit, "user_limit": plan.user_limit, "price": str(plan.price),
        "currency": plan.currency, "period_months": plan.period_months, "is_active": plan.is_active}


def add_months(instant, months):
    index = instant.year * 12 + instant.month - 1 + months
    year, month = divmod(index, 12)
    return instant.replace(year=year, month=month + 1, day=min(instant.day, monthrange(year, month + 1)[1]))


async def lock_organization(db, identifier, include_deleted=False):
    table = Organization.__table__
    query = table.update().where(table.c.id == identifier)
    if not include_deleted:
        query = query.where(table.c.deleted_at.is_(None))
    changed = await db.execute(query.values(updated_at=table.c.updated_at))
    if changed.rowcount != 1:
        raise NotFoundException("Kurum bulunamadı")
    return (await db.execute(select(Organization).where(Organization.id == identifier).execution_options(populate_existing=True))).scalar_one()


async def get_plan(db, identifier):
    plan = (await db.execute(select(SubscriptionPlan).where(SubscriptionPlan.id == identifier))).scalar_one_or_none()
    if plan is None:
        raise NotFoundException("Paket bulunamadı")
    return plan


async def set_account_status(db, actor, identifier, enabled):
    org = await lock_organization(db, identifier)
    org.is_active, org.updated_by = enabled, actor.id
    member = (await db.execute(select(OrganizationSubscription).where(
        OrganizationSubscription.organization_id == org.id).execution_options(populate_existing=True))).scalar_one_or_none()
    if member:
        member.admin_status = "ACTIVE" if enabled else "SUSPENDED"
    audit(db, actor, org, "TENANT_OPENED" if enabled else "TENANT_CLOSED", {"is_active": enabled})
    await db.flush()
    return org


def audit(db, actor, org, event, values, identifier=None):
    db.add(AuditLog(id=identifier or uuid4(), organization_id=org.id if org else None, user_id=actor.id,
        action=AuditAction.UPDATE, entity_type="platform_subscription", entity_id=org.id if org else None,
        new_values={"event": event, **values}))


async def commit(db):
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ConflictException("Kayıt veya istek kimliği zaten kullanılmış") from None


async def create_plan(db, actor, body):
    plan = SubscriptionPlan(**body.model_dump())
    db.add(plan)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise ConflictException("Paket kodu zaten kullanılmış") from None
    audit(db, actor, None, "PLAN_CREATED", {"plan_id": str(plan.id)})
    await commit(db)
    return plan_data(plan)


async def provision(db, actor, body):
    try:
        return await _provision(db, actor, body)
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictException("Hesap veya istek kimliği başka bir kayıtla çakışıyor") from exc


async def _provision(db, actor, body):
    table = User.__table__
    if actor is not None:
        await db.execute(table.update().where(table.c.id == actor.id).values(updated_at=table.c.updated_at))
    else:
        # One platform mutex also serializes the first permission-catalog setup
        # across different public plans, without editing the operator account.
        mutex = (await db.execute(select(table.c.id).where(table.c.is_super_admin.is_(True), table.c.deleted_at.is_(None)).order_by(table.c.id).limit(1))).scalar_one_or_none()
        if mutex is None:
            raise AppException("Kurum üyeliği kurulumu henüz hazır değil", status_code=503)
        await db.execute(table.update().where(table.c.id == mutex).values(updated_at=table.c.updated_at))
    event = "TENANT_PROVISIONED" if actor is not None else "TENANT_SIGNUP"
    # HMAC keeps the provisioning password out of logs and out of an offline
    # password-guessing hash while still binding retries to the exact request.
    digest = hmac.new(get_settings().JWT_SECRET_KEY.encode(), json.dumps(body.model_dump(mode="json", exclude={"request_id"}), sort_keys=True).encode(), hashlib.sha256).hexdigest()
    prior = (await db.execute(select(AuditLog).where(AuditLog.id == body.request_id))).scalar_one_or_none()
    if prior:
        data = prior.new_values or {}
        if (actor is not None and prior.user_id != actor.id) or data.get("event") != event or not hmac.compare_digest(data.get("digest", ""), digest):
            raise ConflictException("İstek kimliği başka bir kurum oluşturma işleminde kullanılmış")
        return data["response"]
    if (await db.execute(select(table.c.id).where(func.lower(table.c.email) == str(body.owner_email).lower()))).first():
        raise ConflictException("Kurum sahibi e-postası zaten kayıtlı")
    plan = await get_plan(db, body.plan_id)
    if not plan.is_active:
        raise ConflictException("Paket yeni üyeliğe kapalı")
    start = utc(body.period_start or datetime.now(UTC))
    end = utc(body.period_end) if body.period_end else add_months(start, plan.period_months)
    if end <= start:
        raise AppException("Üyelik bitişi başlangıçtan sonra olmalı", status_code=422)
    actor_id = actor.id if actor is not None else None
    org = Organization(id=uuid4(), name=body.name, created_by=actor_id, updated_by=actor_id)
    db.add(org); await db.flush()
    codes = default_permissions("owner")
    permissions = list((await db.execute(select(Permission).where(Permission.code.in_(codes)))).scalars())
    known = {row.code for row in permissions}
    permissions.extend(Permission(code=code, name=code, module=code.split(".")[0]) for code in sorted(codes - known))
    roles = institution_roles(org.id, permissions)
    role = next(row for row in roles if row.slug == "owner")
    db.add_all(roles)
    owner = User(id=uuid4(), organization_id=org.id, email=str(body.owner_email).lower(), password_hash=hash_password(body.owner_password),
        first_name=body.owner_first_name, last_name=body.owner_last_name, roles=[role], created_by=actor_id, updated_by=actor_id)
    membership = OrganizationSubscription(organization_id=org.id, owner_user_id=owner.id, plan_id=plan.id, admin_status="ACTIVE",
        package_snapshot=plan_data(plan), period_start=start if actor is not None else None, period_end=end if actor is not None else None)
    # Flush the new owner's role/account before its subscription FK. This is
    # still one transaction; PostgreSQL enforces this dependency immediately.
    db.add(owner)
    await db.flush()
    db.add(membership)
    result = {"organization_id": str(org.id), "owner_user_id": str(owner.id), "owner_email": owner.email, "period_end": end.isoformat() if actor is not None else None}
    audit(db, actor or owner, org, event, {"digest": digest, "response": result}, body.request_id)
    await commit(db)
    return result


async def usage(db, org_id):
    result = {}
    for model, key in ((Branch, "branch_limit"), (Student, "student_limit"), (User, "user_limit")):
        table = model.__table__
        query = select(func.count()).select_from(table).where(table.c.organization_id == org_id, table.c.deleted_at.is_(None))
        if model is User:
            query = query.where(table.c.is_super_admin.is_(False))
        result[key] = (await db.execute(query)).scalar_one()
    return result


async def set_membership(db, actor, org_id, body):
    org = await lock_organization(db, org_id)
    plan = await get_plan(db, body.plan_id)
    start, end = utc(body.period_start), utc(body.period_end)
    if end <= start:
        raise AppException("Üyelik bitişi başlangıçtan sonra olmalı", status_code=422)
    member = (await db.execute(select(OrganizationSubscription).where(OrganizationSubscription.organization_id == org_id))).scalar_one_or_none()
    if member is None:
        member = OrganizationSubscription(organization_id=org_id)
        db.add(member)
    member.plan_id, member.package_snapshot = plan.id, plan_data(plan)
    if "owner_user_id" in body.model_fields_set:
        if body.owner_user_id is not None:
            table = User.__table__
            owner = (await db.execute(select(table.c.id).where(table.c.id == body.owner_user_id, table.c.organization_id == org.id,
                table.c.deleted_at.is_(None), table.c.status == "ACTIVE", table.c.is_super_admin.is_(False)))).first()
            if owner is None:
                raise AppException("Ödeme yetkilisi bu kurumun aktif kullanıcısı olmalı", status_code=422)
        member.owner_user_id = body.owner_user_id
    member.period_start, member.period_end, member.admin_status = start, end, body.admin_status
    audit(db, actor, org, "MEMBERSHIP_CONFIGURED", {"plan_id": str(plan.id), "period_end": end.isoformat(), "admin_status": body.admin_status})
    await commit(db)
    return {"organization_id": str(org.id), "access": evaluate(member, active=org.is_active), "usage": await usage(db, org.id)}
