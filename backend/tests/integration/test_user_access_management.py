from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from test_saas_platform import platform_client, plan_and_tenant  # noqa: F401
from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.infrastructure.models.models import Branch, User, UserRole, UserBranch


async def test_owner_assigns_roles_and_branches_atomically_without_cross_tenant_access(platform_client):
    client, sessions, data = platform_client
    plan, tenant, body = await plan_and_tenant(client, data)
    async with sessions() as db:
        owner = (await db.execute(select(User).options(selectinload(User.branches))
            .where(User.email == body["owner_email"]))).scalar_one()
    auth = headers(owner)
    branch = await client.post("/api/branches", headers=auth, json={"organization_id": tenant["organization_id"], "name": "Owner Branch"})
    assert branch.status_code == 200, branch.text
    options = await client.get("/api/users/options", headers=auth)
    assert options.status_code == 200, options.text
    choices = options.json()["data"]
    assert [row["id"] for row in choices["organizations"]] == [tenant["organization_id"]]
    assert [row["id"] for row in choices["branches"]] == [branch.json()["data"]["id"]]
    assert (await client.get("/api/users/options", headers=auth, params={"organization_id": str(data["org"].id)})).status_code == 403
    created = await client.post("/api/users", headers=auth, json={"email": "new-staff@example.com", "password": "AcceptancePass1!", "first_name": "New", "last_name": "Staff"})
    assert created.status_code == 200, created.text
    identifier = created.json()["data"]["id"]; role = choices["roles"][0]["id"]; branch_id = choices["branches"][0]["id"]
    rejected = await client.put(f"/api/users/{identifier}/access", headers=auth, json={"role_ids": [role], "branch_ids": [str(data["other_branch"].id)]})
    assert rejected.status_code in {403, 404}, rejected.text
    async with sessions() as db:
        assert (await db.execute(select(UserRole).where(UserRole.user_id == UUID(identifier)))).scalars().all() == []
    accepted = await client.put(f"/api/users/{identifier}/access", headers=auth, json={"role_ids": [role, role], "branch_ids": [branch_id, branch_id]})
    assert accepted.status_code == 200, accepted.text
    assert (await client.put(f"/api/users/{identifier}/access", headers=auth, json={"role_ids": [role], "branch_ids": [branch_id]})).status_code == 200
    async with sessions() as db:
        assert len((await db.execute(select(UserRole).where(UserRole.user_id == UUID(identifier)))).scalars().all()) == 1
        assert len((await db.execute(select(UserBranch).where(UserBranch.user_id == UUID(identifier)))).scalars().all()) == 1
    assert (await client.post(f"/api/users/{identifier}/roles", headers=auth, json={"role_ids": ["invalid"]})).status_code == 422
    login = await client.post("/api/auth/login", json={"email": "new-staff@example.com", "password": "AcceptancePass1!"})
    assert login.status_code == 200 and login.json()["data"]["user"]["branch_ids"] == [branch_id], login.text


async def test_owner_with_one_assigned_branch_can_open_every_branch_in_own_institution(platform_client):
    client, sessions, data = platform_client
    plan, tenant, body = await plan_and_tenant(client, data, branch_limit=3)
    async with sessions() as db:
        owner = (await db.execute(select(User).where(User.email == body["owner_email"]))).scalar_one()
    auth = headers(owner); org_id = tenant["organization_id"]
    created = await client.post("/api/branches", headers=auth,
        json={"organization_id": org_id, "name": "Owner scope API branch"})
    assert created.status_code == 200, created.text
    branch_ids = {created.json()["data"]["id"]}
    async with sessions() as db:
        owner = (await db.execute(select(User).options(selectinload(User.branches))
            .where(User.id == owner.id))).scalar_one()
        assigned = next(iter(branch_ids))
        branch = (await db.execute(select(Branch).where(Branch.id == UUID(assigned)))).scalar_one()
        owner.branches = [branch]
        other_branch = Branch(name="Owner scope unassigned branch", organization_id=UUID(org_id))
        db.add(other_branch)
        await db.commit()
        branch_ids.add(str(other_branch.id))
    rows = await client.get("/api/branches", headers=headers(owner), params={"organization_id": org_id})
    assert rows.status_code == 200, rows.text
    actual_ids = {row["id"] for row in rows.json()["data"]["items"]}
    assert actual_ids == branch_ids, {"actual": actual_ids, "expected": branch_ids, "rows": rows.json()}
    foreign = await client.get(f'/api/branches/{data["branch"].id}', headers=headers(owner))
    assert foreign.status_code == 404, foreign.text
