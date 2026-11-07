from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.application.services.subscription_access import evaluate


def test_expiry_and_ten_day_boundary_are_exact_and_do_not_depend_on_server_timezone():
    end = datetime(2026, 11, 3, 12, tzinfo=UTC)
    subscription = SimpleNamespace(admin_status="ACTIVE", period_end=end, package_snapshot={"branch_limit": 1, "student_limit": 10, "user_limit": 5})
    assert evaluate(subscription, now=end - timedelta(microseconds=1))["status"] == "ACTIVE"
    assert evaluate(subscription, now=end)["status"] == "GRACE"
    assert evaluate(subscription, now=end + timedelta(days=10) - timedelta(microseconds=1))["restricted"] is False
    locked = evaluate(subscription, now=end + timedelta(days=10))
    assert locked["restricted"] is True and locked["status"] == "PAST_DUE"
    assert locked["billing_path"] == "/subscription"
    subscription.period_end = end.replace(tzinfo=None)
    assert evaluate(subscription, now=end)["status"] == "GRACE"


def test_manual_suspension_wins_and_missing_legacy_plan_is_not_invented():
    subscription = SimpleNamespace(admin_status="SUSPENDED", period_end=datetime.now(UTC) + timedelta(days=30), package_snapshot={"user_limit": 5})
    assert evaluate(subscription)["status"] == "SUSPENDED"
    assert evaluate(None)["status"] == "LEGACY" and evaluate(None)["restricted"] is False
    assert evaluate(None, active=False)["restricted"] is True
    subscription.admin_status = "ACTIVE"; subscription.package_snapshot = None
    assert evaluate(subscription)["status"] == "UNCONFIGURED" and evaluate(subscription)["restricted"] is True


def test_future_membership_and_corrupt_limit_snapshot_do_not_open_business_access():
    now = datetime.now(UTC)
    subscription = SimpleNamespace(admin_status="ACTIVE", period_start=now + timedelta(days=1), period_end=now + timedelta(days=30),
        package_snapshot={"branch_limit": 1, "student_limit": 10, "user_limit": 5})
    assert evaluate(subscription, now=now)["status"] == "NOT_STARTED"
    subscription.package_snapshot["user_limit"] = -1
    assert evaluate(subscription, now=now)["status"] == "REVIEW_REQUIRED"
