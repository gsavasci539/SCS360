from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select
from test_material_files import materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401

from app.core.security import create_access_token
from app.infrastructure.models.models import Branch, ChatConversation, ChatMessage, User


async def test_conversation_list_history_and_read_use_identical_branch_scope(materials_client):
    client, sessions, fixture = materials_client
    teacher, parent, branch, org = (fixture[name] for name in ("teacher", "user", "branch", "org"))
    timestamp = datetime(2026, 11, 19, 12, tzinfo=UTC)
    older, current, outside_branch, outside_org, unverifiable = [uuid4() for _ in range(5)]
    async with sessions() as db:
        sibling = Branch(name="Sibling", organization_id=org.id)
        foreign = User(email="other-message-user@test.invalid", password_hash="unused", first_name="Other",
                       last_name="Organization", organization_id=fixture["other_branch"].organization_id)
        thread = ChatConversation(student_id=fixture["children"][0].id, parent_id=parent.id,
                                 teacher_id=teacher.id, subject_context="Recorded thread")
        db.add_all([sibling, foreign, thread])
        await db.flush()
        db.add_all([
            ChatMessage(id=older, sender_id=parent.id, recipient_id=teacher.id, conversation_id=thread.id,
                        sent_at=timestamp, content="Eski şube kaydı"),
            ChatMessage(id=current, sender_id=parent.id, recipient_id=teacher.id, organization_id=org.id,
                        branch_id=branch.id, sent_at=timestamp + timedelta(minutes=1), content="Seçili şube kaydı"),
            ChatMessage(id=outside_branch, sender_id=parent.id, recipient_id=teacher.id, organization_id=org.id,
                        branch_id=sibling.id, sent_at=timestamp + timedelta(minutes=2), content="Diğer şube"),
            ChatMessage(id=outside_org, sender_id=foreign.id, recipient_id=teacher.id,
                        sent_at=timestamp, content="Diğer kurum"),
            ChatMessage(id=unverifiable, sender_id=foreign.id, recipient_id=teacher.id, conversation_id=thread.id,
                        sent_at=timestamp, content="Katılımcısı doğrulanamayan kayıt"),
        ])
        await db.commit()
    headers = {"Authorization": "Bearer " + create_access_token(teacher.id)}
    base = "/api/messages"
    params = {"branch_id": str(branch.id)}
    summary = await client.get(base + "/conversations", headers=headers, params=params)
    assert summary.status_code == 200, summary.text
    item, = summary.json()["data"]
    assert item["user_id"] == str(parent.id)
    assert item["unread_count"] == 2
    assert item["last_message"]["id"] == str(current)
    assert (await client.put(f"{base}/{outside_branch}/read", headers=headers, params=params)).status_code == 404
    assert (await client.put(f"{base}/{outside_org}/read", headers=headers, params=params)).status_code == 404
    thread_url = f"{base}/conversation/{parent.id}"
    assert (await client.get(thread_url, headers=headers,
        params={**params, "before_id": str(outside_branch)})).status_code == 404
    page = await client.get(thread_url, headers=headers, params={**params, "limit": 1})
    assert page.status_code == 200, page.text
    assert [row["id"] for row in page.json()["data"]] == [str(current)]
    mark = await client.post(thread_url + "/mark-all-read", headers=headers, params=params)
    assert mark.status_code == 200 and mark.json()["data"]["marked_count"] == 1
    async with sessions() as db:
        states = dict((await db.execute(select(ChatMessage.id, ChatMessage.is_read))).all())
    assert states == {older: True, current: True, outside_branch: False, outside_org: False, unverifiable: False}
    all_branches = await client.get(thread_url, headers=headers)
    assert [row["id"] for row in all_branches.json()["data"]] == [str(older), str(current), str(outside_branch)]


async def test_platform_sender_receipt_and_request_id_stay_in_selected_institution(materials_client):
    client, sessions, fixture = materials_client
    other_org = fixture["other_branch"].organization_id
    async with sessions() as db:
        root = User(email="root-messaging@test.invalid", password_hash="unused", first_name="Platform",
                    last_name="Operator", is_super_admin=True)
        other = User(email="other-school@test.invalid", password_hash="unused", first_name="Other",
                     last_name="Account", organization_id=other_org)
        db.add_all([root, other])
        await db.commit()
    auth = {"Authorization": "Bearer " + create_access_token(root.id)}
    first_workspace = {**auth, "X-SCS360-Organization-Id": str(fixture["org"].id)}
    second_workspace = {**auth, "X-SCS360-Organization-Id": str(other_org)}
    request_id = str(uuid4())
    payload = {"request_id": request_id, "recipient_id": str(fixture["user"].id), "content": "Geçici test kaydı"}
    base = "/api/messages"
    assert (await client.get(base + "/conversations", headers=auth)).status_code == 403
    sent = await client.post(base + "/send", headers=first_workspace, json=payload)
    assert sent.status_code == 200, sent.text
    replay = await client.post(base + "/send", headers=second_workspace, json={**payload, "recipient_id": str(other.id)})
    assert replay.status_code == 409, replay.text
    assert (await client.get(base + "/conversations", headers=second_workspace)).json()["data"] == []
    receipt = f"{base}/sent/{request_id}"
    assert (await client.get(receipt, headers=second_workspace)).status_code == 404
    assert (await client.get(receipt, headers=first_workspace)).json()["data"]["id"] == request_id
