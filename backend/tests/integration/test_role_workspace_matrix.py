from uuid import uuid4

import pytest

from test_material_files import materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.core.security import create_access_token
from app.infrastructure.models.models import Permission, Role, User


def headers(user):
    return {"Authorization": "Bearer " + create_access_token(user.id)}


@pytest.fixture
async def matrix_workspace(materials_client):
    client, sessions, data = materials_client
    async with sessions() as db:
        view = Permission(code="role.read", name="Read roles", module="role")
        write = Permission(code="role.write", name="Write roles", module="role")
        finance = Permission(code="finance.read", name="Read finance", module="finance")
        delegate = Role(name="Limited delegate", slug="limited_delegate", organization_id=data["org"].id, permissions=[view, write])
        owner = Role(name="Owner", slug="owner", organization_id=data["org"].id)
        target = Role(name="Institution role", slug="institution_target", organization_id=data["org"].id)
        foreign = Role(name="Foreign role", slug="foreign_target", organization_id=data["stranger"].organization_id)
        system = Role(name="System template", slug="system_sample", is_system=True)
        operator = User(email="isolated-role-root@test.invalid", password_hash="unused", first_name="Isolated", last_name="Root",
            organization_id=data["org"].id, is_super_admin=True)
        manager = User(email="isolated-role-owner@test.invalid", password_hash="unused", first_name="Isolated", last_name="Owner",
            organization_id=data["org"].id, roles=[owner])
        writer = User(email="isolated-role-delegate@test.invalid", password_hash="unused", first_name="Isolated", last_name="Delegate",
            organization_id=data["org"].id, roles=[delegate])
        db.add_all([finance, target, foreign, system, operator, manager, writer])
        await db.commit()
    return client, data, (view, write, finance), (target, foreign, system), (operator, manager, writer)


async def test_role_catalog_and_creation_stay_in_the_selected_institution(matrix_workspace):
    client, data, _, (target, foreign, system), (operator, manager, _) = matrix_workspace
    for path in ("/api/roles", f"/api/roles/{target.id}", f"/api/roles/{target.id}/permissions"):
        assert (await client.get(path, headers=headers(operator))).status_code == 403
    workspace = {**headers(operator), "X-SCS360-Organization-Id": str(data["org"].id)}
    roles = await client.get("/api/roles", headers=workspace)
    assert roles.status_code == 200, roles.text
    assert str(target.id) in {row["id"] for row in roles.json()["data"]}
    assert str(system.id) in {row["id"] for row in roles.json()["data"]}
    assert str(foreign.id) not in {row["id"] for row in roles.json()["data"]}
    path = "/api/roles"
    assert (await client.post(path, headers=headers(manager), json={"name": "Reserved", "slug": "owner"})).status_code == 422
    identity = str(uuid4())
    draft = {"name": "New institutional role", "slug": "institution_new", "request_id": identity}
    assert (await client.post(path, headers=headers(operator), json=draft)).status_code == 403
    initial = await client.post(path, headers=workspace, json=draft)
    assert initial.status_code == 200, initial.text
    assert initial.json()["data"]["id"] == identity
    retry = await client.post(path, headers=workspace, json=draft)
    assert retry.status_code == 200 and retry.json()["data"] == initial.json()["data"], retry.text
    stale = await client.post(path, headers=workspace, json={**draft, "name": "Different role"})
    assert stale.status_code == 409, stale.text


async def test_role_permission_replacement_rejects_scope_and_stale_changes(matrix_workspace):
    client, data, (view, write, finance), (target, foreign, system), (operator, manager, writer) = matrix_workspace
    path = f"/api/roles/{target.id}/permissions"
    ids = [str(finance.id)]
    response = await client.put(path, headers=headers(writer), json={"permission_ids": ids, "expected_permission_ids": []})
    assert response.status_code == 403, response.text
    approval = await client.put(path, headers=headers(manager), json={"permission_ids": ids, "expected_permission_ids": []})
    assert approval.status_code == 200, approval.text
    assert approval.json()["data"] == {"role_id": str(target.id), "permission_ids": ids}
    replay = await client.post(path, headers=headers(manager), json={"permission_ids": ids, "expected_permission_ids": []})
    assert replay.status_code == 200 and replay.json()["data"] == approval.json()["data"], replay.text
    stale = await client.put(path, headers=headers(manager), json={"permission_ids": [str(write.id)], "expected_permission_ids": []})
    assert stale.status_code == 409, stale.text
    malformed = await client.put(path, headers=headers(manager), json={})
    assert malformed.status_code == 422, malformed.text
    response = await client.get(path, headers=headers(writer))
    assert response.status_code == 200 and [row["id"] for row in response.json()["data"]] == ids, response.text
    workspace = {**headers(operator), "X-SCS360-Organization-Id": str(data["org"].id)}
    assert (await client.put(f"/api/roles/{system.id}/permissions", headers=workspace, json={"permission_ids": []})).status_code == 403
    assert (await client.get(f"/api/roles/{foreign.id}/permissions", headers=workspace)).status_code == 404
    assert (await client.get("/api/permissions", headers=headers(writer), params={"limit": 1, "offset": 1})).status_code == 200
