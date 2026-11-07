"""Enforce purchased capacities for all ORM creation/import paths atomically."""
from collections import defaultdict
from uuid import UUID

from sqlalchemy import event, func, inspect, select
from sqlalchemy.orm import Session

from app.application.services.subscription_access import evaluate
from app.core.exceptions import AppException
from app.domain.entities.saas import OrganizationSubscription
from app.infrastructure.models.models import Branch, Organization, Student, User

RESOURCES = {Branch: "branch_limit", Student: "student_limit", User: "user_limit"}


def identifier(value):
    return UUID(str(value)) if value is not None else None


def old_value(state, field, current):
    values = state.attrs[field].history.deleted
    return values[0] if values else current


@event.listens_for(Session, "before_flush")
def enforce_subscription_capacity(session, context, instances):
    if session.info.get("tenant_context") is None:
        return
    deltas = defaultdict(int)
    for row in set(session.new) | set(session.dirty) | set(session.deleted):
        kind = next((model for model in RESOURCES if isinstance(row, model)), None)
        if kind is None:
            continue
        state = inspect(row)
        org = identifier(row.organization_id)
        current_counted = row.deleted_at is None and not (kind is User and row.is_super_admin)
        if row in session.new:
            if org and current_counted:
                deltas[(org, kind)] += 1
            continue
        original_org = identifier(old_value(state, "organization_id", row.organization_id))
        was_counted = old_value(state, "deleted_at", row.deleted_at) is None and not (kind is User and old_value(state, "is_super_admin", row.is_super_admin))
        if original_org and was_counted:
            deltas[(original_org, kind)] -= 1
        if org and current_counted and row not in session.deleted:
            deltas[(org, kind)] += 1
    organizations = sorted({org for (org, kind), delta in deltas.items() if delta > 0}, key=str)
    for org in organizations:
        table = Organization.__table__
        # A write lock works in both SQLite and PostgreSQL; keep it until the
        # enclosing transaction commits so concurrent last-seat requests queue.
        session.execute(table.update().where(table.c.id == org).values(updated_at=table.c.updated_at))
        subscription = next((row for row in session.new if isinstance(row, OrganizationSubscription) and identifier(row.organization_id) == org), None)
        if subscription is None:
            table = OrganizationSubscription.__table__
            data = session.execute(select(table).where(table.c.organization_id == org)).mappings().first()
            if data:
                from types import SimpleNamespace
                subscription = SimpleNamespace(**data)
        if subscription is None:
            continue  # Preserved existing/unmanaged institution, reported as legacy.
        access = evaluate(subscription)
        if access["restricted"]:
            if not (session.info["tenant_context"].is_super_admin or session.info["tenant_context"].platform_admin):
                raise AppException(access["warning"], status_code=402, errors=[{"code": "SUBSCRIPTION_REQUIRED", "access": access}])
            if access["status"] == "UNCONFIGURED":
                continue  # Platform preparation does not grant customer access.
            if access["status"] == "REVIEW_REQUIRED":
                raise AppException(access["warning"], status_code=409)
        limits = subscription.package_snapshot
        for kind, key in RESOURCES.items():
            delta = deltas.get((org, kind), 0)
            if delta <= 0:
                continue
            table = kind.__table__
            query = select(func.count()).select_from(table).where(table.c.organization_id == org, table.c.deleted_at.is_(None))
            if kind is User:
                query = query.where(table.c.is_super_admin.is_(False))
            used = session.execute(query).scalar_one()
            limit = int(limits[key])
            if used + delta > limit:
                raise AppException("Satın alınan paketin kayıt sınırına ulaşıldı", status_code=409,
                    errors=[{"code": "PLAN_LIMIT_REACHED", "resource": key, "used": used, "limit": limit, "requested": delta,
                        "billing_path": "/subscription"}])
