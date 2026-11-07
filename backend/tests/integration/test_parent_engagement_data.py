from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from app.core.dates import school_day_bounds, school_today
from app.infrastructure.models.models import (Branch, NotificationChannel, NotificationJob,
    NotificationRecipient, NotificationStatus, Parent, Permission, Role, Student, StudentParent, User)
from test_finance_compatibility import finance_client, auth  # noqa: F401
from test_material_files import materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401


@pytest.fixture
async def parent_analytics_client(finance_client):
    client, sessions, data = finance_client
    async with sessions() as db:
        role = (await db.execute(select(Role).options(selectinload(Role.permissions))
            .where(Role.slug == "accountant"))).scalar_one()
        role.permissions.extend([Permission(code=code, name=code, module=code.split(".")[0])
            for code in ("parents.read", "notification.read")])
        await db.commit()
    return client, sessions, data


async def test_parent_overview_counts_records_and_preferences_without_inventing_mood(parent_analytics_client):
    client, sessions, data = parent_analytics_client
    now = datetime.now(UTC)
    async with sessions() as db:
        existing = (await db.execute(select(Parent).where(Parent.user_id == data["user"].id))).scalar_one()
        existing.email, existing.receive_notifications = "private-parent@example.invalid", True
        db.add_all([
            Parent(organization_id=data["org"].id, first_name="Blank", last_name="Contact",
                phone=" \t", email=" \n", receive_notifications=False),
            Parent(organization_id=data["org"].id, first_name="WhatsApp", last_name="Contact",
                whatsapp_phone=" 05555555555 ", receive_notifications=False),
            Parent(organization_id=data["org"].id, first_name="Deleted", last_name="Contact",
                phone="05554443322", deleted_at=now),
            Parent(organization_id=data["stranger"].organization_id, first_name="Foreign", last_name="Private",
                phone="09999999999")])
        await db.commit()
    reply = await client.get("/api/ai/ai-parent-sentiment", headers=auth(data["accountant"]))
    assert reply.status_code == 200, reply.text
    result = reply.json()["data"]
    assert result["analysis_type"] == "recorded_parent_engagement" and result["ai_model"] is None, result
    assert result["sentiment_available"] is False
    assert result["sentiment_analysis"] == {"overall_sentiment": "unknown", "sentiment_score": None, "confidence": None, "key_indicators": []}
    metrics = result["registration_metrics"]
    assert metrics["total_records"] == 3 and metrics["records_with_contact"] == 2 and metrics["records_without_contact"] == 1
    assert metrics["account_linked_records"] == 1
    assert metrics["notification_allowed_records"] == 1 and metrics["notification_declined_records"] == 2
    assert Decimal(str(metrics["contact_availability_rate"])) == Decimal("66.7")
    assert Decimal(str(metrics["notification_consent_rate"])) == Decimal("33.3")
    assert "private-parent" not in reply.text and "05555555555" not in reply.text and "Foreign" not in reply.text


async def test_parent_overview_reads_recipient_results_not_job_or_consent_counts(parent_analytics_client):
    client, sessions, data = parent_analytics_client
    now = datetime.now(UTC)
    async with sessions() as db:
        parent = (await db.execute(select(Parent).where(Parent.user_id == data["user"].id))).scalar_one()
        job = NotificationJob(organization_id=data["org"].id, branch_id=data["branch"].id,
            channel=NotificationChannel.EMAIL, status=NotificationStatus.SENT, subject="PRIVATE subject", body="PRIVATE body")
        other = NotificationJob(organization_id=data["stranger"].organization_id, branch_id=data["other_branch"].id,
            channel=NotificationChannel.EMAIL, status=NotificationStatus.SENT, body="foreign body")
        no_recipients = NotificationJob(organization_id=data["org"].id, branch_id=data["branch"].id,
            channel=NotificationChannel.SMS, status=NotificationStatus.SENT, body="Not delivery evidence")
        db.add_all([job, other, no_recipients]); await db.flush()
        def recipient(status, **values):
            return NotificationRecipient(notification_job_id=job.id, parent_id=parent.id,
                recipient_address="private@example.invalid", status=status, created_at=now, **values)
        db.add_all([recipient(NotificationStatus.SENT, sent_at=now), recipient(NotificationStatus.FAILED),
            recipient(NotificationStatus.PENDING), recipient(NotificationStatus.CANCELLED), recipient(NotificationStatus.SENT),
            recipient(NotificationStatus.SENT, sent_at=now+timedelta(days=1)),
            NotificationRecipient(notification_job_id=job.id, parent_id=parent.id, recipient_address="old@example.invalid",
                status=NotificationStatus.SENT, sent_at=now-timedelta(days=40), created_at=now-timedelta(days=40)),
            NotificationRecipient(notification_job_id=job.id, parent_id=parent.id, recipient_address="future@example.invalid",
                status=NotificationStatus.SENT, sent_at=now+timedelta(days=1), created_at=now+timedelta(days=1)),
            NotificationRecipient(notification_job_id=other.id, parent_id=parent.id, recipient_address="corrupt-cross-org@example.invalid",
                status=NotificationStatus.SENT, sent_at=now, created_at=now),
            NotificationRecipient(notification_job_id=job.id, user_id=data["accountant"].id, recipient_address="staff@example.invalid",
                status=NotificationStatus.SENT, sent_at=now, created_at=now)])
        await db.commit()
    reply = await client.get("/api/ai/ai-parent-sentiment", headers=auth(data["accountant"]), params={"days": 30})
    assert reply.status_code == 200, reply.text
    result = reply.json()["data"]; metrics = result["communication_metrics"]
    assert metrics["record_count"] == 6, metrics
    assert {key: metrics[key] for key in ("sent_count", "pending_count", "failed_count", "cancelled_count", "unknown_count")} == {
        "sent_count": 1, "pending_count": 1, "failed_count": 1, "cancelled_count": 1, "unknown_count": 2}
    assert metrics["completed_attempt_count"] == 2 and metrics["send_success_rate"] == 50
    assert result["requires_review"] is True
    assert "PRIVATE" not in reply.text and "example.invalid" not in reply.text


async def test_empty_parent_overview_reports_known_zero_counts_but_unknown_rates(parent_analytics_client):
    client, sessions, data = parent_analytics_client
    async with sessions() as db:
        parent = (await db.execute(select(Parent).where(Parent.user_id == data["user"].id))).scalar_one()
        parent.deleted_at = datetime.now(UTC); await db.commit()
    reply = await client.get("/api/ai/ai-parent-sentiment", headers=auth(data["accountant"]))
    assert reply.status_code == 200, reply.text
    result = reply.json()["data"]
    assert result["registration_metrics"]["total_records"] == 0
    assert result["registration_metrics"]["contact_availability_rate"] is None
    assert result["registration_metrics"]["notification_consent_rate"] is None
    assert result["communication_metrics"]["record_count"] == 0
    assert result["communication_metrics"]["send_success_rate"] is None
    for days in (0, -1, 366):
        assert (await client.get("/api/ai/ai-parent-sentiment", headers=auth(data["accountant"]), params={"days": days})).status_code == 422


async def test_parent_overview_respects_branch_scope_without_double_counting_multiple_children(parent_analytics_client):
    client, sessions, data = parent_analytics_client
    async with sessions() as db:
        branch = Branch(organization_id=data["org"].id, name="Other branch")
        db.add(branch); await db.flush()
        student = Student(organization_id=data["org"].id, branch_id=branch.id, first_name="Other", last_name="Student")
        parent = Parent(organization_id=data["org"].id, first_name="Other", last_name="Parent", email="other@example.invalid")
        db.add_all([student, parent]); await db.flush()
        db.add(StudentParent(student_id=student.id, parent_id=parent.id))
        staff = (await db.execute(select(User).options(selectinload(User.branches))
            .where(User.id == data["accountant"].id))).scalar_one()
        staff.branches = [data["branch"]]
        await db.commit()
    reply = await client.get("/api/ai/ai-parent-sentiment", headers=auth(data["accountant"]))
    assert reply.status_code == 200, reply.text
    assert reply.json()["data"]["registration_metrics"]["total_records"] == 1


async def test_parent_overview_requires_both_native_domains_without_granting_parent_role_access(finance_client):
    client, sessions, data = finance_client
    endpoint = "/api/ai/ai-parent-sentiment"
    for actor in (data["accountant"], data["teacher"], data["user"]):
        assert (await client.get(endpoint, headers=auth(actor))).status_code == 403
    async with sessions() as db:
        role = (await db.execute(select(Role).options(selectinload(Role.permissions)).where(Role.slug == "accountant"))).scalar_one()
        role.permissions.append(Permission(code="parents.read", name="Parents", module="parents"))
        await db.commit()
    assert (await client.get(endpoint, headers=auth(data["accountant"]))).status_code == 403
    async with sessions() as db:
        role = (await db.execute(select(Role).options(selectinload(Role.permissions)).where(Role.slug == "accountant"))).scalar_one()
        role.permissions = [permission for permission in role.permissions if permission.code != "parents.read"]
        role.permissions.append(Permission(code="notification.read", name="Notifications", module="notification"))
        await db.commit()
    assert (await client.get(endpoint, headers=auth(data["accountant"]))).status_code == 403


async def test_parent_overview_query_failure_is_retryable_and_sanitized(parent_analytics_client, monkeypatch):
    from app.application.services import parent_engagement
    client, _, data = parent_analytics_client
    async def unavailable(*args, **kwargs):
        raise SQLAlchemyError("PRIVATE SELECT and database credentials")
    monkeypatch.setattr(parent_engagement, "summary", unavailable)
    reply = await client.get("/api/ai/ai-parent-sentiment", headers=auth(data["accountant"]))
    assert reply.status_code == 503 and reply.json()["success"] is False, reply.text
    assert "PRIVATE" not in reply.text and "credentials" not in reply.text and "SELECT" not in reply.text


async def test_parent_communication_period_uses_school_day_bounds_and_keeps_a_real_zero_success_rate(parent_analytics_client, monkeypatch):
    from app.application.services import parent_engagement
    from app.core.config import get_settings
    client, sessions, data = parent_analytics_client
    instant = datetime(2026, 12, 31, 21, 30, tzinfo=UTC)
    monkeypatch.setattr(get_settings(), "BUSINESS_TIMEZONE", "Europe/Istanbul")
    monkeypatch.setattr(parent_engagement, "utc_now", lambda: instant)
    start, end = school_day_bounds(school_today(instant))
    async with sessions() as db:
        parent = (await db.execute(select(Parent).where(Parent.user_id == data["user"].id))).scalar_one()
        job = NotificationJob(organization_id=data["org"].id, branch_id=data["branch"].id,
            channel=NotificationChannel.EMAIL, body="private")
        db.add(job); await db.flush()
        db.add_all([NotificationRecipient(notification_job_id=job.id, parent_id=parent.id,
            recipient_address="private@example.invalid", status=NotificationStatus.FAILED, created_at=created)
            for created in (start-timedelta(microseconds=1), start, instant, end)])
        await db.commit()
    reply = await client.get("/api/ai/ai-parent-sentiment", headers=auth(data["accountant"]), params={"days": 1})
    assert reply.status_code == 200, reply.text
    result = reply.json()["data"]
    assert result["as_of"] == result["period_start"] == "2027-01-01"
    assert result["period_end_exclusive"] == "2027-01-02"
    assert result["communication_metrics"]["record_count"] == 2
    assert result["communication_metrics"]["send_success_rate"] == 0


@pytest.mark.parametrize("portal_db", ["sqlite"], indirect=True)
async def test_parent_overview_preserves_old_keys_and_unknown_recipient_statuses(parent_analytics_client):
    client, sessions, data = parent_analytics_client
    now = datetime.now(UTC)
    async with sessions() as db:
        db.add(Parent(id="legacy-parent-key", organization_id=data["org"].id, first_name="Old", last_name="Contact",
            phone="05001112233", receive_notifications=False))
        job = NotificationJob(organization_id=data["org"].id, branch_id=data["branch"].id,
            channel=NotificationChannel.EMAIL, body="private")
        db.add(job); await db.flush()
        db.add(NotificationRecipient(id="legacy-recipient-key", notification_job_id=job.id,
            parent_id="legacy-parent-key", recipient_address="legacy@example.invalid", created_at=now))
        await db.commit()
        await db.execute(text("UPDATE parents SET relation_type = :value WHERE id = :key"), {"value": "LEGACY_KIND", "key": "legacy-parent-key"})
        await db.execute(text("UPDATE parents SET receive_notifications = :value WHERE id = :key"), {"value": "LEGACY_CONSENT", "key": "legacy-parent-key"})
        await db.execute(text("UPDATE notification_recipients SET status = :value WHERE id = :key"), {"value": "LEGACY_STATUS", "key": "legacy-recipient-key"})
        await db.commit()
    reply = await client.get("/api/ai/ai-parent-sentiment", headers=auth(data["accountant"]))
    assert reply.status_code == 200, reply.text
    result = reply.json()["data"]
    assert result["registration_metrics"]["total_records"] == 2
    assert result["registration_metrics"]["notification_unknown_records"] == 1
    assert result["registration_metrics"]["notification_consent_rate"] is None
    assert result["communication_metrics"]["unknown_count"] == 1
    assert result["requires_review"] is True
    async with sessions() as db:
        assert (await db.execute(text("SELECT relation_type FROM parents WHERE id = :key"), {"key": "legacy-parent-key"})).scalar_one() == "LEGACY_KIND"
        assert (await db.execute(text("SELECT status FROM notification_recipients WHERE id = :key"), {"key": "legacy-recipient-key"})).scalar_one() == "LEGACY_STATUS"
