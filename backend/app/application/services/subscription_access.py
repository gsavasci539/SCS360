"""Commercial access is evaluated from current server data, never token claims."""
from datetime import UTC, datetime, timedelta
from math import ceil

from sqlalchemy import select

from app.domain.entities.saas import OrganizationSubscription
from app.infrastructure.models.models import Organization


def utc(value):
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def evaluate(subscription, *, active=True, now=None):
    now = utc(now or datetime.now(UTC))
    result = {"status": "LEGACY", "restricted": False, "warning": None, "period_end": None,
        "grace_end": None, "billing_path": "/subscription", "days_remaining": None}
    if not active or (subscription and subscription.admin_status != "ACTIVE"):
        return {**result, "status": "SUSPENDED", "restricted": True, "warning": "Kurum hesabı kapatılmış. Platform yöneticisiyle iletişime geçin."}
    if subscription is None:
        return result
    if subscription.package_snapshot and getattr(subscription, "period_start", None) is None and subscription.period_end is None:
        return {**result, "status": "PENDING_PAYMENT", "restricted": True, "warning": "Kurum hesabınız oluşturuldu. Çalışma alanını açmak için üyelik ödemenizi tamamlayın."}
    if not subscription.package_snapshot or subscription.period_end is None:
        return {**result, "status": "UNCONFIGURED", "restricted": True, "warning": "Kurum üyeliği henüz tanımlanmamış. Platform yöneticisiyle iletişime geçin."}
    snapshot = subscription.package_snapshot
    if not isinstance(snapshot, dict) or any(type(snapshot.get(key)) is not int or snapshot[key] < 1 for key in ("branch_limit", "student_limit", "user_limit")):
        return {**result, "status": "REVIEW_REQUIRED", "restricted": True, "warning": "Üyelik paketi incelenmeli. Platform yöneticisiyle iletişime geçin."}
    end = utc(subscription.period_end)
    grace_end = end + timedelta(days=10)
    result.update(period_end=end.isoformat(), grace_end=grace_end.isoformat())
    start = getattr(subscription, "period_start", None)
    if start is not None and utc(start) > now:
        return {**result, "status": "NOT_STARTED", "restricted": True, "warning": "Üyelik dönemi henüz başlamadı."}
    if now < end:
        return {**result, "status": "ACTIVE", "days_remaining": ceil((end - now).total_seconds() / 86400)}
    if now < grace_end:
        return {**result, "status": "GRACE", "days_remaining": ceil((grace_end - now).total_seconds() / 86400),
            "warning": "Üyelik süreniz doldu. On günlük ek süre bitmeden ödemenizi tamamlayın."}
    return {**result, "status": "PAST_DUE", "restricted": True, "days_remaining": 0,
        "warning": "Üyelik süresi ve on günlük ek süre doldu. Devam etmek için üyelik ödemenizi tamamlayın."}


async def for_user(db, user, now=None):
    if user.is_super_admin:
        return {**evaluate(None), "status": "PLATFORM"}
    if user.organization_id is None:
        return {**evaluate(None), "status": "UNASSIGNED", "restricted": True, "warning": "Hesabınız bir kuruma bağlı değil."}
    # Core reads are intentional: account access must not disappear behind
    # feature-specific ORM/branch filters.
    table = Organization.__table__
    organization = (await db.execute(select(table.c.is_active, table.c.deleted_at).where(table.c.id == user.organization_id))).first()
    subscription = (await db.execute(select(OrganizationSubscription).where(OrganizationSubscription.organization_id == user.organization_id))).scalar_one_or_none()
    return evaluate(subscription, active=bool(organization and organization.is_active and organization.deleted_at is None), now=now)
