import asyncio
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from test_subscription_billing import prepare  # noqa: F401
from test_saas_platform import platform_client  # noqa: F401
from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.core.role_catalog import ROLE_NAMES
from app.infrastructure.models.models import Role


async def test_new_school_gets_complete_roles_and_legacy_repair_preserves_customization(platform_client):
    client, sessions, data = await prepare(platform_client)
    organization = UUID(data["tenant"]["organization_id"])
    async with sessions() as db:
        roles = (await db.execute(select(Role).where(Role.organization_id == organization).options(selectinload(Role.permissions)))).scalars().all()
        assert {row.slug for row in roles} == set(ROLE_NAMES)
        parent = next(row for row in roles if row.slug == "parent")
        assert "parent.make_payment" in {permission.code for permission in parent.permissions}
        assert "finance.write" not in {permission.code for permission in parent.permissions}
        parent.name = "Kurumun özel veli rolü"; parent.permissions = []
        parent_id = parent.id
        teacher = next(row for row in roles if row.slug == "teacher"); teacher.deleted_at = datetime.now(UTC)
        await db.commit()
    body = {"organization_id": str(organization)}
    responses = await asyncio.gather(*[client.post("/api/users/role-catalog", headers=headers(data["owner"]), json=body) for _ in range(2)])
    assert all(row.status_code == 200 for row in responses), [row.text for row in responses]
    assert sorted(row.json()["data"]["created_count"] for row in responses) == [0, 1]
    assert (await client.post("/api/users/role-catalog", headers=headers(data["owner"]), json={"organization_id": str(data["org"].id)})).status_code == 403
    assert (await client.post("/api/users/role-catalog", headers=headers(data["teacher"]), json=body)).status_code == 403
    async with sessions() as db:
        old = (await db.execute(select(Role).where(Role.id == parent_id).options(selectinload(Role.permissions)))).scalar_one()
        assert old.name == "Kurumun özel veli rolü" and old.permissions == []
        active = (await db.execute(select(Role).where(Role.organization_id == organization, Role.deleted_at.is_(None)))).scalars().all()
        assert len(active) == len(ROLE_NAMES)
