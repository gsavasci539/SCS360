import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.infrastructure.models.models import Organization, User


@pytest.fixture
async def platform_client(materials_client):
    client, sessions, data = materials_client
    async with sessions() as db:
        root = User(email="platform@test.invalid", password_hash="unused", first_name="Platform", last_name="Owner", is_super_admin=True)
        db.add(root); await db.commit()
    return client, sessions, {**data, "root": root}


async def plan_and_tenant(client, data, **limits):
    plan = await client.post("/api/platform/plans", headers=headers(data["root"]), json={
        "code": "PKG" + uuid4().hex[:8], "name": "Acceptance package", "branch_limit": 1,
        "student_limit": 1, "user_limit": 2, "price": "100.00", **limits})
    assert plan.status_code == 200, plan.text
    body = {"name": "New school", "owner_email": "new-owner@example.com", "owner_password": "AcceptancePass1!",
        "owner_first_name": "School", "owner_last_name": "Owner", "plan_id": plan.json()["data"]["id"], "request_id": str(uuid4())}
    created = await client.post("/api/platform/tenants", headers=headers(data["root"]), json=body)
    assert created.status_code == 200, created.text
    return plan.json()["data"], created.json()["data"], body


async def test_only_platform_can_provision_and_retries_do_not_duplicate_school_or_owner(platform_client):
    client, sessions, data = platform_client
    plan, tenant, body = await plan_and_tenant(client, data)
    denied = await client.get("/api/platform/plans", headers=headers(data["teacher"]))
    assert denied.status_code == 403, denied.text
    retries = await asyncio.gather(*[client.post("/api/platform/tenants", headers=headers(data["root"]), json=body) for _ in range(2)])
    assert all(row.status_code == 200 and row.json()["data"] == tenant for row in retries), [row.text for row in retries]
    assert (await client.post("/api/platform/tenants", headers=headers(data["root"]), json={**body, "name": "Changed"})).status_code == 409
    async with sessions() as db:
        owner = (await db.execute(select(User).where(User.email == body["owner_email"])) ).scalar_one()
        assert owner.organization_id == UUID(tenant["organization_id"]) and owner.is_super_admin is False
        assert (await db.execute(select(func.count(Organization.id)).where(Organization.name == "New school"))).scalar() == 1
    assert (await client.post("/api/platform/plans", headers=headers(owner), json={"name": "Forged"})).status_code == 403
    login = await client.post("/api/auth/login", json={"email": body["owner_email"], "password": body["owner_password"]})
    assert login.status_code == 200 and login.json()["data"]["user"]["organization_access"]["status"] == "ACTIVE", login.text


async def test_platform_summary_and_billing_delegate_are_tenant_scoped(platform_client):
    client, sessions, data = platform_client
    plan, tenant, body = await plan_and_tenant(client, data)
    root = headers(data["root"]); org = tenant["organization_id"]
    response = await client.get("/api/platform/summary", headers=root)
    assert response.status_code == 200 and response.json()["data"]["active_memberships"] == 1, response.text
    users = await client.get(f"/api/platform/tenants/{org}/users", headers=root)
    assert users.status_code == 200 and [row["email"] for row in users.json()["data"]] == [body["owner_email"]], users.text
    async with sessions() as db:
        member_owner = (await db.execute(select(User).where(User.email == body["owner_email"]))).scalar_one()
        delegate = User(organization_id=UUID(org), email="billing@example.com", password_hash="unused", first_name="Billing", last_name="Delegate", roles=[], branches=[])
        db.add(delegate); await db.commit()
    now = datetime.now(UTC)
    request = {"plan_id": plan["id"], "period_start": now.isoformat(), "period_end": (now + timedelta(days=30)).isoformat()}
    invalid = await client.put(f"/api/platform/tenants/{org}/subscription", headers=root, json={**request, "owner_user_id": str(data["teacher"].id)})
    assert invalid.status_code == 422, invalid.text
    valid = await client.put(f"/api/platform/tenants/{org}/subscription", headers=root, json={**request, "owner_user_id": str(delegate.id)})
    assert valid.status_code == 200, valid.text
    auth = headers(delegate)
    assert (await client.get("/api/subscription/access", headers=auth)).json()["data"]["can_manage"] is True
    assert (await client.get("/api/subscription/plans", headers=auth)).status_code == 200
    assert (await client.get("/api/platform/summary", headers=auth)).status_code == 403
    assert (await client.get(f"/api/platform/tenants/{org}/users", headers=headers(member_owner))).status_code == 403


async def test_package_quotas_are_atomic_for_branch_student_and_login_accounts(platform_client):
    client, sessions, data = platform_client
    plan, tenant, body = await plan_and_tenant(client, data)
    async with sessions() as db:
        owner = (await db.execute(select(User).where(User.email == body["owner_email"]))).scalar_one()
    auth = headers(owner); org = tenant["organization_id"]
    branches = await asyncio.gather(*[client.post("/api/branches", headers=auth, json={"organization_id": org, "name": f"Branch {i}"}) for i in range(2)])
    assert sorted(row.status_code for row in branches) == [200, 409], [row.text for row in branches]
    branch = next(row.json()["data"]["id"] for row in branches if row.status_code == 200)
    students = await asyncio.gather(*[client.post("/api/students", headers=auth, json={"organization_id": org, "branch_id": branch,
        "first_name": f"Child{i}", "last_name": "Quota"}) for i in range(2)])
    assert sorted(row.status_code for row in students) == [200, 409], [row.text for row in students]
    accounts = await asyncio.gather(*[client.post("/api/users", headers=auth, json={"email": f"quota{i}@test.invalid", "password": "AcceptancePass1!",
        "first_name": "Account", "last_name": str(i)}) for i in range(2)])
    assert sorted(row.status_code for row in accounts) == [200, 409], [row.text for row in accounts]


async def test_owner_account_crud_loads_roles_and_cannot_modify_the_platform_identity(platform_client):
    client, sessions, data = platform_client
    plan, tenant, body = await plan_and_tenant(client, data)
    async with sessions() as db:
        owner = (await db.execute(select(User).where(User.email == body["owner_email"]))).scalar_one()
        # Existing installations may keep a platform administrator in a school organization.
        root = await db.get(User, data["root"].id); root.organization_id = owner.organization_id; await db.commit()
    auth = headers(owner)
    created = await client.post("/api/users", headers=auth, json={"email": "staff@example.com", "password": "AcceptancePass1!", "first_name": "Staff", "last_name": "Account"})
    assert created.status_code == 200, created.text
    identifier = created.json()["data"]["id"]
    detail = await client.get(f"/api/users/{identifier}", headers=auth)
    assert detail.status_code == 200 and detail.json()["data"]["roles"] == [], detail.text
    changed = await client.put(f"/api/users/{identifier}", headers=auth, json={"first_name": "Updated", "status": "PASSIVE"})
    assert changed.status_code == 200 and changed.json()["data"]["first_name"] == "Updated", changed.text
    invalid = await client.put(f"/api/users/{identifier}", headers=auth, json={"status": "INVALID"})
    assert invalid.status_code == 422, invalid.text
    denied = await client.put(f'/api/users/{data["root"].id}', headers=auth, json={"password": "ForgedPlatformPassword1!"})
    assert denied.status_code in {403, 404}, denied.text
    assert (await client.delete(f'/api/users/{data["root"].id}', headers=auth)).status_code in {403, 404}
    assert (await client.put(f'/api/users/{data["root"].id}', headers=headers(data["root"]), json={"status": "PASSIVE"})).status_code == 409


async def test_expired_or_closed_school_cannot_use_old_token_but_can_open_billing(platform_client):
    client, sessions, data = platform_client
    plan, tenant, body = await plan_and_tenant(client, data)
    async with sessions() as db:
        owner = (await db.execute(select(User).where(User.email == body["owner_email"]))).scalar_one()
    auth = headers(owner); root = headers(data["root"]); org = tenant["organization_id"]
    now = datetime.now(UTC)
    membership = {"plan_id": plan["id"], "period_start": (now - timedelta(days=40)).isoformat(), "period_end": (now - timedelta(days=11)).isoformat()}
    changed = await client.put(f"/api/platform/tenants/{org}/subscription", headers=root, json=membership)
    assert changed.status_code == 200, changed.text
    denied = await client.get("/api/users", headers=auth)
    assert denied.status_code == 402, denied.text
    access = await client.get("/api/subscription/access", headers=auth)
    assert access.status_code == 200 and access.json()["data"]["access"]["status"] == "PAST_DUE", access.text
    me = await client.get("/api/auth/me", headers=auth)
    assert me.status_code == 200 and me.json()["data"]["organization_access"]["restricted"] is True, me.text
    closed = await client.patch(f"/api/platform/tenants/{org}/status", headers=root, json={"is_active": False})
    assert closed.status_code == 200, closed.text
    membership["period_end"] = (now + timedelta(days=30)).isoformat()
    assert (await client.put(f"/api/platform/tenants/{org}/subscription", headers=root, json=membership)).status_code == 200
    assert (await client.get("/api/subscription/access", headers=auth)).json()["data"]["access"]["status"] == "SUSPENDED"
    assert (await client.patch(f"/api/platform/tenants/{org}/status", headers=root, json={"is_active": True})).status_code == 200
    assert (await client.get("/api/users", headers=auth)).status_code == 200


async def test_import_cannot_bypass_student_capacity_or_create_unmanaged_new_schools(platform_client):
    client, sessions, data = platform_client
    plan, tenant, body = await plan_and_tenant(client, data)
    async with sessions() as db:
        owner = (await db.execute(select(User).where(User.email == body["owner_email"]))).scalar_one()
    auth = headers(owner)
    created = await client.post("/api/branches", headers=auth, json={"organization_id": tenant["organization_id"], "name": "Import branch"})
    assert created.status_code == 200, created.text
    branch = created.json()["data"]["id"]
    csv = f"first_name,last_name,branch_id\nFirst,Import,{branch}\nSecond,Import,{branch}\n".encode()
    imported = await client.post("/api/import/students", headers=auth, files={"file": ("students.csv", csv, "text/csv")})
    assert imported.status_code == 200, imported.text
    assert imported.json()["data"]["imported"] == 1 and len(imported.json()["data"]["errors"]) == 1
    from app.domain.entities.saas import OrganizationSubscription
    created = await client.post("/api/organizations", headers=headers(data["root"]), json={"name": "Needs package"})
    assert created.status_code == 200, created.text
    async with sessions() as db:
        sub = await db.get(OrganizationSubscription, UUID(created.json()["data"]["id"]))
        assert sub is not None and sub.package_snapshot is None


async def test_catalog_changes_do_not_reprice_existing_membership_and_school_cannot_edit_catalog(platform_client):
    client, sessions, data = platform_client
    plan, tenant, body = await plan_and_tenant(client, data)
    async with sessions() as db:
        owner = (await db.execute(select(User).where(User.email == body["owner_email"]))).scalar_one()
    values = {key: value for key, value in plan.items() if key != "id"}
    values.update(price="200.00", student_limit=5)
    assert (await client.put(f'/api/platform/plans/{plan["id"]}', headers=headers(owner), json=values)).status_code == 403
    updated = await client.put(f'/api/platform/plans/{plan["id"]}', headers=headers(data["root"]), json=values)
    assert updated.status_code == 200, updated.text
    access = await client.get("/api/subscription/access", headers=headers(owner), params={"organization_id": str(data["org"].id)})
    assert access.status_code == 200 and access.json()["data"]["organization_id"] == tenant["organization_id"], access.text
    snapshot = access.json()["data"]["package"]
    assert snapshot["price"] == "100.00" and snapshot["student_limit"] == 1
