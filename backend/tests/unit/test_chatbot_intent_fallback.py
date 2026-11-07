import asyncio
from datetime import date
from uuid import uuid4

import pytest

from app.application.services.chatbot.intent_schemas import ChatbotContext
from app.application.services.chatbot.intent_service import IntentDetectionService
from app.application.services.chatbot.llm_provider import LLMProvider


class FailingProvider(LLMProvider):
    async def chat_completion(self, *args, **kwargs):
        raise RuntimeError("LLM unavailable")

    async def structured_completion(self, *args, **kwargs):
        raise RuntimeError("LLM unavailable")


class HangingProvider(LLMProvider):
    async def chat_completion(self, *args, **kwargs):
        await asyncio.sleep(1)

    async def structured_completion(self, *args, **kwargs):
        await asyncio.sleep(1)


class UncertainProvider(FailingProvider):
    async def structured_completion(self, *args, **kwargs):
        return {"intent": "GENERAL", "confidence": 0.5}


def context() -> ChatbotContext:
    return ChatbotContext(
        user_id=uuid4(),
        role="parent",
        current_date=date.today(),
    )


@pytest.mark.asyncio
async def test_uses_keyword_fallback_when_llm_fails():
    service = IntentDetectionService(FailingProvider(), timeout_seconds=0.1)

    result = await service.detect_intent_with_fallback("Bu ay devamsızlık var mı?", context())

    assert result.intent == "ATTENDANCE"
    assert 0 < result.confidence <= 1


@pytest.mark.asyncio
async def test_uses_keyword_fallback_when_llm_times_out():
    service = IntentDetectionService(HangingProvider(), timeout_seconds=0.01)

    result = await service.detect_intent_with_fallback("Notları göster", context())

    assert result.intent == "GRADES"
    assert 0 < result.confidence <= 1


@pytest.mark.asyncio
async def test_detail_follow_up_reuses_the_previous_intent_without_llm():
    service = IntentDetectionService(HangingProvider(), timeout_seconds=0.01)
    previous_context = context().model_copy(
        update={
            "conversation_history": [
                {
                    "role": "assistant",
                    "content": "Son notlarınız hazır.",
                    "intent": "GRADES",
                }
            ]
        }
    )

    result = await service.detect_intent_with_fallback("Detayları aç", previous_context)

    assert result.intent == "GRADES"
    assert result.operation == "details"


@pytest.mark.asyncio
async def test_new_topic_does_not_inherit_previous_intent():
    service = IntentDetectionService(FailingProvider(), timeout_seconds=0.1)
    previous_context = context().model_copy(update={"conversation_history": [
        {"role": "assistant", "content": "Notlar", "intent": "GRADES"}
    ]})
    result = await service.detect_intent_with_fallback("Borçları göster", previous_context)
    assert result.intent == "DEBT"


@pytest.mark.asyncio
async def test_uncertain_llm_does_not_override_clear_grade_request():
    service = IntentDetectionService(UncertainProvider(), timeout_seconds=0.1)
    result = await service.detect_intent_with_fallback("notlarımı göster", context())
    assert result.intent == "GRADES"
