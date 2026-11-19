from asyncio import gather
from hashlib import sha256
from uuid import uuid4

import pytest
from sqlalchemy import select
from test_material_files import headers, materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401

from app.infrastructure.models.models import (
    Branch,
    ChatConversation,
    ClassRoom,
    Parent,
    Role,
    Student,
    StudentParent,
    User,
)

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


async def test_staff_chat_directory_and_conversation_keep_student_guardian_and_branch_scope(materials_client):  # noqa: F811
    client, sessions, data = materials_client
    child = data["children"][0]
    teacher = data["teacher"]
    parent = data["user"]
    organization = data["org"].id
    async with sessions() as db:
        branch = Branch(name="Second branch", organization_id=organization)
        role = Role(name="Owner", slug="owner", organization_id=organization)
        owner = User(email="chat-owner@fixture.invalid", password_hash="unused", first_name="Owner", last_name="Fixture",
            organization_id=organization, roles=[role])
        other_account = User(email="other-guardian@fixture.invalid", password_hash="unused", first_name="Other", last_name="Guardian",
            organization_id=organization)
        db.add_all([branch, owner, other_account])
        await db.flush()
        classroom = ClassRoom(name="Other class", organization_id=organization, branch_id=branch.id)
        db.add(classroom)
        await db.flush()
        other_student = Student(first_name="Other branch learner", last_name="Fixture", organization_id=organization,
            branch_id=branch.id, class_id=classroom.id)
        other_guardian = Parent(user_id=other_account.id, organization_id=organization, first_name="Other", last_name="Guardian")
        db.add_all([other_student, other_guardian])
        await db.flush()
        db.add(StudentParent(student_id=other_student.id, parent_id=other_guardian.id))
        await db.commit()

    result = await client.get("/api/teacher/chat-contacts", headers=headers(teacher), params={"page_size": 1})
    assert result.status_code == 200, result.text
    result = result.json()["data"]
    assert result["total"] == 2 and result["total_pages"] == 2
    assert result["items"][0]["parent_id"] == str(parent.id)
    assert (await client.get("/api/teacher/chat-contacts", headers=headers(parent))).status_code == 403
    result = await client.get("/api/admin/chat-contacts", headers=headers(owner),
        params={"branch_id": str(branch.id), "search": "guardian"})
    assert result.status_code == 200, result.text
    assert [r["student_id"] for r in result.json()["data"]["items"]] == [str(other_student.id)]
    assert result.json()["data"]["items"][0]["branch_id"] == str(branch.id)
    foreign_branch = await client.get("/api/admin/chat-contacts", headers=headers(owner),
        params={"branch_id": str(data["other_branch"].id)})
    assert foreign_branch.status_code in (403, 404)

    path = f"/api/admin/chat/{child.id}"
    payload = {"message": "Branch-bound reply", "request_id": str(uuid4())}
    wrong_branch = await client.post(path, headers=headers(owner), json=payload,
        params={"parent_id": str(parent.id), "branch_id": str(branch.id)})
    assert wrong_branch.status_code == 404
    wrong_parent = await client.get(path, headers=headers(owner), params={"parent_id": str(other_account.id)})
    assert wrong_parent.status_code == 404
    valid = {"parent_id": str(parent.id), "branch_id": str(child.branch_id)}
    saved = await client.post(path, headers=headers(owner), json=payload, params=valid)
    assert saved.status_code == 200, saved.text
    assert saved.json()["data"]["receiver_id"] == str(parent.id)
    receipt = await client.get(f"{path}/sent/{payload['request_id']}", headers=headers(owner), params=valid)
    assert receipt.json()["data"] == saved.json()["data"]
