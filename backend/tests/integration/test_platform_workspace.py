from uuid import UUID
from sqlalchemy import select

from test_saas_platform import platform_client, plan_and_tenant  # noqa: F401
from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.infrastructure.models.models import User, Student


async def test_platform_workspace_is_server_scoped_and_never_reassigns_the_operator(platform_client):
    client, sessions, data = platform_client
    plan, tenant, body = await plan_and_tenant(client, data)
    org = tenant["organization_id"]; root = headers(data["root"])
    scoped = {**root, "X-SCS360-Organization-Id": org}
    selected = await client.get(f"/api/platform/tenants/{org}/workspace", headers=root)
    assert selected.status_code == 200 and selected.json()["data"]["id"] == org, selected.text
    branch = await client.post("/api/branches", headers=scoped, json={"organization_id": org, "name": "Selected School Branch"})
    assert branch.status_code == 200, branch.text
    student = await client.post("/api/students", headers=scoped, json={"organization_id": org, "branch_id": branch.json()["data"]["id"], "first_name": "Scoped", "last_name": "Child"})
    assert student.status_code == 200, student.text
    listing = await client.get("/api/students", headers=scoped)
    assert listing.status_code == 200, listing.text
    assert [row["id"] for row in listing.json()["data"]["items"]] == [student.json()["data"]["id"]]
    other = await client.get(f'/api/students/{data["children"][0].id}', headers=scoped)
    assert other.status_code in {403, 404}, other.text
    account = await client.post("/api/users", headers=scoped, json={"email": "scoped-staff@example.com", "password": "AcceptancePass1!", "first_name": "Scoped", "last_name": "Staff"})
    assert account.status_code == 200 and account.json()["data"]["organization_id"] == org, account.text
    denied = await client.post("/api/branches", headers=scoped, json={"organization_id": str(data["org"].id), "name": "Wrong school"})
    assert denied.status_code in {403, 404}, denied.text
    async with sessions() as db:
        operator = await db.get(User, data["root"].id)
        assert operator.organization_id == data["root"].organization_id and operator.is_super_admin
        stored = await db.get(Student, UUID(student.json()["data"]["id"]))
        assert stored.created_by == data["root"].id
    me = await client.get("/api/auth/me", headers=scoped)
    assert me.status_code == 200 and me.json()["data"]["is_super_admin"] is True, me.text


async def test_school_owner_cannot_spoof_a_platform_workspace(platform_client):
    client, sessions, data = platform_client
    denied = await client.get("/api/students", headers={**headers(data["teacher"]), "X-SCS360-Organization-Id": str(data["org"].id)})
    assert denied.status_code == 403, denied.text
    invalid = await client.get("/api/students", headers={**headers(data["root"]), "X-SCS360-Organization-Id": "invalid"})
    assert invalid.status_code == 422, invalid.text


async def test_platform_operator_must_select_school_before_any_school_reads_or_writes(platform_client):
    client, sessions, data = platform_client
    root = headers(data["root"])
    child = str(data["children"][0].id)
    requests = [("GET", "/api/students", None), ("GET", "/api/users", None),
        ("POST", "/api/students", {"organization_id": str(data["org"].id), "branch_id": str(data["branch"].id), "first_name": "Unscoped", "last_name": "Forbidden"}),
        ("PUT", f"/api/students/{child}", {"first_name": "Forbidden"}),
        ("DELETE", f"/api/students/{child}", None)]
    for method, path, payload in requests:
        result = await client.request(method, path, headers=root, **({"json": payload} if payload else {}))
        assert result.status_code == 403, (method, path, result.text)
    assert (await client.get("/api/platform/summary", headers=root)).status_code == 200
    assert (await client.get("/api/auth/me", headers=root)).status_code == 200
    async with sessions() as db:
        stored = await db.get(Student, data["children"][0].id)
        assert stored.first_name == data["children"][0].first_name and stored.deleted_at is None
