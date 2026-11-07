"""Recorded contact availability and explicitly linked send records."""
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import String, and_, case, cast, func, select

from app.core.dates import school_day_bounds, school_today
from app.core.exceptions import ForbiddenException
from app.infrastructure.models.models import NotificationJob, NotificationRecipient, Parent, User
from app.infrastructure.repositories.base import BaseRepository


def utc_now():
    return datetime.now(UTC)


def percentage(numerator, denominator):
    return float((Decimal(numerator) / Decimal(denominator) * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)) if denominator else None


def registrations(rows):
    contact = sum(any(isinstance(value, str) and bool(value.strip()) for value in (row.phone, row.sms_phone, row.whatsapp_phone, row.email)) for row in rows)
    consent = defaultdict(int)
    for row in rows:
        value = str(row.notification_consent or "").strip().lower()
        consent["allowed" if value in {"true", "1"} else "declined" if value in {"false", "0"} else "unknown"] += 1
    total = len(rows)
    return {"total_records": total, "records_with_contact": contact, "records_without_contact": total - contact,
        "account_linked_records": sum(bool(row.account_linked) for row in rows),
        "notification_allowed_records": consent["allowed"], "notification_declined_records": consent["declined"],
        "notification_unknown_records": consent["unknown"], "contact_availability_rate": percentage(contact, total),
        "notification_consent_rate": percentage(consent["allowed"], total) if not consent["unknown"] else None}


def communications(rows):
    values = {"record_count": 0, "sent_count": 0, "pending_count": 0, "failed_count": 0,
        "cancelled_count": 0, "unknown_count": 0}
    for row in rows:
        count, confirmed = int(row.record_count), int(row.confirmed_sent or 0)
        status = str(row.record_status or "").strip().upper()
        values["record_count"] += count
        if status == "SENT":
            values["sent_count"] += confirmed
            values["unknown_count"] += count - confirmed
        elif status in {"PENDING", "FAILED", "CANCELLED"}:
            values[status.lower() + "_count"] += count
        else:
            values["unknown_count"] += count
    completed = values["sent_count"] + values["failed_count"]
    return {**values, "completed_attempt_count": completed,
        "send_success_rate": percentage(values["sent_count"], completed)}


async def summary(db, tenant, days):
    if not tenant.organization_id:
        raise ForbiddenException("Önce kurum çalışma alanını seçin")
    now = utc_now()
    today = school_today(now)
    first = today - timedelta(days=days - 1)
    start, _ = school_day_bounds(first)
    _, end = school_day_bounds(today)
    repo = BaseRepository(db, tenant)
    valid_account = select(User.id).where(User.id == Parent.user_id,
        User.organization_id == tenant.organization_id, User.deleted_at.is_(None),
        User.is_super_admin.is_(False)).correlate(Parent).exists()
    parent_filter = (Parent.organization_id == tenant.organization_id, Parent.deleted_at.is_(None))
    parent_rows = (await db.execute(select(Parent.phone, Parent.sms_phone, Parent.whatsapp_phone, Parent.email,
        cast(Parent.receive_notifications, String).label("notification_consent"), valid_account.label("account_linked"))
        .where(*parent_filter))).all()
    parent_ids = select(Parent.id).where(*parent_filter)
    record_status = func.upper(func.trim(cast(NotificationRecipient.status, String)))
    sent = and_(record_status == "SENT", NotificationRecipient.sent_at.is_not(None), NotificationRecipient.sent_at <= now)
    record_query = select(record_status.label("record_status"), func.count().label("record_count"),
        func.sum(case((sent, 1), else_=0)).label("confirmed_sent")).join(NotificationJob,
            NotificationJob.id == NotificationRecipient.notification_job_id).where(
        NotificationJob.organization_id == tenant.organization_id,
        NotificationRecipient.parent_id.in_(parent_ids),
        NotificationRecipient.created_at >= start, NotificationRecipient.created_at < end,
        NotificationRecipient.created_at <= now).group_by(record_status)
    record_query = repo._branch_filter(record_query, NotificationJob)
    record_rows = (await db.execute(record_query)).all()
    registration, communication = registrations(parent_rows), communications(record_rows)
    return {"analysis_type": "recorded_parent_engagement", "ai_model": None, "sentiment_available": False,
        "as_of": today.isoformat(), "period_start": first.isoformat(),
        "period_end_exclusive": (today + timedelta(days=1)).isoformat(), "analysis_period_days": days,
        "registration_metrics": registration, "communication_metrics": communication,
        "requires_review": bool(registration["notification_unknown_records"] or communication["unknown_count"]),
        "sentiment_analysis": {"overall_sentiment": "unknown", "sentiment_score": None, "confidence": None, "key_indicators": []},
        "engagement_metrics": {"total_parents": registration["total_records"], "engaged_parents": None,
            "parents_with_contact": registration["records_with_contact"], "communication_frequency": communication["record_count"]},
        "communication_effectiveness": {"notification_success_rate": communication["send_success_rate"],
            "response_time_estimate": None, "channel_diversity": None, "timing_optimization": None},
        "recommendations": [], "key_indicators": []}
