import asyncio
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from test_material_files import materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401

from app.core.config import get_settings
from app.core.security import create_access_token
from app.infrastructure.models.models import Branch, ChatMessage, Permission, Role, User, UserRole


def auth(user):
    return {"Authorization": "Bearer " + create_access_token(user.id)}


async def test_private_attachment_is_verified_once_and_shared_only_with_scoped_participants(materials_client):
    client, sessions, fixture = materials_client
    teacher, parent, branch, organization = (fixture[key] for key in ("teacher", "user", "branch", "org"))
    async with sessions() as db:
        permission = await db.scalar(select(Permission).where(Permission.code == "messaging.read"))
        parent_role = await db.scalar(select(Role).where(Role.organization_id == organization.id, Role.slug == "parent"))
        await db.refresh(parent_role, ["permissions"])
        parent_role.permissions.append(permission)
        read_role = Role(name="Reader", slug="attachment-test-reader", organization_id=organization.id, permissions=[permission])
        other_user = User(email="attachment-reader@test.invalid", password_hash="unused",
                         first_name="Other", last_name="Reader", organization_id=organization.id)
        other_branch = Branch(name="Sibling", organization_id=organization.id)
        db.add_all([read_role, other_user, other_branch])
        await db.flush()
        db.add(UserRole(user_id=other_user.id, role_id=read_role.id))
        await db.commit()

    base = "/api/messages"
    identifier = str(uuid4())
    form = {"request_id": identifier, "recipient_id": str(parent.id), "branch_id": str(branch.id)}
    content = b"%PDF-1.4\nSynthetic file\n%%EOF"
    files = {"file": ("../Ödev.pdf", content, "application/pdf")}
    first, second = await asyncio.gather(*(
        client.post(base + "/send-file", headers=auth(teacher), data=form, files=files) for _ in range(2)
    ))
    assert first.status_code == second.status_code == 200, (first.text, second.text)
    row = first.json()["data"]
    route = f"{base}/{identifier}/attachment"
    assert row == second.json()["data"]
    assert (row["id"], row["content"], row["attachment_url"], row["attachment_name"], row["attachment_sha256"]) == (
        identifier, "", route, "Ödev.pdf", sha256(content).hexdigest(),
    )
    receipt = await client.get(f"{base}/sent/{identifier}", headers=auth(teacher), params={"branch_id": str(branch.id)})
    assert receipt.status_code == 200 and receipt.json()["data"] == row
    assert (await client.post(base + "/send-file", headers=auth(teacher), data=form, files={
        "file": ("Ödev.pdf", b"%PDF-1.4\nDifferent", "application/pdf"),
    })).status_code == 409

    for actor in (teacher, parent):
        result = await client.get(route, headers=auth(actor), params={"branch_id": str(branch.id)})
        assert result.status_code == 200 and result.content == content
        assert result.headers["cache-control"] == "private, no-store"
        assert result.headers["x-content-type-options"] == "nosniff"
        assert result.headers["content-disposition"].startswith("attachment;")
    assert (await client.get(route, headers=auth(other_user))).status_code == 404
    assert (await client.get(route, headers=auth(parent), params={"branch_id": str(other_branch.id)})).status_code == 404
    assert (await client.get(route)).status_code == 401
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(ChatMessage)) == 1
    private_files = [path for path in Path(get_settings().PRIVATE_UPLOAD_DIR).rglob("*") if path.is_file()]
    assert len(private_files) == 1 and private_files[0].read_bytes() == content


async def test_invalid_upload_and_caller_url_are_rejected_and_legacy_link_stays_private(materials_client, monkeypatch):
    client, sessions, fixture = materials_client
    teacher, parent = fixture["teacher"], fixture["user"]
    base = "/api/messages"
    identifier = uuid4()
    legacy_link = "https://legacy.invalid/document.pdf"
    async with sessions() as db:
        db.add(ChatMessage(id=identifier, sender_id=teacher.id, recipient_id=parent.id,
                           content="Legacy text", attachment_url=legacy_link))
        await db.commit()
    form = {"request_id": str(uuid4()), "recipient_id": str(parent.id)}
    monkeypatch.setattr(get_settings(), "MAX_UPLOAD_SIZE_MB", 1)
    for filename, contents in (("false.pdf", b"wrong signature"), ("active.html", b"file"),
                               ("large.pdf", b"%PDF-" + b"x" * (1024 * 1024))):
        result = await client.post(base + "/send-file", headers=auth(teacher), data=form,
                                   files={"file": (filename, contents, "application/pdf")})
        assert result.status_code == 422, result.text
    result = await client.post(base + "/send", headers=auth(teacher), json={
        "recipient_id": str(parent.id), "content": "Geçici test", "attachment_url": legacy_link,
    })
    assert result.status_code == 422
    history = await client.get(f"{base}/conversation/{parent.id}", headers=auth(teacher))
    assert history.status_code == 200
    assert history.json()["data"][0]["attachment_url"] is None
    assert (await client.get(f"{base}/{identifier}/attachment", headers=auth(teacher))).status_code == 404
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(ChatMessage)) == 1
        assert await db.scalar(select(ChatMessage.attachment_url)) == legacy_link
    assert not any(Path(get_settings().PRIVATE_UPLOAD_DIR).rglob("*"))


async def test_message_is_rolled_back_when_private_storage_fails(materials_client, monkeypatch):
    client, sessions, fixture = materials_client
    teacher, parent = fixture["teacher"], fixture["user"]

    async def fail(*_):
        raise OSError("Synthetic storage failure")

    monkeypatch.setattr("app.routers.messages.save_message_attachment", fail)
    identifier = str(uuid4())
    with pytest.raises(OSError, match="Synthetic storage failure"):
        await client.post("/api/messages/send-file", headers=auth(teacher),
            data={"request_id": identifier, "recipient_id": str(parent.id)},
            files={"file": ("Test.pdf", b"%PDF-1.4\nSynthetic", "application/pdf")})
    assert (await client.get(f"/api/messages/sent/{identifier}", headers=auth(teacher))).status_code == 404
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(ChatMessage)) == 0
