import asyncio
from uuid import UUID

from sqlalchemy import select

from test_saas_platform import platform_client  # noqa: F401
from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.infrastructure.models.models import Parent, StudentParent, User


async def test_parent_account_link_is_explicit_scoped_and_atomic(platform_client):
    client, sessions, data = platform_client
    root = {**headers(data["root"]), "X-SCS360-Organization-Id": str(data["org"].id)}
    contacts = []
    for name in ["Birinci", "Ikinci"]:
        response = await client.post("/api/parents", headers=root, json={"organization_id": str(data["org"].id), "first_name": name, "last_name": "Veli"})
        assert response.status_code == 200, response.text
        contacts.append(response.json()["data"]["id"])
    async with sessions() as db:
        original = (await db.execute(select(Parent).where(Parent.user_id == data["user"].id))).scalar_one()
        original_id = original.id
        for index, contact in enumerate(contacts):
            db.add(StudentParent(student_id=data["children"][index].id, parent_id=UUID(contact)))
        await db.commit()
    path = f"/api/parents/{contacts[0]}/account"
    assert (await client.put(path, headers=headers(data["teacher"]), json={"user_id": str(data["user"].id)})).status_code == 403
    assert (await client.put(path, headers=root, json={"user_id": str(data["root"].id)})).status_code == 409
    assert (await client.put(path, headers=root, json={"user_id": str(data["user"].id)})).status_code == 409
    options = await client.get(f"/api/parents/{contacts[0]}/account-options", headers=root)
    assert options.status_code == 200 and str(data["user"].id) not in options.text
    assert (await client.put(f"/api/parents/{original_id}/account", headers=root, json={"user_id": None})).status_code == 200
    rows = await asyncio.gather(*[client.put(f"/api/parents/{contact}/account", headers=root, json={"user_id": str(data["user"].id)}) for contact in contacts])
    assert sorted(row.status_code for row in rows) == [200, 409], [row.text for row in rows]
    winner = next(index for index, row in enumerate(rows) if row.status_code == 200)
    children = await client.get("/api/parent/my-children", headers=headers(data["user"]))
    assert children.status_code == 200, children.text
    assert [row["student_id"] for row in children.json()["data"]] == [str(data["children"][winner].id)]
    async with sessions() as db:
        operator = await db.get(User, data["root"].id)
        assert operator.organization_id is None and operator.is_super_admin is True
