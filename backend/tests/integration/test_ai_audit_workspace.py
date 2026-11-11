"""Platform audit access needs an explicit institution and never grants native-owner access."""
from uuid import uuid4

from test_material_files import headers, materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from test_saas_platform import platform_client  # noqa: F401

from app.infrastructure.models.models import AiChatAuditLog, Role, User


async def test_audit_root_selection_and_native_owner_boundaries(platform_client):  # noqa: F811
    client, sessions, data = platform_client
    async with sessions() as db:
        owner = User(email="audit-owner@test.invalid", password_hash="unused", first_name="Owner", last_name="Test",
            organization_id=data["org"].id, roles=[Role(name="Owner", slug="owner", organization_id=data["org"].id)])
        own = AiChatAuditLog(user_id=data["root"].id, organization_id=data["org"].id,
            session_id=str(uuid4()), user_query="Own query", ai_response="Own response")
        other = AiChatAuditLog(user_id=data["root"].id, organization_id=data["other_branch"].organization_id,
            session_id=str(uuid4()), user_query="Foreign query", ai_response="Foreign response")
        db.add_all([owner, own, other])
        await db.commit()
        own_id, foreign_id = str(own.id), str(other.id)
    path = "/api/v1/chatbot/ai/audit-logs"
    root = headers(data["root"])
    assert (await client.get(path, headers=root)).status_code == 403
    assert (await client.get(path, headers=headers(owner))).status_code == 403
    assert (await client.get(path, headers=headers(data["user"]))).status_code == 403
    scoped = {**root, "X-SCS360-Organization-Id": str(data["org"].id)}
    response = await client.get(path, headers=scoped)
    assert response.status_code == 200, response.text
    assert response.json()["data"]["total"] == 1
    assert {row["id"] for row in response.json()["data"]["logs"]} == {own_id}
    assert "Foreign query" not in response.text and foreign_id not in response.text
    other_scope = {**root, "X-SCS360-Organization-Id": str(data["other_branch"].organization_id)}
    response = await client.get(path, headers=other_scope)
    assert response.status_code == 200, response.text
    assert {row["id"] for row in response.json()["data"]["logs"]} == {foreign_id}


async def test_audit_filter_uses_recorded_role_for_global_actor_and_bounds_pagination(platform_client):  # noqa: F811
    client, sessions, data = platform_client
    async with sessions() as db:
        root = await db.get(User, data["root"].id)
        root.organization_id = None
        logs = [AiChatAuditLog(user_id=root.id, organization_id=organization, session_id=str(uuid4()),
            user_query="Controlled query", ai_response="Controlled answer", meta_data=metadata)
            for organization, metadata in ((data["org"].id, {"sender_role": "SUPER_ADMIN"}),
                (data["org"].id, {"sender_role": "teacher"}), (data["org"].id, None),
                (data["other_branch"].organization_id, {"sender_role": "SUPER_ADMIN"}))]
        db.add_all(logs)
        await db.commit()
        own_admin, own_teacher, own_unknown, foreign = [str(row.id) for row in logs]
    auth = {**headers(data["root"]), "X-SCS360-Organization-Id": str(data["org"].id)}
    path = "/api/v1/chatbot/ai/audit-logs"
    for role, identifier in (("  SUPER_ADMIN  ", own_admin), (" TEACHER ", own_teacher)):
        response = await client.get(path, headers=auth, params={"role": role})
        assert response.status_code == 200, response.text
        result = response.json()["data"]
        assert result["total"] == 1 and [row["id"] for row in result["logs"]] == [identifier]
        assert result["logs"][0]["sender_role"] == role.lower().strip()
        assert result["logs"][0]["sender_name"] == f'{data["root"].first_name} {data["root"].last_name}'
        assert foreign not in response.text
    unknown = await client.get(path, headers=auth, params={"role": "no-such-role"})
    assert unknown.json()["data"]["total"] == 0
    pages = [await client.get(path, headers=auth, params={"page": page, "page_size": 1}) for page in (1, 2, 3)]
    assert all(reply.status_code == 200 and reply.json()["data"]["total"] == 3 for reply in pages)
    rows = [reply.json()["data"]["logs"][0] for reply in pages]
    assert {row["id"] for row in rows} == {own_admin, own_teacher, own_unknown}
    assert next(row for row in rows if row["id"] == own_unknown)["sender_role"] == "UNKNOWN"
    for params in ({"page": 0}, {"page": -1}, {"page_size": 0}, {"page_size": 101}, {"role": "x" * 51}):
        assert (await client.get(path, headers=auth, params=params)).status_code == 422


async def test_legacy_captured_superadmin_aliases_are_filtered_without_changing_privileges(platform_client):  # noqa: F811
    client, sessions, data = platform_client
    async with sessions() as db:
        (await db.get(User, data["root"].id)).organization_id = None
        logs = [AiChatAuditLog(user_id=data["root"].id, organization_id=org, session_id=str(uuid4()),
            user_query="Alias query", ai_response="Alias answer", meta_data={"sender_role": role})
            for org, role in ((data["org"].id, "SUPERADMIN"), (data["org"].id, "super admin"),
                (data["other_branch"].organization_id, "SUPERADMIN"))]
        db.add_all(logs)
        await db.commit()
        expected = {str(row.id) for row in logs[:2]}
    auth = {**headers(data["root"]), "X-SCS360-Organization-Id": str(data["org"].id)}
    path = "/api/v1/chatbot/ai/audit-logs"
    for role in ("SUPERADMIN", " super admin ", "super_admin", "super-admin"):
        reply = await client.get(path, headers=auth, params={"role": role})
        assert reply.status_code == 200, reply.text
        result = reply.json()["data"]
        assert result["total"] == 2 and {row["id"] for row in result["logs"]} == expected
        assert all(row["sender_role"] == "super_admin" for row in result["logs"])
    assert (await client.get(path, headers=headers(data["user"]), params={"role": "SUPERADMIN"})).status_code == 403
