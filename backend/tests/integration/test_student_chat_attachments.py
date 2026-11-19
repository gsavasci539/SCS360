from asyncio import gather
from hashlib import sha256
from uuid import uuid4

import pytest
from sqlalchemy import select
from test_material_files import headers, materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401

from app.infrastructure.models.models import ChatConversation

PDF = b"%PDF-1.4\nstudent chat test\n"


async def test_student_chat_file_is_private_and_recoverable(materials_client):  # noqa: F811
    client, sessions, data = materials_client
    child, sibling = data["children"]
    teacher, parent = data["teacher"], data["user"]
    parent_path = f"/api/parent/child/{child.id}/chat/{teacher.id}"
    teacher_path = f"/api/teacher/chat/{child.id}"
    request_id = str(uuid4())
    attachment = {"file": ("rapor.pdf", PDF, "application/pdf")}

    first, replay = await gather(*(client.post(f"{parent_path}/send-file", headers=headers(parent),
        data={"request_id": request_id}, files=attachment) for _ in range(2)))
    assert first.status_code == replay.status_code == 200, (first.text, replay.text)
    receipt = first.json()["data"]
    assert receipt["id"] == request_id and receipt["content"] == ""
    assert receipt["attachment_name"] == "rapor.pdf" and receipt["attachment_sha256"] == sha256(PDF).hexdigest()
    assert replay.json()["data"] == receipt
    conflict = await client.post(f"{parent_path}/send-file", headers=headers(parent),
        data={"request_id": request_id, "message": "Farklı içerik"}, files=attachment)
    assert conflict.status_code == 409
    assert (await client.get(f"{parent_path}/sent/{request_id}", headers=headers(parent))).json()["data"] == receipt
    assert (await client.get(f"{teacher_path}/sent/{request_id}", headers=headers(teacher))).status_code == 404

    listing = (await client.get(teacher_path, headers=headers(teacher))).json()["data"]
    assert [(row["id"], row["attachment_name"], row["is_current_user"]) for row in listing] == [
        (request_id, "rapor.pdf", False)
    ]
    for path, actor in ((parent_path, parent), (teacher_path, teacher)):
        result = await client.get(f"{path}/attachments/{request_id}", headers=headers(actor))
        assert result.status_code == 200 and result.content == PDF
        assert result.headers["cache-control"] == "private, no-store"
        assert result.headers["x-content-type-options"] == "nosniff"
    assert (await client.get(f"{parent_path}/attachments/{request_id}")).status_code == 401
    wrong = f"/api/parent/child/{sibling.id}/chat/{teacher.id}"
    assert (await client.get(f"{wrong}/attachments/{request_id}", headers=headers(parent))).status_code == 404
    foreign = f'/api/parent/child/{data["stranger"].id}/chat/{teacher.id}'
    assert (await client.get(f"{foreign}/attachments/{request_id}", headers=headers(parent))).status_code == 403

    admin_path = f"/api/admin/chat/{child.id}"
    invalid = await client.post(f"{admin_path}/send-file", headers=headers(teacher),
        data={"request_id": str(uuid4())}, files={"file": ("invalid.pdf", b"invalid", "application/pdf")})
    assert invalid.status_code == 422
    reply_id = str(uuid4())
    first, second = await gather(*(client.post(f"{admin_path}/send-file", headers=headers(teacher),
        params={"parent_id": str(parent.id)}, data={"request_id": reply_id, "message": "Yanıt"},
        files=attachment) for _ in range(2)))
    assert first.status_code == second.status_code == 200, (first.text, second.text)
    assert first.json()["data"] == second.json()["data"]
    async with sessions() as db:
        conversation = await db.scalar(select(ChatConversation).where(ChatConversation.student_id == child.id))
        assert conversation.parent_unread_count == 1
    reply = await client.get(f"{parent_path}/attachments/{reply_id}", headers=headers(parent))
    assert reply.status_code == 200 and reply.content == PDF


async def test_failed_private_write_rolls_back_first_message_and_thread(materials_client, monkeypatch):  # noqa: F811
    from app.application.services import student_chat_messages

    async def unavailable(*_args):
        raise OSError("Synthetic storage failure")

    client, sessions, data = materials_client
    child = data["children"][0]
    path = f'/api/parent/child/{child.id}/chat/{data["teacher"].id}'
    actor = headers(data["user"])
    request_id = str(uuid4())
    with monkeypatch.context() as patch:
        patch.setattr(student_chat_messages, "save_message_attachment", unavailable)
        with pytest.raises(OSError, match="Synthetic storage failure"):
            await client.post(f"{path}/send-file", headers=actor, data={"request_id": request_id},
                files={"file": ("rapor.pdf", PDF, "application/pdf")})
    assert (await client.get(f"{path}/sent/{request_id}", headers=actor)).status_code == 404
    async with sessions() as db:
        assert await db.scalar(select(ChatConversation).where(ChatConversation.student_id == child.id)) is None
    saved = await client.post(path, headers=actor, json={"message": "Yazılı mesaj", "request_id": request_id})
    assert saved.status_code == 200
    assert (await client.get(f"{path}/sent/{request_id}", headers=actor)).json()["data"] == saved.json()["data"]
