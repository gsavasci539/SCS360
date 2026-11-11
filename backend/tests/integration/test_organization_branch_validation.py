from uuid import uuid4
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from test_saas_platform import platform_client  # noqa: F401
from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.infrastructure.models.models import Branch, Organization, Permission, Role, Student, User


def scoped(data):
    return {**headers(data["root"]), "X-SCS360-Organization-Id": str(data["org"].id)}


async def test_organization_mandatory_fields_and_storage_limits_reject_invalid_writes_without_changing_rows(platform_client):
    client, sessions, data = platform_client; auth = scoped(data); path = f'/api/organizations/{data["org"].id}'
    for field, value in [("name", None), ("name", " "), ("name", "x" * 256), ("is_active", None),
            ("country", None), ("country", " "), ("country", "x" * 101), ("tax_office", "x" * 101), ("legal_name", "x" * 256), ("tax_number", "x" * 51), ("phone", "x" * 21), ("email", "x" * 256), ("city", "x" * 101)]:
        response = await client.put(path, headers=auth, json={field: value})
        assert response.status_code == 422, (field, response.text)
    result = await client.get(path, headers=auth)
    assert result.status_code == 200 and result.json()["data"]["name"] == "Acceptance"
    assert result.json()["data"]["is_active"] is True
    assert (await client.put(path, headers=auth, json={"phone": "05320000000"})).status_code == 200
    cleared = await client.put(path, headers=auth, json={"phone": "  "})
    assert cleared.status_code == 200 and cleared.json()["data"]["phone"] is None


async def test_branch_uuid_required_fields_and_storage_limits_are_validated(platform_client):
    client, sessions, data = platform_client; auth = scoped(data); path = f'/api/branches/{data["branch"].id}'
    for field, value in [("name", None), ("name", " "), ("name", "x" * 256), ("is_active", None), ("capacity", None),
            ("capacity", -1), ("capacity", 2147483648), ("code", "x" * 51), ("phone", "x" * 21), ("email", "x" * 256), ("city", "x" * 101)]:
        response = await client.put(path, headers=auth, json={field: value})
        assert response.status_code == 422, (field, response.text)
    response = await client.post("/api/branches", headers=auth, json={"organization_id": "not-uuid", "name": "Invalid branch"})
    assert response.status_code == 422, response.text
    assert (await client.get(path, headers=auth)).json()["data"]["name"] == "School"
    valid = await client.put(path, headers=auth, json={"code": "  ", "phone": None, "capacity": 0, "is_active": False})
    assert valid.status_code == 200 and valid.json()["data"]["code"] is None and valid.json()["data"]["is_active"] is False


async def test_duplicate_names_codes_and_unknown_organization_have_controlled_responses(platform_client):
    client, sessions, data = platform_client; auth = scoped(data)
    organization = await client.post("/api/organizations", headers=headers(data["root"]), json={"name": "Acceptance"})
    assert organization.status_code == 409, organization.text
    repeated = await client.post("/api/branches", headers=auth, json={"organization_id": str(data["org"].id), "name": "School"})
    assert repeated.status_code == 409, repeated.text
    created = await client.post("/api/branches", headers=auth, json={"organization_id": str(data["org"].id), "name": "Another branch", "code": "UNIQUE"})
    assert created.status_code == 200, created.text
    collision = await client.put(f'/api/branches/{data["branch"].id}', headers=auth, json={"code": "UNIQUE"})
    assert collision.status_code == 409, collision.text
    unknown_id = str(uuid4())
    unknown = await client.post("/api/branches", headers={**headers(data["root"]), "X-SCS360-Organization-Id": unknown_id},
        json={"organization_id": unknown_id, "name": "Orphan branch"})
    assert unknown.status_code == 404, unknown.text
    async with sessions() as db:
        assert (await db.get(Branch, data["branch"].id)).code is None
        assert (await db.execute(select(Branch.id).where(Branch.name == "Orphan branch"))).first() is None


async def test_owner_edits_institution_details_but_only_platform_controls_account_lifecycle(platform_client):
    client, sessions, data = platform_client
    async with sessions() as db:
        permissions = []
        for code in ("org.read", "org.write"):
            permissions.append(Permission(code=code, name=code, module="org"))
        role = Role(organization_id=data["org"].id, slug="owner", name="Owner", permissions=permissions)
        user = User(organization_id=data["org"].id, email="org-owner@test.invalid", first_name="Owner", last_name="Test", password_hash="unused", roles=[role])
        db.add(user); await db.commit()
    path = f'/api/organizations/{data["org"].id}'
    assert (await client.put(path, headers=headers(user), json={"phone": "05320000000"})).status_code == 200
    assert (await client.put(path, headers=headers(user), json={"is_active": False})).status_code == 403
    assert (await client.delete(path, headers=headers(user))).status_code == 403
    closed = await client.delete(path, headers=scoped(data))
    assert closed.status_code == 200, closed.text
    async with sessions() as db:
        row = await db.get(Organization, data["org"].id)
        assert row.deleted_at is None and row.is_active is False
    reopened = await client.put(path, headers=scoped(data), json={"is_active": True})
    assert reopened.status_code == 200, reopened.text


async def test_country_and_tax_office_persist_and_optional_field_clears(platform_client):
    client, sessions, data = platform_client
    path = f'/api/organizations/{data["org"].id}'
    saved = await client.put(path, headers=scoped(data), json={"country": "Türkiye", "tax_office": "Kadıköy"})
    assert saved.status_code == 200 and saved.json()["data"]["tax_office"] == "Kadıköy", saved.text
    read = (await client.get(path, headers=scoped(data))).json()["data"]
    assert read["country"] == "Türkiye" and read["tax_office"] == "Kadıköy"
    cleared = await client.put(path, headers=scoped(data), json={"tax_office": " "})
    assert cleared.status_code == 200 and cleared.json()["data"]["tax_office"] is None


async def test_branch_counts_real_roster_excludes_deleted_and_corrupt_cross_school_links(platform_client):
    client, sessions, data = platform_client; auth = scoped(data)
    path = f'/api/branches/{data["branch"].id}'
    read = await client.get(path, headers=auth)
    assert read.status_code == 200 and read.json()["data"]["student_count"] == 2, read.text
    async with sessions() as db:
        await db.execute(update(Student.__table__).where(Student.__table__.c.id == data["children"][0].id).values(deleted_at=datetime.now(UTC)))
        await db.execute(update(Student.__table__).where(Student.__table__.c.id == data["stranger"].id).values(branch_id=data["branch"].id))
        await db.commit()
    for response in [await client.get(path, headers=auth), await client.put(path, headers=auth, json={"phone": "05320000000"})]:
        assert response.status_code == 200 and response.json()["data"]["student_count"] == 1, response.text
    listed = await client.get("/api/branches", headers=auth)
    assert listed.status_code == 200 and listed.json()["data"]["items"][0]["student_count"] == 1, listed.text
    created = await client.post("/api/branches", headers=auth, json={"organization_id": str(data["org"].id), "name": "Empty branch"})
    assert created.status_code == 200 and created.json()["data"]["student_count"] == 0, created.text
