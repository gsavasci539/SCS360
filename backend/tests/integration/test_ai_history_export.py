"""Registered history/export APIs: actor + institution isolation, empty export, and CSV text."""
import csv
import json
from io import StringIO
from uuid import uuid4

import pytest
from test_material_files import headers, materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from test_saas_platform import platform_client  # noqa: F401

from app.infrastructure.models.models import AiChatAuditLog, User


@pytest.mark.parametrize("actor_key", ["teacher", "user"])
async def test_shared_session_key_never_combines_other_users_or_institutions(materials_client, actor_key):  # noqa: F811
    client, sessions, data = materials_client
    session_id = "shared-" + uuid4().hex
    async with sessions() as db:
        colleague = User(email="history-colleague@test.invalid", password_hash="unused", first_name="Other", last_name="Teacher",
            organization_id=data["org"].id)
        db.add(colleague)
        await db.flush()
        db.add_all([AiChatAuditLog(user_id=actor, organization_id=org, session_id=key, user_query=question,
            ai_response=answer, detected_intent=intent, topic_category=intent, latency_ms=latency)
            for actor, org, key, question, answer, intent, latency in (
                (data[actor_key].id, data["org"].id, session_id, "OWN QUESTION", "OWN ANSWER", "OWN", 10),
                (colleague.id, data["org"].id, session_id, "OTHER SECRET", "OTHER ANSWER", "OTHER", 900),
                (data[actor_key].id, data["other_branch"].organization_id, session_id, "FOREIGN SECRET", "FOREIGN ANSWER", "FOREIGN", 800),
                (colleague.id, data["org"].id, "other-only", "PRIVATE SESSION", "PRIVATE ANSWER", "PRIVATE", 700))])
        await db.commit()
    auth = headers(data[actor_key])
    base = "/api/v1/chatbot/ai/conversation/"
    history = await client.get(base + "history/" + session_id, headers=auth)
    assert history.status_code == 200, history.text
    assert [row["content"] for row in history.json()["data"]["history"]] == ["OWN QUESTION", "OWN ANSWER"]
    summary = await client.get(base + "summary/" + session_id, headers=auth)
    assert summary.status_code == 200, summary.text
    result = summary.json()["data"]["summary"]
    assert result["message_count"] == 1 and result["intents"] == ["OWN"] and result["avg_latency"] == 10
    stats = await client.get(base + "my-stats", headers=auth)
    assert stats.status_code == 200 and stats.json()["data"]["stats"]["total_messages"] == 1
    for kind in ("history", "summary"):
        assert (await client.get(base + kind + "/other-only", headers=auth)).status_code == 403
    for limit in (0, -1, 101):
        assert (await client.get(base + "history/" + session_id, headers=auth, params={"limit": limit})).status_code == 422
    assert (await client.get(base + "history/" + "x" * 101, headers=auth)).status_code == 422


async def test_empty_export_keeps_not_found_and_formats_are_checked_before_data(platform_client):  # noqa: F811
    client, _, data = platform_client
    auth = {**headers(data["root"]), "X-SCS360-Organization-Id": str(data["org"].id)}
    path = "/api/v1/chatbot/ai/export-dataset"
    assert (await client.get(path, headers=auth)).status_code == 404
    assert (await client.get(path, headers=auth, params={"format": "unsupported"})).status_code == 400
    assert (await client.get(path, headers=headers(data["root"]))).status_code == 403
    assert (await client.get(path, headers=headers(data["user"]))).status_code == 403


async def test_export_formats_stay_school_scoped_and_csv_does_not_execute_message_cells(platform_client):  # noqa: F811
    client, sessions, data = platform_client
    async with sessions() as db:
        db.add_all([AiChatAuditLog(user_id=data["root"].id, organization_id=org, session_id=str(uuid4()),
            user_query=prompt, ai_response="Original answer", corrected_response=completion,
            feedback_status="VERIFIED", is_fine_tuning_ready=True, meta_data={"sender_role": "SUPERADMIN"})
            for org, prompt, completion in ((data["org"].id, "=2+2", " +1+1"),
                (data["other_branch"].organization_id, "FOREIGN EXPORT SECRET", "FOREIGN COMPLETION"))])
        await db.commit()
    auth = {**headers(data["root"]), "X-SCS360-Organization-Id": str(data["org"].id)}
    path = "/api/v1/chatbot/ai/export-dataset"
    for format in ("jsonl", "alpaca", "llama", "csv", "CSV"):
        reply = await client.get(path, headers=auth, params={"format": format, "is_fine_tuning_ready": "true"})
        assert reply.status_code == 200, reply.text
        assert "FOREIGN EXPORT SECRET" not in reply.text and "FOREIGN COMPLETION" not in reply.text
        assert " +1+1" in reply.text and "Original answer" not in reply.text
        assert "attachment; filename=" in reply.headers["content-disposition"]
        if format == "jsonl":
            assert json.loads(reply.text)["messages"][1]["content"] == "=2+2"
        if format.lower() == "csv":
            rows = list(csv.DictReader(StringIO(reply.text)))
            assert len(rows) == 1 and rows[0]["prompt"] == "'=2+2" and rows[0]["completion"] == "' +1+1"


@pytest.mark.parametrize("kind,method", [("history/session", "get_conversation_history"),
    ("summary/session", "get_session_summary"), ("my-stats", "get_user_conversation_stats")])
async def test_history_read_failure_is_not_successful_empty_data_or_database_details(materials_client, monkeypatch, kind, method):  # noqa: F811
    from app.routers.chatbot import conversation_history_service
    client, sessions, data = materials_client
    async with sessions() as db:
        db.add(AiChatAuditLog(user_id=data["teacher"].id, organization_id=data["org"].id,
            session_id="session", user_query="Controlled question", ai_response="Controlled answer"))
        await db.commit()

    async def fail(*args, **kwargs):
        raise RuntimeError("SENSITIVE_DATABASE_DETAILS")

    monkeypatch.setattr(conversation_history_service, method, fail)
    reply = await client.get("/api/v1/chatbot/ai/conversation/" + kind, headers=headers(data["teacher"]))
    assert reply.status_code == 503, reply.text
    assert "SENSITIVE_DATABASE_DETAILS" not in reply.text


async def test_feedback_edits_only_the_selected_school_and_keeps_original_messages(platform_client):  # noqa: F811
    client, sessions, data = platform_client
    async with sessions() as db:
        logs = [AiChatAuditLog(user_id=data["root"].id, organization_id=org, session_id=str(uuid4()),
            user_query="Original question", ai_response="Original response")
            for org in (data["org"].id, data["other_branch"].organization_id)]
        db.add_all(logs)
        await db.commit()
        own_id, other_id = [row.id for row in logs]
    auth = {**headers(data["root"]), "X-SCS360-Organization-Id": str(data["org"].id)}
    base = "/api/v1/chatbot/ai/audit-logs/"
    body = {"quality_rating": 5, "feedback_status": "VERIFIED", "corrected_response": "Reviewed answer", "is_fine_tuning_ready": True}
    saved = await client.put(base + str(own_id) + "/verify", headers=auth, json=body)
    assert saved.status_code == 200, saved.text
    assert (await client.put(base + str(other_id) + "/verify", headers=auth, json=body)).status_code == 404
    assert (await client.put(base + "invalid/verify", headers=auth, json=body)).status_code == 400
    assert (await client.put(base + str(own_id) + "/verify", headers=headers(data["user"]), json=body)).status_code == 403
    for invalid in ({"quality_rating": 0}, {"quality_rating": 6}, {"feedback_status": "INVALID"}):
        assert (await client.put(base + str(own_id) + "/verify", headers=auth, json={**body, **invalid})).status_code == 422
    async with sessions() as db:
        own, other = await db.get(AiChatAuditLog, own_id), await db.get(AiChatAuditLog, other_id)
        assert own.user_query == other.user_query == "Original question"
        assert own.ai_response == other.ai_response == "Original response"
        assert own.corrected_response == "Reviewed answer" and own.updated_by == data["root"].id
        assert other.quality_rating == 0 and other.corrected_response is None and not other.is_fine_tuning_ready
