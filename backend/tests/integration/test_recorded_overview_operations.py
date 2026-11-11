from datetime import timedelta

from test_academic_summary_data import grade
from test_material_files import headers, materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from test_saas_platform import platform_client  # noqa: F401

from app.core.dates import school_today
from app.infrastructure.models.models import AttendanceRecord, Debt, DebtStatus, DebtType


def auth(data):
    return {**headers(data["root"]), "X-SCS360-Organization-Id": str(data["org"].id)}


async def test_overview_does_not_invent_scores_sentiment_or_predictions_when_missing(platform_client):  # noqa: F811
    client, _, data = platform_client
    response = await client.get("/api/ai/insights-report", headers=auth(data))
    assert response.status_code == 200, response.text
    result = response.json()["data"]
    assert result["analysis_kind"] == "RECORDED_OVERVIEW" and result["ai_model"] is None
    assert result["insights"]["attendance"]["overall_rate"] is None
    assert result["insights"]["financial"]["collection_rate"] is None
    assert result["insights"]["financial"]["forecast_trend"] is None
    assert result["insights"]["parent_satisfaction"] == {"score": None, "sentiment": None}
    assert not any("normal" in message or "gönder" in message for message in result["priority_actions"])


async def test_overview_reuses_normalized_student_counts_real_attendance_and_valid_finance(platform_client):  # noqa: F811
    client, sessions, data = platform_client
    async with sessions() as db:
        db.add_all([grade(data, 0, ago=2), grade(data, 40, maximum=80, ago=1)])
        for ago, status in ((0, "PRESENT"), (1, "LATE"), (2, "ABSENT"), (-1, "ABSENT")):
            db.add(AttendanceRecord(organization_id=data["org"].id, branch_id=data["branch"].id,
                class_id=data["classroom"].id, student_id=data["children"][0].id,
                recorded_by=data["teacher"].id, attendance_date=school_today() - timedelta(days=ago), status=status))
        for amount, paid, status in ((100, 25, DebtStatus.PARTIALLY_PAID), (900, 900, DebtStatus.CANCELLED)):
            db.add(Debt(organization_id=data["org"].id, branch_id=data["branch"].id,
                student_id=data["children"][0].id, debt_type=DebtType.EDUCATION,
                amount=amount, paid_amount=paid, status=status, due_date=school_today()))
        await db.commit()
    response = await client.get("/api/ai/insights-report", headers=auth(data))
    assert response.status_code == 200, response.text
    result = response.json()["data"]["insights"]
    assert result["academic_performance"]["average_grade"] == 25 and result["academic_performance"]["at_risk_students"] == 1
    assert result["attendance"]["overall_rate"] == 66.7
    assert result["financial"]["collection_rate"] == 25


async def test_operational_counts_capacity_without_inventing_staff_efficiency(platform_client):  # noqa: F811
    client, _, data = platform_client
    response = await client.get("/api/ai/ai-operational-optimization", headers=auth(data))
    assert response.status_code == 200, response.text
    result = response.json()["data"]
    assert result["analysis_kind"] == "RECORDED_OPERATIONS" and result["ai_model"] is None
    assert result["optimization_scores"]["overall_score"] is None and result["optimization_scores"]["staff_efficiency"] is None
    assert result["counts"]["class_count"] == 2 and result["counts"]["active_students"] == 2
    assert result["counts"]["assigned_active_students"] == 2
    assert result["counts"]["known_capacity"] == 40
    assert result["optimization_scores"]["classroom_utilization"] == 5
    assert result["counts"]["staff_count"] == 1
    for actor in (data["root"], data["user"], data["teacher"]):
        assert (await client.get("/api/ai/ai-operational-optimization", headers=headers(actor))).status_code == 403
