"""School analytics must report measured records and preserve access boundaries."""
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from test_academic_summary_data import grade
from test_material_files import headers, materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from test_saas_platform import platform_client  # noqa: F401

from app.core.dates import school_today
from app.infrastructure.models.models import (
    AttendanceRecord,
    AttendanceStatus,
    Debt,
    DebtStatus,
    DebtType,
    Permission,
    Role,
)
from app.main import router_registry
from app.routers import ai_analytics

PATHS = ("/api/ai/organization-health", "/api/ai/student-performance-trends")


def auth(data):
    return {**headers(data["root"]), "X-SCS360-Organization-Id": str(data["org"].id)}


@pytest.mark.parametrize("path,name", [(PATHS[0], "get_organization_health"), (PATHS[1], "get_student_performance_trends")])
def test_school_metrics_have_one_canonical_handler(path, name):
    raw = [r for r in ai_analytics.router.routes if r.path == path and "GET" in r.methods]
    active = [r for r in router_registry.router.routes if r.path == path and "GET" in r.methods]
    assert len(raw) == len(active) == 1
    assert active[0].endpoint is getattr(ai_analytics, name)


async def test_school_metrics_do_not_invent_health_or_stable_trend_for_missing_data(platform_client):  # noqa: F811
    client, _, data = platform_client
    result = (await client.get(PATHS[0], headers=auth(data))).json()["data"]
    assert result["overall_health"] is None and result["health_status"] == "not_calculated"
    assert all(value is None for value in result["scores"].values())
    assert result["metrics"]["total_students"] == 2
    assert result["metrics"]["notification_opt_in_rate"] == 100
    assert result["analysis_kind"] == "RECORDED_SCHOOL_METRICS" and result["ai_model"] is None
    result = (await client.get(PATHS[1], headers=auth(data))).json()["data"]
    assert result["trends"] == [] and result["trend_direction"] == "insufficient_data"
    assert result["trend_percentage"] is None
    for path in PATHS:
        for days in (0, -1, 366):
            assert (await client.get(path, headers=auth(data), params={"days": days})).status_code == 422


async def test_school_health_uses_normalized_grades_valid_ledger_and_scoped_attendance(platform_client):  # noqa: F811
    client, sessions, data = platform_client
    today = school_today()
    now = datetime.now(UTC)
    async with sessions() as db:
        db.add_all([grade(data, 0, ago=2), grade(data, 40, maximum=80, ago=1), grade(data, 99, ago=40), grade(data, 100, ago=-1)])
        def attendance(day, status, **values):
            return AttendanceRecord(organization_id=data["org"].id, branch_id=data["branch"].id,
                class_id=data["classroom"].id, student_id=data["children"][0].id,
                attendance_date=day, status=status, recorded_by=data["teacher"].id, **values)
        db.add_all([attendance(today - timedelta(days=i), status) for i, status in enumerate(
            (AttendanceStatus.PRESENT, AttendanceStatus.LATE, AttendanceStatus.ABSENT, AttendanceStatus.EXCUSED))])
        db.add_all([attendance(today - timedelta(days=40), AttendanceStatus.ABSENT),
            attendance(today + timedelta(days=1), AttendanceStatus.ABSENT),
            attendance(today - timedelta(days=4), AttendanceStatus.ABSENT, deleted_at=now),
            attendance(today - timedelta(days=5), AttendanceStatus.HALF_DAY)])
        db.add_all([Debt(organization_id=data["org"].id, branch_id=data["branch"].id,
            student_id=data["children"][0].id, debt_type=DebtType.EDUCATION, amount=amount,
            paid_amount=paid, due_date=today, **values)
            for amount, paid, values in ((100, 25, {}), (900, 900, {"status": DebtStatus.CANCELLED}),
                (700, 700, {"deleted_at": now}))])
        foreign = grade(data, 100, ago=3)
        foreign.organization_id = data["stranger"].organization_id
        foreign.branch_id = data["other_branch"].id
        foreign.student_id = data["stranger"].id
        db.add(foreign)
        # Notification consent is not a measurement of actual engagement.
        from app.infrastructure.models.models import Parent
        parent = (await db.execute(select(Parent).where(Parent.user_id == data["user"].id))).scalar_one()
        parent.receive_notifications = True
        await db.commit()
    reply = await client.get(PATHS[0], headers=auth(data))
    assert reply.status_code == 200, reply.text
    result = reply.json()["data"]
    assert result["scores"] == {"academic": 25.0, "attendance": 62.5, "financial": 25.0, "engagement": None}
    assert result["overall_health"] is None and result["requires_review"] is False
    assert result["metrics"]["total_grades"] == 2 and result["metrics"]["total_debts"] == 1
    assert result["metrics"]["total_attendance_records"] == 5
    assert result["metrics"]["attendance_denominator"] == 4
    assert result["metrics"]["attendance_half_day_count"] == 1
    assert result["metrics"]["notification_opt_in_rate"] == 100
    assert result["period_start"] == (today - timedelta(days=29)).isoformat()


async def test_performance_trends_include_zero_normalize_maximum_and_use_exam_date(platform_client):  # noqa: F811
    client, sessions, data = platform_client
    today = school_today()
    this_monday = today - timedelta(days=today.weekday())
    previous_monday = this_monday - timedelta(days=7)
    async with sessions() as db:
        db.add_all([grade(data, 0, ago=(today - previous_monday).days),
            grade(data, 40, maximum=80, ago=(today - this_monday).days),
            grade(data, 99, ago=150), grade(data, 100, ago=-1)])
        # A future created_at must not move a real exam into the wrong period.
        from app.infrastructure.models.models import GradeType
        recent = grade(data, 100, maximum=100, ago=(today - this_monday).days)
        recent.grade_type = GradeType.QUIZ
        recent.created_at = datetime.now(UTC) + timedelta(days=10)
        db.add(recent)
        await db.commit()
    reply = await client.get(PATHS[1], headers=auth(data))
    assert reply.status_code == 200, reply.text
    result = reply.json()["data"]
    assert result["total_grades_analyzed"] == 3
    assert [r["average_grade"] for r in result["trends"]] == [0, 75]
    assert [r["week_start"] for r in result["trends"]] == [previous_monday.isoformat(), this_monday.isoformat()]
    assert result["trend_direction"] == "improving" and result["trend_percentage"] is None
    assert result["change_percentage_points"] == 75


@pytest.mark.parametrize("path", PATHS)
async def test_school_metrics_require_domain_permissions_and_explicit_root_selection(platform_client, path):  # noqa: F811
    client, sessions, data = platform_client
    for actor in (data["root"], data["user"], data["teacher"]):
        assert (await client.get(path, headers=headers(actor))).status_code == 403
    async with sessions() as db:
        role = (await db.execute(select(Role).options(selectinload(Role.permissions)).where(Role.slug == "teacher"))).scalar_one()
        role.permissions.append(Permission(code="academic.read", name="Academic", module="academic"))
        await db.commit()
    expected = 200 if path == PATHS[1] else 403
    assert (await client.get(path, headers=headers(data["teacher"]))).status_code == expected
    other = {**headers(data["root"]), "X-SCS360-Organization-Id": str(data["other_branch"].organization_id)}
    result = (await client.get(path, headers=other)).json()["data"]
    if path == PATHS[0]:
        assert result["metrics"]["total_students"] == 1 and all(value is None for value in result["scores"].values())
    else:
        assert result["trends"] == []


async def test_school_metrics_include_current_exam_results_and_keep_bad_balances_unknown(platform_client):  # noqa: F811
    from app.domain.entities.exams import Exam, ExamResult

    client, sessions, data = platform_client
    async with sessions() as db:
        for status in ("COMPLETED", "CANCELLED"):
            exam = Exam(class_id=data["classroom"].id, title="Synthetic assessment " + status,
                exam_type="QUIZ", exam_date=school_today(), max_score=80, status=status)
            db.add(exam)
            await db.flush()
            db.add(ExamResult(exam_id=exam.id, student_id=data["children"][0].id, score=40))
        db.add(Debt(organization_id=data["org"].id, branch_id=data["branch"].id,
            student_id=data["children"][0].id, debt_type=DebtType.EDUCATION,
            amount=100, paid_amount=101, due_date=school_today()))
        await db.commit()
    reply = await client.get(PATHS[0], headers=auth(data))
    assert reply.status_code == 200, reply.text
    result = reply.json()["data"]
    assert result["scores"]["academic"] == 50 and result["scores"]["financial"] is None
    assert result["metrics"]["total_grades"] == 1 and result["requires_review"] is True
    reply = await client.get(PATHS[1], headers=auth(data))
    assert reply.status_code == 200, reply.text
    result = reply.json()["data"]
    assert result["trends"][0]["average_grade"] == 50 and result["total_grades_analyzed"] == 1
    assert result["ignored_grade_count"] == 1 and result["trend_direction"] == "insufficient_data"


@pytest.mark.parametrize("path", PATHS)
async def test_school_metrics_database_failure_is_not_success_with_fabricated_zero(platform_client, monkeypatch, path):  # noqa: F811
    client, _, data = platform_client
    execute = AsyncSession.execute

    async def unavailable(db, statement, *args, **kwargs):
        if "students" in str(statement) and "users" not in str(statement):
            raise SQLAlchemyError("SENSITIVE_DATABASE_DETAILS")
        return await execute(db, statement, *args, **kwargs)

    monkeypatch.setattr(AsyncSession, "execute", unavailable)
    reply = await client.get(path, headers=auth(data))
    assert reply.status_code == 503 and "SENSITIVE_DATABASE_DETAILS" not in reply.text
