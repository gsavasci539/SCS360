from datetime import timedelta

from test_saas_platform import platform_client  # noqa: F401
from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.core.dates import school_today
from app.infrastructure.models.models import Grade, GradeType, SubjectType


def auth(data):
    return {**headers(data["root"]), "X-SCS360-Organization-Id": str(data["org"].id)}


def grade(data, score, maximum=100, ago=0):
    return Grade(organization_id=data["org"].id, branch_id=data["branch"].id, class_id=data["classroom"].id,
        student_id=data["children"][0].id, subject=SubjectType.MATHEMATICS, grade_type=GradeType.EXAM,
        score=score, max_score=maximum, exam_date=school_today() - timedelta(days=ago))


async def test_zero_grade_and_maximum_are_normalized_without_inventing_predictions_or_confidence(platform_client):
    client, sessions, data = platform_client
    async with sessions() as db:
        db.add_all([grade(data, 0, ago=2), grade(data, 40, maximum=80, ago=1)])
        await db.commit()
    response = await client.get("/api/ai/ai-academic-predictions", headers=auth(data))
    assert response.status_code == 200, response.text
    result = response.json()["data"]
    assert result["total_analyzed"] == 1 and result["students_without_grades"] == 1, result
    assert result["analysis_kind"] == "RECORDED_GRADES" and result["ai_model"] is None
    assert result["prediction_available"] is False and result["confidence_threshold"] is None
    risk = result["risk_students"][0]
    assert risk["current_average"] == 25 and risk["grade_count"] == 2, risk
    assert risk["predicted_grade"] is None and risk["confidence"] is None


async def test_recent_trend_uses_chronological_nonoverlapping_groups_and_skips_invalid_scores(platform_client):
    client, sessions, data = platform_client
    async with sessions() as db:
        db.add_all([grade(data, score, ago=6-index) for index, score in reversed(list(enumerate([10, 20, 30, 80, 90, 100])))])
        db.add(grade(data, 10, maximum=0, ago=0)); await db.commit()
    response = await client.get("/api/ai/ai-academic-predictions", headers=auth(data))
    assert response.status_code == 200, response.text
    result = response.json()["data"]; risk = result["risk_students"][0]
    assert risk["current_average"] == 55 and risk["trend"] == "artıyor", result
    assert risk["grade_count"] == 6 and result["ignored_grade_count"] == 1


async def test_selected_period_and_empty_data_are_reported_without_all_good_fallback(platform_client):
    client, sessions, data = platform_client
    async with sessions() as db:
        db.add(grade(data, 40, ago=60)); await db.commit()
    response = await client.get("/api/ai/ai-academic-predictions", headers=auth(data), params={"days": 7})
    assert response.status_code == 200, response.text
    result = response.json()["data"]
    assert result["total_analyzed"] == 0 and result["students_without_grades"] == 2, result
    assert result["risk_students"] == [] and "genel olarak iyi" not in str(result)
    older = await client.get("/api/ai/ai-academic-predictions", headers=auth(data), params={"days": 90})
    assert older.status_code == 200 and older.json()["data"]["total_analyzed"] == 1, older.text
    assert (await client.get("/api/ai/ai-academic-predictions", headers=auth(data), params={"days": 0})).status_code == 422


async def test_query_failure_is_a_retryable_error_without_private_database_text(platform_client, monkeypatch):
    from sqlalchemy.exc import SQLAlchemyError
    from app.application.services import academic_summary
    async def unavailable(*args, **kwargs):
        raise SQLAlchemyError("private SQL and credentials must not reach the client")
    monkeypatch.setattr(academic_summary, "summary", unavailable)
    client, sessions, data = platform_client
    for path in ("/api/ai/ai-academic-predictions", "/api/ai/academic-performance"):
        response = await client.get(path, headers=auth(data))
        assert response.status_code == 503 and response.json()["success"] is False, response.text
        assert "private SQL" not in response.text and "credentials" not in response.text
