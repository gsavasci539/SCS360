"""Attendance summaries use each visible pupil's own dated observations."""
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from test_material_files import headers, materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from test_saas_platform import platform_client  # noqa: F401

from app.core.dates import school_today
from app.infrastructure.models.models import (
    AttendanceRecord,
    Branch,
    ClassRoom,
    Permission,
    Role,
    Student,
)
from app.main import router_registry
from app.routers import ai_analytics

PATHS = ("/api/ai/ai-attendance-predictions", "/api/ai/attendance-analysis")


def auth(data):
    return {**headers(data["root"]), "X-SCS360-Organization-Id": str(data["org"].id)}


def observation(data, child, day, status, **values):
    return AttendanceRecord(organization_id=data["org"].id, branch_id=data["branch"].id,
        class_id=data["classroom"].id, student_id=child.id, recorded_by=data["teacher"].id,
        attendance_date=day, status=status, **values)


def test_attendance_prediction_symbol_is_the_registered_canonical_handler():
    source = [r for r in ai_analytics.router.routes if r.path == PATHS[0]]
    active = [r for r in router_registry.router.routes if r.path == PATHS[0]]
    assert len(source) == len(active) == 1 and active[0].endpoint is ai_analytics.get_ai_attendance_predictions


async def test_empty_attendance_has_no_model_prediction_or_positive_judgement(platform_client):  # noqa: F811
    client, _, data = platform_client
    for path in PATHS:
        reply = await client.get(path, headers=auth(data))
        assert reply.status_code == 200, reply.text
        result = reply.json()["data"]
        assert result["ai_model"] is None and result["prediction_available"] is False
        assert result["current_rate"] is None and result["predicted_rate"] is None
        assert result["total_records"] == 0 and result["students_without_records"] == 2
        assert result["trend"] == "veri yetersiz" and result["patterns"] == []
        assert "iyi" not in " ".join(result["recommendations"]).lower()
        for days in (0, -1, 366, 10**20):
            assert (await client.get(path, headers=auth(data), params={"days": days})).status_code == 422


async def test_each_risk_pupil_keeps_their_own_weekday_patterns_without_fake_prediction(platform_client):  # noqa: F811
    client, sessions, data = platform_client
    monday = school_today() - timedelta(days=school_today().weekday() + 7)
    async with sessions() as db:
        for child, statuses in zip(data["children"], (("ABSENT", "PRESENT"), ("PRESENT", "ABSENT")), strict=True):
            db.add_all([observation(data, child, monday + timedelta(days=i), status) for i, status in enumerate(statuses)])
        await db.commit()
    reply = await client.get(PATHS[0], headers=auth(data))
    assert reply.status_code == 200, reply.text
    result = reply.json()["data"]
    assert result["current_rate"] == 50 and result["total_analyzed"] == 2
    alerts = {r["student_id"]: r for r in result["risk_alerts"]}
    assert all(r["predicted_rate"] is None and r["trend"] == "veri yetersiz" for r in alerts.values())
    patterns = {r["student_id"]: r["patterns"] for r in result["patterns"]}
    assert [(r["day"], r["rate"]) for r in patterns[str(data["children"][0].id)]] == [("Pazartesi", 100)]
    assert [(r["day"], r["rate"]) for r in patterns[str(data["children"][1].id)]] == [("Salı", 100)]
    assert result["total_risk_students"] == 2


async def test_attendance_inclusive_dates_states_archives_and_future_are_measured(platform_client):  # noqa: F811
    client, sessions, data = platform_client
    today = school_today()
    now = datetime.now(UTC)
    async with sessions() as db:
        child = data["children"][0]
        db.add_all([observation(data, child, today - timedelta(days=ago), status)
            for ago, status in ((29, "PRESENT"), (3, "LATE"), (2, "HALF_DAY"), (1, "EXCUSED"), (0, "ABSENT"),
                (30, "ABSENT"), (-1, "ABSENT"))])
        db.add(observation(data, child, today - timedelta(days=4), "ABSENT", deleted_at=now))
        archived = Student(first_name="Archived", last_name="Synthetic", organization_id=data["org"].id,
            branch_id=data["branch"].id, class_id=data["classroom"].id, deleted_at=now)
        db.add(archived)
        await db.flush()
        db.add(observation(data, archived, today, "ABSENT"))
        await db.commit()
    for path in PATHS:
        reply = await client.get(path, headers=auth(data), params={"days": 30})
        assert reply.status_code == 200, reply.text
        result = reply.json()["data"]
        assert result["total_records"] == 5 and result["attendance_denominator"] == 4
        assert result["current_rate"] == 62.5 and result["students_without_records"] == 1
        assert result["period_start"] == (today - timedelta(days=29)).isoformat()
        assert result["status_counts"] == {"PRESENT": 1, "LATE": 1, "HALF_DAY": 1, "EXCUSED": 1, "ABSENT": 1}


async def test_recorded_trend_is_chronological_and_not_a_schoolwide_other_student_trend(platform_client):  # noqa: F811
    client, sessions, data = platform_client
    today = school_today()
    async with sessions() as db:
        for ago, status in ((0, "PRESENT"), (5, "ABSENT"), (2, "PRESENT"), (4, "ABSENT"), (1, "PRESENT"), (3, "ABSENT")):
            db.add(observation(data, data["children"][0], today - timedelta(days=ago), status))
            db.add(observation(data, data["children"][1], today - timedelta(days=ago), "ABSENT" if status == "PRESENT" else "PRESENT"))
        await db.commit()
    result = (await client.get(PATHS[0], headers=auth(data))).json()["data"]
    alerts = {r["student_id"]: r for r in result["risk_alerts"]}
    assert alerts[str(data["children"][0].id)]["trend"] == "artıyor"
    assert alerts[str(data["children"][1].id)]["trend"] == "azalıyor"
    assert result["trend"] == "stabil" and result["predicted_rate"] is None


async def test_analytics_respects_teacher_class_and_root_institution_scope(platform_client):  # noqa: F811
    client, sessions, data = platform_client
    async with sessions() as db:
        role = (await db.execute(select(Role).options(selectinload(Role.permissions)).where(Role.slug == "teacher"))).scalar_one()
        role.permissions.append(Permission(code="attendance.read", name="Attendance", module="attendance"))
        branch = Branch(name="Other own branch", organization_id=data["org"].id)
        db.add(branch)
        await db.flush()
        classroom = ClassRoom(name="Peer class", organization_id=data["org"].id, branch_id=branch.id)
        db.add(classroom)
        await db.flush()
        peer = Student(first_name="PrivatePeer", last_name="Synthetic", organization_id=data["org"].id,
            branch_id=branch.id, class_id=classroom.id)
        foreign_class = ClassRoom(name="Foreign class", organization_id=data["stranger"].organization_id,
            branch_id=data["other_branch"].id)
        db.add_all([peer, foreign_class])
        await db.flush()
        db.add(observation(data, data["children"][0], school_today(), "PRESENT"))
        db.add(AttendanceRecord(organization_id=data["org"].id, branch_id=branch.id, class_id=classroom.id,
            student_id=peer.id, recorded_by=data["teacher"].id, attendance_date=school_today(), status="ABSENT"))
        db.add(AttendanceRecord(organization_id=data["stranger"].organization_id, branch_id=data["other_branch"].id,
            class_id=foreign_class.id, student_id=data["stranger"].id, recorded_by=data["teacher"].id,
            attendance_date=school_today(), status="ABSENT"))
        await db.commit()
    for path in PATHS:
        assert (await client.get(path, headers=headers(data["root"]))).status_code == 403
        assert (await client.get(path, headers=headers(data["user"]))).status_code == 403
        reply = await client.get(path, headers=headers(data["teacher"]))
        assert reply.status_code == 200, reply.text
        assert reply.json()["data"]["current_rate"] == 100 and "PrivatePeer" not in reply.text
        own = (await client.get(path, headers=auth(data))).json()["data"]
        assert own["total_records"] == 2 and own["current_rate"] == 50
        foreign = {**headers(data["root"]), "X-SCS360-Organization-Id": str(data["other_branch"].organization_id)}
        other = (await client.get(path, headers=foreign)).json()["data"]
        assert other["total_records"] == 1 and other["current_rate"] == 0


async def test_unknown_legacy_status_requires_review_and_is_not_a_fake_absence(platform_client):  # noqa: F811
    client, sessions, data = platform_client
    async with sessions() as db:
        if db.get_bind().dialect.name != "sqlite":
            pytest.skip("Only SQLite permits an unknown legacy enum label")
        record = observation(data, data["children"][0], school_today(), "PRESENT")
        db.add(record)
        await db.commit()
        await db.execute(text("UPDATE attendance_records SET status='LEGACY_UNKNOWN' WHERE id=:id"), {"id": str(record.id)})
        await db.commit()
    for path in PATHS:
        result = (await client.get(path, headers=auth(data))).json()["data"]
        assert result["current_rate"] is None and result["requires_review"] is True
        assert result["invalid_attendance_count"] == 1 and result["risk_alerts"] == []


@pytest.mark.parametrize("path", PATHS)
async def test_attendance_storage_errors_return_controlled_unavailable(platform_client, monkeypatch, path):  # noqa: F811
    client, _, data = platform_client
    execute = AsyncSession.execute

    async def unavailable(db, statement, *args, **kwargs):
        if "attendance_records" in str(statement):
            raise SQLAlchemyError("SENSITIVE_DATABASE_DETAILS")
        return await execute(db, statement, *args, **kwargs)

    monkeypatch.setattr(AsyncSession, "execute", unavailable)
    reply = await client.get(path, headers=auth(data))
    assert reply.status_code == 503 and "SENSITIVE_DATABASE_DETAILS" not in reply.text
