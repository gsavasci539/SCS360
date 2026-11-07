"""School merchant ownership, encrypted account snapshots and safe configuration."""
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

from cryptography.fernet import Fernet
import pytest
from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.domain.entities.saas import OrganizationSubscription
from app.infrastructure.models.models import AuditLog, Permission, Role, User
from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401


@pytest.fixture
async def merchant_client(materials_client, monkeypatch):
    client, sessions, data = materials_client
    settings = get_settings()
    monkeypatch.setattr(settings, "SCHOOL_PAYMENT_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setattr(settings, "SCHOOL_PAYMENT_CALLBACK_URL", "https://api.test.invalid/api/payments/iyzico/callback")
    monkeypatch.setattr(settings, "SCHOOL_PAYMENT_PORTAL_URL", "https://portal.test.invalid")
    async with sessions() as db:
        staff = Role(name="Finance admin", slug="org_admin", organization_id=data["org"].id,
            permissions=[Permission(code=code, name=code, module=code.split('.')[0]) for code in ("finance.read", "finance.write", "settings.write")])
        finance = User(email="merchant-finance@test.invalid", password_hash="unused", first_name="Finance", last_name="Admin", organization_id=data["org"].id, roles=[staff])
        false_owner = User(email="merchant-role-owner@test.invalid", password_hash="unused", first_name="Role", last_name="Owner", organization_id=data["org"].id,
            roles=[Role(name="Role owner", slug="owner", organization_id=data["org"].id)])
        other_owner = User(email="merchant-other-owner@test.invalid", password_hash="unused", first_name="Other", last_name="Owner", organization_id=data["stranger"].organization_id)
        root = User(email="merchant-root@test.invalid", password_hash="unused", first_name="Platform", last_name="Admin", is_super_admin=True)
        db.add_all([finance, false_owner, other_owner, root]); await db.flush()
        now = datetime.now(UTC)
        for organization_id, owner_id in ((data["org"].id, data["user"].id), (data["stranger"].organization_id, other_owner.id)):
            db.add(OrganizationSubscription(organization_id=organization_id, owner_user_id=owner_id,
                admin_status="ACTIVE", period_start=now-timedelta(days=1), period_end=now+timedelta(days=30),
                package_snapshot={"branch_limit": 1000, "student_limit": 1000, "user_limit": 1000}))
        await db.commit()
    return client, sessions, {**data, "finance": finance, "false_owner": false_owner, "other_owner": other_owner, "root": root}


def body(**values):
    return {"request_id": str(uuid4()), "expected_revision": None, "enabled": True, "environment": "LIVE",
        "api_key": "acceptance-school-api-one", "secret_key": "acceptance-school-secret-one", **values}


async def configure(client, actor, values):
    return await client.put("/api/payments/merchant", headers=headers(actor), json=values)


async def test_merchant_owner_controls_secrets_while_finance_and_root_require_proper_context(merchant_client):
    client, sessions, data = merchant_client
    initial = await client.get("/api/payments/merchant", headers=headers(data["user"]))
    assert initial.status_code == 200, initial.text
    assert initial.json()["data"]["can_manage"] is True and initial.json()["data"]["revision"] is None
    saved = await configure(client, data["user"], body())
    assert saved.status_code == 200, saved.text
    result = saved.json()["data"]
    assert result["available"] is True and result["configured"] is True and result["has_secret_key"] is True
    assert len(result["revision"]) == 64
    for actor in (data["finance"], data["false_owner"], data["teacher"], data["root"]):
        denied = await configure(client, actor, body())
        assert denied.status_code == 403, denied.text
    minimal = await client.get("/api/payments/merchant", headers=headers(data["finance"]))
    assert minimal.status_code == 200 and minimal.json()["data"] == {"can_manage": False, "available": True}, minimal.text
    scoped = {**headers(data["root"]), "X-SCS360-Organization-Id": str(data["org"].id)}
    viewed = await client.get("/api/payments/merchant", headers=scoped)
    assert viewed.status_code == 200 and viewed.json()["data"]["can_manage"] is True, viewed.text
    async with sessions() as db:
        from app.infrastructure.models.models import SchoolPaymentMerchant
        row = (await db.execute(select(SchoolPaymentMerchant))).scalar_one()
        logs = (await db.execute(select(AuditLog).where(AuditLog.entity_type == "school_payment_merchant"))).scalars().all()
        assert "acceptance-school" not in row.credentials_ciphertext
        assert all("acceptance-school" not in str(log.new_values) for log in logs)
    assert "acceptance-school" not in saved.text and "acceptance-school" not in viewed.text


async def test_merchant_nonce_and_revision_prevent_replacement_or_rotation_replays(merchant_client):
    client, sessions, data = merchant_client
    request = body()
    first = await configure(client, data["user"], request)
    assert first.status_code == 200, first.text
    repeat = await configure(client, data["user"], request)
    assert repeat.status_code == 200 and repeat.json()["data"] == first.json()["data"], repeat.text
    collision = await configure(client, data["user"], {**request, "secret_key": "different-secret"})
    assert collision.status_code == 409, collision.text
    stale = await configure(client, data["user"], body(expected_revision="0"*64))
    assert stale.status_code == 409, stale.text
    bad_environment = await configure(client, data["user"], body(expected_revision=first.json()["data"]["revision"], environment="SANDBOX"))
    assert bad_environment.status_code == 409, bad_environment.text
    async with sessions() as db:
        from app.infrastructure.models.models import SchoolPaymentMerchant
        assert await db.scalar(select(func.count(SchoolPaymentMerchant.id))) == 1
        assert await db.scalar(select(func.count(AuditLog.id)).where(AuditLog.entity_type == "school_payment_merchant")) == 1


async def test_school_key_rotation_and_disable_preserve_checkout_snapshot_and_other_school(merchant_client):
    from app.application.services.school_payment_merchant import resolve_gateway
    client, sessions, data = merchant_client
    first = await configure(client, data["user"], body())
    assert first.status_code == 200, first.text
    async with sessions() as db:
        context = await resolve_gateway(db, data["org"].id)
    original = SimpleNamespace(organization_id=data["org"].id, merchant_account_id=context["merchant_account_id"], merchant_scope=context["merchant_scope"], merchant_snapshot=context["merchant_snapshot"])
    rotated = await configure(client, data["user"], body(expected_revision=first.json()["data"]["revision"], secret_key="rotated-acceptance-school-secret"))
    assert rotated.status_code == 200 and rotated.json()["data"]["account_id"] == first.json()["data"]["account_id"], rotated.text
    other = await configure(client, data["other_owner"], body(api_key="other-school-api", secret_key="other-school-secret"))
    assert other.status_code == 200 and other.json()["data"]["account_id"] != first.json()["data"]["account_id"], other.text
    disabled = await configure(client, data["user"], body(expected_revision=rotated.json()["data"]["revision"], enabled=False, api_key="", secret_key=""))
    assert disabled.status_code == 200 and disabled.json()["data"]["available"] is False, disabled.text
    async with sessions() as db:
        old = await resolve_gateway(db, data["org"].id, original)
        assert old["gateway"].settings.IYZICO_SECRET_KEY == "acceptance-school-secret-one"
        assert old["merchant_scope"] == context["merchant_scope"]
        with pytest.raises(AppException): await resolve_gateway(db, data["org"].id)
        second = await resolve_gateway(db, data["stranger"].organization_id)
        assert second["gateway"].settings.IYZICO_SECRET_KEY == "other-school-secret"
