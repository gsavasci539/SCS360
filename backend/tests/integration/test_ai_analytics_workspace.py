"""Real audit metrics, explicit institution access, and UTC calendar ranges."""
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from test_material_files import headers, materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from test_saas_platform import platform_client  # noqa: F401

from app.infrastructure.models.models import AiChatAuditLog, Role, User
from app.routers import chatbot

PREFIX = "/api/v1/chatbot/ai/analytics/"
NOW = datetime(2026, 11, 11, 10, 30, tzinfo=UTC)


def auth(data, org=None):
    return {**headers(data["root"]), "X-SCS360-Organization-Id": str(org or data["org"].id)}


def audit(data, **values):
    return AiChatAuditLog(user_id=data["root"].id, organization_id=data["org"].id,
        session_id=str(uuid4()), user_query="Synthetic question", ai_response="Synthetic answer", **values)


async def test_analytics_averages_use_only_rated_records_and_selected_institution(platform_client):  # noqa: F811
    client, sessions, data = platform_client
    async with sessions() as db:
        rows = [audit(data, detected_intent="ATTENDANCE", quality_rating=rating, latency_ms=latency,
            feedback_status=status, topic_category=topic, is_fine_tuning_ready=ready)
            for rating, latency, status, topic, ready in (
                (4, 100, "VERIFIED", "Attendance", True),
                (0, 300, "NEEDS_REVIEW", None, False),
                (2, 200, "CORRECTED", "Attendance", False))]
        foreign = audit(data, detected_intent="FOREIGN_ONLY", quality_rating=5, latency_ms=9000)
        foreign.organization_id = data["other_branch"].organization_id
        db.add_all([*rows, foreign])
        await db.commit()
    reply = await client.get(PREFIX + "overview", headers=auth(data))
    assert reply.status_code == 200, reply.text
    result = reply.json()["data"]
    assert result["overview"] == {"total_logs": 3, "avg_latency_ms": 200.0,
        "avg_quality_rating": 3.0, "quality_rated_count": 2, "finetuning_ready_count": 1}
    assert result["distributions"]["topic"] == {"Attendance": 2, "UNKNOWN": 1}
    assert result["distributions"]["intent"] == {"ATTENDANCE": 3}
    reply = await client.get(PREFIX + "intent-performance", headers=auth(data))
    assert reply.status_code == 200, reply.text
    assert reply.json()["data"]["intent_performance"] == [{"intent": "ATTENDANCE", "count": 3,
        "avg_latency_ms": 200.0, "avg_quality_rating": 3.0, "quality_rated_count": 2,
        "verified_count": 1, "verification_rate": 33.33}]
    for suffix in ("overview", "intent-performance"):
        reply = await client.get(PREFIX + suffix, headers=auth(data, foreign.organization_id))
        assert reply.status_code == 200 and "FOREIGN_ONLY" in reply.text and "ATTENDANCE" not in reply.text


async def test_analytics_empty_and_unrated_metrics_do_not_invent_quality(platform_client):  # noqa: F811
    client, sessions, data = platform_client
    reply = await client.get(PREFIX + "overview", headers=auth(data))
    assert reply.status_code == 200, reply.text
    result = reply.json()["data"]
    assert result["overview"] == {"total_logs": 0, "avg_latency_ms": None,
        "avg_quality_rating": None, "quality_rated_count": 0, "finetuning_ready_count": 0}
    assert all(value == {} for value in result["distributions"].values())
    assert (await client.get(PREFIX + "intent-performance", headers=auth(data))).json()["data"]["intent_performance"] == []
    assert (await client.get(PREFIX + "trends", headers=auth(data))).json()["data"]["daily_trends"] == []
    async with sessions() as db:
        db.add(audit(data, quality_rating=0, latency_ms=0))
        await db.commit()
    result = (await client.get(PREFIX + "overview", headers=auth(data))).json()["data"]
    assert result["overview"]["avg_quality_rating"] is None
    assert result["overview"]["avg_latency_ms"] == 0
    assert result["distributions"]["intent"] == {"UNKNOWN": 1}
    row = (await client.get(PREFIX + "intent-performance", headers=auth(data))).json()["data"]["intent_performance"][0]
    assert row["intent"] == "UNKNOWN" and row["avg_quality_rating"] is None and row["quality_rated_count"] == 0


async def test_trends_uses_bounded_utc_calendar_days_and_excludes_future(platform_client, monkeypatch):  # noqa: F811
    client, sessions, data = platform_client

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW if tz else NOW.replace(tzinfo=None)

    monkeypatch.setattr(chatbot, "datetime", Clock)
    start = NOW.replace(hour=0, minute=0, second=0) - timedelta(days=1)
    async with sessions() as db:
        for when in (start - timedelta(microseconds=1), start,
            start + timedelta(hours=23, minutes=59), start + timedelta(days=1), NOW, NOW + timedelta(microseconds=1)):
            db.add(audit(data, created_at=when))
        foreign = audit(data, created_at=NOW)
        foreign.organization_id = data["other_branch"].organization_id
        db.add(foreign)
        await db.commit()
    # PostgreSQL DATE(timestamptz) must not depend on the connection's timezone.
    execute = AsyncSession.execute

    async def non_utc_session(db, statement, *args, **kwargs):
        if db.get_bind().dialect.name == "postgresql" and "ai_chat_audit_logs" in str(statement):
            await execute(db, text("SET LOCAL TIME ZONE 'Europe/Istanbul'"))
        return await execute(db, statement, *args, **kwargs)

    monkeypatch.setattr(AsyncSession, "execute", non_utc_session)
    reply = await client.get(PREFIX + "trends", headers=auth(data), params={"days": 2})
    assert reply.status_code == 200, reply.text
    result = reply.json()["data"]
    assert result["period_days"] == 2 and result["timezone"] == "UTC"
    assert result["daily_trends"] == [{"date": "2026-11-10", "count": 2}, {"date": "2026-11-11", "count": 2}]
    assert result["sentiment_trends"] == {"2026-11-10": {"NEUTRAL": 2}, "2026-11-11": {"NEUTRAL": 2}}
    result = (await client.get(PREFIX + "trends", headers=auth(data), params={"days": 1})).json()["data"]
    assert result["daily_trends"] == [{"date": "2026-11-11", "count": 2}]
    for days in (0, -1, 367, 10**20):
        assert (await client.get(PREFIX + "trends", headers=auth(data), params={"days": days})).status_code == 422
    assert (await client.get(PREFIX + "trends", headers=auth(data), params={"days": 366})).status_code == 200


async def test_analytics_access_remains_platform_selected_only(platform_client):  # noqa: F811
    client, sessions, data = platform_client
    async with sessions() as db:
        owner = User(email="metrics-owner@test.invalid", password_hash="unused", first_name="Owner", last_name="Test",
            organization_id=data["org"].id, roles=[Role(name="Owner", slug="owner", organization_id=data["org"].id)])
        db.add(owner)
        await db.commit()
    for suffix in ("overview", "trends", "intent-performance"):
        for actor in (data["root"], owner, data["user"], data["teacher"]):
            assert (await client.get(PREFIX + suffix, headers=headers(actor))).status_code == 403
        assert (await client.get(PREFIX + suffix, headers=auth(data))).status_code == 200


@pytest.mark.parametrize("suffix", ["overview", "trends", "intent-performance"])
async def test_analytics_store_failure_is_controlled_not_empty_success(platform_client, monkeypatch, suffix):  # noqa: F811
    client, _, data = platform_client
    execute = AsyncSession.execute

    async def unavailable(db, statement, *args, **kwargs):
        if "ai_chat_audit_logs" in str(statement):
            raise RuntimeError("SENSITIVE_DATABASE_DETAILS")
        return await execute(db, statement, *args, **kwargs)

    monkeypatch.setattr(AsyncSession, "execute", unavailable)
    reply = await client.get(PREFIX + suffix, headers=auth(data))
    assert reply.status_code == 503 and "SENSITIVE_DATABASE_DETAILS" not in reply.text
