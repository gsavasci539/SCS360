from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.application.services.chatbot.conversation_history import ConversationHistoryService


@pytest.mark.parametrize("name", ["get_conversation_history", "get_session_summary", "get_user_conversation_stats"])
async def test_store_errors_are_propagated_instead_of_fabricating_empty_history(name):
    db = SimpleNamespace(execute=AsyncMock(side_effect=RuntimeError("store unavailable")))
    params = {"db": db, "user_id": uuid4(), "organization_id": uuid4()}
    if name != "get_user_conversation_stats":
        params["session_id"] = "controlled-session"
    with pytest.raises(RuntimeError, match="store unavailable"):
        await getattr(ConversationHistoryService, name)(**params)
