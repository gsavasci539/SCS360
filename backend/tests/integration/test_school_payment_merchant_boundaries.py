import asyncio
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from app.application.services import school_payment_merchant as merchants
from app.core.config import get_settings
from app.core.exceptions import AppException
from app.domain.entities.saas import OrganizationSubscription
from app.infrastructure.models.models import AuditLog, SchoolPaymentMerchant
from test_school_payment_merchants import merchant_client, body, configure  # noqa: F401
from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401


async def test_explicit_account_replacement_archives_previous_account_and_snapshot(merchant_client):
    client, sessions, data = merchant_client
    first = await configure(client, data["user"], body())
    assert first.status_code == 200, first.text
    async with sessions() as db:
        original = await merchants.resolve_gateway(db, data["org"].id)
    checkout = SimpleNamespace(organization_id=data["org"].id, merchant_account_id=original["merchant_account_id"],
        merchant_scope=original["merchant_scope"], merchant_snapshot=original["merchant_snapshot"])
    replaced = await configure(client, data["user"], body(expected_revision=first.json()["data"]["revision"], environment="SANDBOX", replace_account=True,
        api_key="replacement-school-api", secret_key="replacement-school-secret"))
    assert replaced.status_code == 200 and replaced.json()["data"]["account_id"] != first.json()["data"]["account_id"], replaced.text
    async with sessions() as db:
        rows = (await db.execute(select(SchoolPaymentMerchant))).scalars().all()
        assert len(rows) == 2 and sum(row.is_current for row in rows) == 1
        old = await merchants.resolve_gateway(db, data["org"].id, checkout)
        new = await merchants.resolve_gateway(db, data["org"].id)
        assert old["gateway"].settings.IYZICO_BASE_URL == "https://api.iyzipay.com"
        assert new["gateway"].settings.IYZICO_BASE_URL == "https://sandbox-api.iyzipay.com"
        assert old["gateway"].settings.IYZICO_SECRET_KEY == "acceptance-school-secret-one"
        assert old["merchant_scope"] != new["merchant_scope"]


async def test_configured_owner_reference_takes_precedence_over_legacy_owner_role(merchant_client):
    client, sessions, data = merchant_client
    assert (await configure(client, data["false_owner"], body())).status_code == 403
    async with sessions() as db:
        row = await db.get(OrganizationSubscription, data["org"].id)
        row.owner_user_id = None
        await db.commit()
    assert (await configure(client, data["finance"], body())).status_code == 403
    allowed = await configure(client, data["false_owner"], body())
    assert allowed.status_code == 200, allowed.text


@pytest.mark.parametrize("field", ["SCHOOL_PAYMENT_ENCRYPTION_KEY", "SCHOOL_PAYMENT_CALLBACK_URL", "SCHOOL_PAYMENT_PORTAL_URL"])
async def test_incomplete_server_configuration_never_enables_school_merchant(merchant_client, monkeypatch, field):
    client, sessions, data = merchant_client
    monkeypatch.setattr(get_settings(), field, "")
    rejected = await configure(client, data["user"], body())
    assert rejected.status_code == 503, rejected.text
    assert "acceptance-school" not in rejected.text
    async with sessions() as db:
        assert await db.scalar(select(func.count(SchoolPaymentMerchant.id))) == 0
        assert await db.scalar(select(func.count(AuditLog.id)).where(AuditLog.entity_type == "school_payment_merchant")) == 0


async def test_disabling_still_works_when_encryption_key_is_unavailable(merchant_client, monkeypatch):
    client, sessions, data = merchant_client
    saved = await configure(client, data["user"], body())
    assert saved.status_code == 200, saved.text
    async with sessions() as db:
        original = (await db.execute(select(SchoolPaymentMerchant))).scalar_one().credentials_ciphertext
    monkeypatch.setattr(get_settings(), "SCHOOL_PAYMENT_ENCRYPTION_KEY", "")
    stopped = await configure(client, data["user"], body(expected_revision=saved.json()["data"]["revision"], enabled=False, api_key=None, secret_key=None))
    assert stopped.status_code == 200 and stopped.json()["data"]["enabled"] is False, stopped.text
    async with sessions() as db:
        assert (await db.execute(select(SchoolPaymentMerchant))).scalar_one().credentials_ciphertext == original


async def test_production_rejects_sandbox_configuration_and_accepts_live_without_network(merchant_client, monkeypatch):
    client, _, data = merchant_client
    monkeypatch.setattr(get_settings(), "APP_ENV", "production")
    rejected = await configure(client, data["user"], body(environment="SANDBOX"))
    assert rejected.status_code == 422, rejected.text
    live = await configure(client, data["user"], body())
    assert live.status_code == 200 and live.json()["data"]["available"] is True, live.text


async def test_pending_snapshot_rejects_other_school_or_account_metadata(merchant_client):
    client, sessions, data = merchant_client
    assert (await configure(client, data["user"], body())).status_code == 200
    async with sessions() as db:
        context = await merchants.resolve_gateway(db, data["org"].id)
        values = merchants.open_school_secret(context["merchant_snapshot"])
        for changed in ({"organization_id": str(data["stranger"].organization_id)}, {"merchant_account_id": str(uuid4())}, {"merchant_scope": "school:"+str(uuid4())}):
            checkout = SimpleNamespace(organization_id=data["org"].id, merchant_account_id=context["merchant_account_id"],
                merchant_scope=context["merchant_scope"], merchant_snapshot=merchants.seal_school_secret({**values, **changed}))
            with pytest.raises(AppException):
                await merchants.resolve_gateway(db, data["org"].id, checkout)


async def test_concurrent_same_configuration_nonce_creates_one_account_and_audit(merchant_client):
    client, sessions, data = merchant_client
    request = body()
    replies = await asyncio.gather(*[configure(client, data["user"], request) for _ in range(2)])
    assert all(reply.status_code == 200 for reply in replies), [reply.text for reply in replies]
    assert replies[0].json()["data"] == replies[1].json()["data"]
    async with sessions() as db:
        assert await db.scalar(select(func.count(SchoolPaymentMerchant.id))) == 1
        assert await db.scalar(select(func.count(AuditLog.id)).where(AuditLog.entity_type == "school_payment_merchant")) == 1


async def test_disabled_school_record_blocks_legacy_fallback_but_not_old_callback(merchant_client, monkeypatch):
    from app.application.services import online_payment_service
    client, sessions, data = merchant_client
    gateway_class = online_payment_service.IyzicoGateway
    settings = SimpleNamespace(APP_ENV="development", IYZICO_API_KEY="legacy-test-api", IYZICO_SECRET_KEY="legacy-test-secret",
        IYZICO_BASE_URL="https://sandbox-api.iyzipay.com", IYZICO_CALLBACK_URL="https://api.test.invalid/api/payments/iyzico/callback",
        IYZICO_ORGANIZATION_ID=str(data["org"].id), IYZICO_PAYMENT_ENABLED=True)
    monkeypatch.setattr(online_payment_service, "IyzicoGateway", lambda: gateway_class(settings))
    async with sessions() as db:
        legacy = await merchants.resolve_gateway(db, data["org"].id)
        assert legacy["merchant_snapshot"] is None and legacy["merchant_account_id"] is None
        with pytest.raises(AppException): await merchants.resolve_gateway(db, data["stranger"].organization_id)
    disabled = await configure(client, data["user"], body(enabled=False, api_key=None, secret_key=None))
    assert disabled.status_code == 200, disabled.text
    async with sessions() as db:
        with pytest.raises(AppException): await merchants.resolve_gateway(db, data["org"].id)
        old = SimpleNamespace(organization_id=data["org"].id, merchant_account_id=None,
            merchant_scope="legacy:"+str(data["org"].id), merchant_snapshot=None)
        callback = await merchants.resolve_gateway(db, data["org"].id, old)
        assert callback["gateway"].settings.IYZICO_SECRET_KEY == "legacy-test-secret"
