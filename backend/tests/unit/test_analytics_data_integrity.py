from decimal import Decimal
import pytest
from app.application.services.ai_service import AIService


@pytest.mark.asyncio
async def test_missing_grades_do_not_create_sample_scores_or_behavior():
    result = await AIService().predict_student_performance("student", [], 0)
    assert result["predicted_grade"] is None
    assert result["current_average"] is None
    assert result["behavioral_analysis"] is None
    assert result["subject_performance"] == {}


@pytest.mark.asyncio
async def test_grade_history_does_not_invent_subject_scores_or_peer_ranking():
    result = await AIService().predict_student_performance("student", [80, 90], 95)
    assert result["current_average"] == 85
    assert result["peer_percentile"] is None
    assert result["subject_performance"] == {}


@pytest.mark.asyncio
async def test_collection_forecast_is_reproducible_from_real_history():
    service = AIService()
    history = [{"amount": "100.00", "payment_date": "2026-10-01"}]
    first = await service.forecast_payment_collection(history, Decimal("500"), 3)
    second = await service.forecast_payment_collection(history, Decimal("500"), 3)
    assert first == second
