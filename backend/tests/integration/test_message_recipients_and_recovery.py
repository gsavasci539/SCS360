import asyncio
from uuid import uuid4

from sqlalchemy import func, select
from test_material_files import materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401

from app.core.security import create_access_token
from app.infrastructure.models.models import Branch, ChatMessage, Permission, Role, User, UserBranch, UserRole


def auth(user):
    return {"Authorization": "Bearer " + create_access_token(user.id)}


async def test_recipients_apply_relationship_and_branch_limits_to_list_and_send(materials_client):
    client, sessions, fixture = materials_client
    teacher, parent, branch = fixture["teacher"], fixture["user"], fixture["branch"]
    organization_id = fixture["org"].id
    async with sessions() as db:
        permission = await db.scalar(select(Permission).where(Permission.code == "messaging.send"))
        role = await db.scalar(select(Role).where(Role.slug == "parent", Role.organization_id == organization_id))
        await db.refresh(role, ["permissions"])
        role.permissions.append(permission)
        staff_role = Role(name="Scoped staff", slug="scoped-staff", organization_id=organization_id, permissions=[permission])
        other = Branch(name="Sibling branch", organization_id=organization_id)
        users = [
            User(email=f"{role_name}@test.invalid", password_hash="unused", first_name=role_name,
                 last_name="Test", organization_id=org)
            for role_name, org in (
                ("staff", organization_id), ("unassigned", organization_id),
                ("foreign", fixture["other_branch"].organization_id),
            )
        ]
        staff, outsider, foreign = users
        db.add_all([staff_role, other, *users])
        await db.flush()
        db.add_all([UserRole(user_id=staff.id, role_id=staff_role.id),
                    UserBranch(user_id=staff.id, branch_id=branch.id),
                    UserBranch(user_id=outsider.id, branch_id=other.id)])
        await db.commit()

    base = "/api/messages"
    for actor, expected in [(parent, {teacher.id}), (teacher, {parent.id}), (staff, {teacher.id, parent.id})]:
        result = await client.get(base + "/recipients", headers=auth(actor), params={"page_size": 1})
        assert result.status_code == 200, result.text
        page = result.json()["data"]
        assert page["total"] == len(expected)
        combined = page["items"]
        if page["total_pages"] == 2:
            combined += (await client.get(base + "/recipients", headers=auth(actor),
                params={"page": 2, "page_size": 1})).json()["data"]["items"]
        assert {row["id"] for row in combined} == {str(key) for key in expected}
        assert all("email" not in row for row in combined)
    for actor, target in [(parent, outsider), (teacher, outsider), (staff, outsider), (staff, foreign)]:
        result = await client.post(base + "/send", headers=auth(actor), json={
            "recipient_id": str(target.id), "content": "Geçici test kaydı",
        })
        assert result.status_code == 404, result.text
    assert (await client.get(base + "/recipients", headers=auth(staff),
        params={"branch_id": str(other.id)})).status_code == 404
    assert (await client.post(base + "/send", headers=auth(staff), json={
        "recipient_id": str(parent.id), "content": "Geçici test kaydı", "branch_id": str(other.id),
    })).status_code == 404


async def test_message_receipt_recovers_persisted_send_and_replay_is_idempotent(materials_client):
    client, sessions, fixture = materials_client
    teacher, parent = fixture["teacher"], fixture["user"]
    base = "/api/messages"
    request_id = str(uuid4())
    payload = {
        "request_id": request_id, "recipient_id": str(parent.id), "content": "Geçici test metni",
        "branch_id": str(fixture["branch"].id),
    }
    first, replay = await asyncio.gather(*(
        client.post(base + "/send", headers=auth(teacher), json=payload) for _ in range(2)
    ))
    assert first.status_code == 200, first.text
    assert first.json()["data"]["id"] == request_id
    assert replay.status_code == 200, replay.text
    assert replay.json()["data"] == first.json()["data"]
    mismatch = await client.post(base + "/send", headers=auth(teacher), json={**payload, "content": "Farklı"})
    assert mismatch.status_code == 409
    receipt = await client.get(f"{base}/sent/{request_id}", headers=auth(teacher),
        params={"branch_id": payload["branch_id"]})
    assert receipt.status_code == 200 and receipt.json()["data"] == first.json()["data"]
    async with sessions() as db:
        role = await db.scalar(select(Role).where(Role.slug == "parent", Role.organization_id == fixture["org"].id))
        permission = await db.scalar(select(Permission).where(Permission.code == "messaging.send"))
        await db.refresh(role, ["permissions"])
        role.permissions.append(permission)
        await db.commit()
        assert await db.scalar(select(func.count()).select_from(ChatMessage)) == 1
    assert (await client.get(f"{base}/sent/{request_id}", headers=auth(parent))).status_code == 404
