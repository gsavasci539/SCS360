from sqlalchemy import select

from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.infrastructure.models.models import Branch, Permission, Role, User, UserBranch, UserRole


async def test_access_assignment_limits_delegation_and_rejects_stale_snapshots(materials_client):
    client, sessions, data = materials_client
    organization = data["org"].id
    branch = data["branch"].id
    async with sessions() as db:
        read = Permission(code="users.read", name="Read users", module="users")
        write = Permission(code="users.write", name="Manage users", module="users")
        finance = Permission(code="finance.read", name="Finance", module="finance")
        delegate = Role(name="Branch delegate", slug="branch_delegate", organization_id=organization, permissions=[read, write])
        owner = Role(name="Owner", slug="owner", organization_id=organization)
        valid = Role(name="Readable access", slug="role_operator_read", organization_id=organization, permissions=[read])
        restricted = Role(name="Restricted access", slug="role_finance_read", organization_id=organization, permissions=[finance])
        alternate = Branch(name="Second allowed branch", organization_id=organization)
        other = Branch(name="Other assigned branch", organization_id=organization)
        writer = User(organization_id=organization, email="isolated-delegate-access@test.invalid",
            first_name="Test", last_name="Writer", password_hash="unused", roles=[delegate], branches=[data["branch"], alternate])
        principal = User(organization_id=organization, email="isolated-owner-access@test.invalid",
            first_name="Test", last_name="Owner", password_hash="unused", roles=[owner])
        target = User(organization_id=organization, email="isolated-target-access@test.invalid",
            first_name="Test", last_name="Target", password_hash="unused", branches=[data["branch"]])
        db.add_all([writer, principal, target, valid, restricted, other])
        await db.commit()

    path = f"/api/users/{target.id}/access"
    person = {"first_name": "Isolated", "last_name": "Creation", "email": "isolated-branch-creation@test.invalid",
        "password": "TestPassword-2026"}
    missing = await client.post("/api/users", headers=headers(writer), json=person)
    assert missing.status_code == 422, missing.text
    created = await client.post("/api/users", headers=headers(writer), json={**person, "branch_id": str(branch)})
    assert created.status_code == 200, created.text
    created_id = created.json()["data"]["id"]
    verified = await client.get(f"/api/users/{created_id}", headers=headers(writer))
    assert verified.status_code == 200 and verified.json()["data"]["id"] == created_id, verified.text
    assigned = await client.get(f"/api/users/{created_id}/branches", headers=headers(writer))
    assert assigned.status_code == 200 and [row["id"] for row in assigned.json()["data"]] == [str(branch)], assigned.text
    visible = await client.get("/api/users", headers=headers(writer), params={"branch_id": str(branch)})
    assert created_id in {row["id"] for row in visible.json()["data"]["items"]}, visible.text
    outside = await client.get("/api/users", headers=headers(writer), params={"branch_id": str(other.id)})
    assert outside.status_code == 404, outside.text
    new = {"role_ids": [str(valid.id)], "branch_ids": [str(alternate.id)], "expected_role_ids": [], "expected_branch_ids": [str(branch)]}
    denied = await client.put(path, headers=headers(writer), json={**new, "role_ids": [str(restricted.id)]})
    assert denied.status_code == 403, denied.text
    async with sessions() as db:
        assert (await db.scalars(select(UserBranch.branch_id).where(UserBranch.user_id == target.id))).all() == [branch]
        assert not (await db.scalars(select(UserRole.role_id).where(UserRole.user_id == target.id))).all()
    result = await client.put(path, headers=headers(writer), json=new)
    assert result.status_code == 200, result.text
    assert result.json()["data"] == {"user_id": str(target.id), "role_ids": new["role_ids"], "branch_ids": new["branch_ids"]}
    replay = await client.put(path, headers=headers(writer), json=new)
    assert replay.status_code == 200 and replay.json()["data"] == result.json()["data"], replay.text
    owner_role = await client.put(path, headers=headers(writer), json={**new, "expected_role_ids": new["role_ids"],
        "expected_branch_ids": new["branch_ids"], "role_ids": [str(owner.id)]})
    assert owner_role.status_code == 403, owner_role.text
    widened = await client.put(path, headers=headers(writer), json={**new, "expected_role_ids": new["role_ids"],
        "expected_branch_ids": new["branch_ids"], "branch_ids": []})
    assert widened.status_code == 403, widened.text
    stale = await client.put(path, headers=headers(principal), json={**new, "role_ids": [str(restricted.id)]})
    assert stale.status_code == 409, stale.text
    accepted = await client.put(path, headers=headers(principal), json={**new, "expected_role_ids": new["role_ids"],
        "expected_branch_ids": new["branch_ids"], "role_ids": [str(restricted.id)], "branch_ids": [str(other.id)]})
    assert accepted.status_code == 200, accepted.text
    async with sessions() as db:
        assert (await db.scalars(select(UserBranch.branch_id).where(UserBranch.user_id == target.id))).all() == [other.id]
        assert (await db.scalars(select(UserRole.role_id).where(UserRole.user_id == target.id))).all() == [restricted.id]
