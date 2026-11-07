from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.application.services.school_checkout_service import actions
from app.core.tenant import TenantContext
from app.core.config import get_settings
from app.infrastructure.models.models import Parent, Permission, Role, StudentParent
from test_school_checkout_durability import school_checkout_client, payment, start, callback  # noqa: F401
from test_school_payment_merchants import merchant_client  # noqa: F401
from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401


async def test_creator_losing_finance_write_has_no_actions_until_current_permission_is_restored(school_checkout_client):
    client, sessions, data, _provider = school_checkout_client
    request = payment(data)
    started = await client.post("/api/payments/iyzico/initialize", headers=headers(data["finance"]), json=request)
    assert started.status_code == 200, started.text
    identifier = request["request_id"]
    async with sessions() as db:
        role = (await db.execute(select(Role).options(selectinload(Role.permissions)).where(Role.slug == "org_admin", Role.organization_id == data["org"].id))).scalar_one()
        role.permissions = [permission for permission in role.permissions if permission.code != "finance.write"]
        await db.commit()
    metadata = await client.get(f"/api/payments/iyzico/checkouts/{identifier}", headers=headers(data["finance"]))
    assert metadata.status_code == 200, metadata.text
    assert metadata.json()["data"]["can_resume"] is False and metadata.json()["data"]["can_refresh"] is False
    assert "school-token-" not in metadata.text
    for action in ("resume", "refresh"):
        assert (await client.post(f"/api/payments/iyzico/checkouts/{identifier}/{action}", headers=headers(data["finance"]))).status_code == 403
    async with sessions() as db:
        role = (await db.execute(select(Role).options(selectinload(Role.permissions)).where(Role.slug == "org_admin", Role.organization_id == data["org"].id))).scalar_one()
        permission = (await db.execute(select(Permission).where(Permission.code == "finance.write"))).scalar_one()
        role.permissions.append(permission)
        await db.commit()
    restored = await client.post(f"/api/payments/iyzico/checkouts/{identifier}/resume", headers=headers(data["finance"]))
    assert restored.status_code == 200 and restored.json()["data"]["can_resume"] is True, restored.text


@pytest.mark.parametrize("parent_purpose,own,permissions,allowed", [
    (False, True, {"finance.read"}, False),
    (False, False, {"finance.write"}, True),
    (False, True, {"parent.make_payment"}, True),
    (False, False, {"parent.make_payment"}, False),
    (True, True, {"finance.write"}, False),
    (True, True, {"parent.make_payment"}, True),
    (True, False, {"finance.write", "parent.make_payment"}, False),
])
def test_checkout_action_capabilities_follow_current_route_permission_and_purpose(parent_purpose, own, permissions, allowed):
    actor = uuid4()
    tenant = TenantContext(user_id=actor, permissions=permissions, parent_portal=parent_purpose)
    row = SimpleNamespace(created_by=actor if own else uuid4())
    assert actions(tenant, row) is allowed


async def test_finance_read_plus_parent_payment_permission_requires_actual_guardian_child_for_actions(school_checkout_client):
    client, sessions, data, _provider = school_checkout_client
    request = payment(data)
    started = await client.post("/api/payments/iyzico/initialize", headers=headers(data["finance"]), json=request)
    assert started.status_code == 200, started.text
    identifier = request["request_id"]
    async with sessions() as db:
        role = (await db.execute(select(Role).options(selectinload(Role.permissions)).where(Role.slug == "org_admin", Role.organization_id == data["org"].id))).scalar_one()
        parent_payment = (await db.execute(select(Permission).where(Permission.code == "parent.make_payment"))).scalar_one()
        role.permissions = [permission for permission in role.permissions if permission.code != "finance.write"] + [parent_payment]
        await db.commit()
    metadata = await client.get(f"/api/payments/iyzico/checkouts/{identifier}", headers=headers(data["finance"]))
    assert metadata.status_code == 200, metadata.text
    assert metadata.json()["data"]["can_resume"] is False and metadata.json()["data"]["can_refresh"] is False
    for action in ("resume", "refresh"):
        refused = await client.post(f"/api/payments/iyzico/checkouts/{identifier}/{action}", headers=headers(data["finance"]))
        assert refused.status_code == 403, refused.text
    async with sessions() as db:
        contact = Parent(user_id=data["finance"].id, organization_id=data["org"].id, first_name="Finance", last_name="Guardian")
        db.add(contact); await db.flush()
        db.add(StudentParent(parent_id=contact.id, student_id=data["children"][0].id))
        await db.commit()
    own_child = await client.get(f"/api/payments/iyzico/checkouts/{identifier}", headers=headers(data["finance"]))
    assert own_child.status_code == 200 and own_child.json()["data"]["can_resume"] is True, own_child.text
    resumed = await client.post(f"/api/payments/iyzico/checkouts/{identifier}/resume", headers=headers(data["finance"]))
    assert resumed.status_code == 200 and resumed.json()["data"]["can_resume"] is True, resumed.text


async def test_completed_checkout_metadata_does_not_need_current_merchant_cipher(school_checkout_client, monkeypatch):
    client, _, data, provider = school_checkout_client
    request = payment(data)
    assert (await start(client, data, request)).status_code == 200
    captured = await callback(client, provider, request["request_id"])
    assert captured.status_code == 200, captured.text
    monkeypatch.setattr(get_settings(), "SCHOOL_PAYMENT_ENCRYPTION_KEY", "")
    metadata = await client.get(f'/api/parent/payments/checkouts/{request["request_id"]}', headers=headers(data["user"]))
    assert metadata.status_code == 200, metadata.text
    values = metadata.json()["data"]
    assert values["status"] == "COMPLETED" and values["payment_id"]
    assert values["can_resume"] is False and values["can_refresh"] is False
    assert "school-token-" not in metadata.text and "acceptance-school-secret" not in metadata.text
