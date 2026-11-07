import pytest
from sqlalchemy import select

from app.application.services import school_payment_merchant as merchants
from app.core.config import get_settings
from app.core.exceptions import AppException
from app.infrastructure.models.models import SchoolPaymentMerchant
from test_school_payment_merchants import merchant_client, body, configure  # noqa: F401
from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401


async def test_invalid_encrypted_credential_types_are_unknown_and_never_reach_provider(merchant_client):
    client, sessions, data = merchant_client
    assert (await configure(client, data["user"], body())).status_code == 200
    async with sessions() as db:
        row = (await db.execute(select(SchoolPaymentMerchant))).scalar_one()
        row.credentials_ciphertext = merchants.seal_school_secret({"api_key": 123, "secret_key": "private-invalid-credential"})
        await db.commit()
    status = await client.get("/api/payments/merchant", headers=headers(data["user"]))
    assert status.status_code == 200, status.text
    assert status.json()["data"]["available"] is False and status.json()["data"]["configured"] is False
    assert "private-invalid-credential" not in status.text
    async with sessions() as db:
        with pytest.raises(AppException) as caught:
            await merchants.resolve_gateway(db, data["org"].id)
        assert caught.value.status_code == 503


async def test_live_always_requires_https_while_development_sandbox_can_use_loopback(merchant_client, monkeypatch):
    client, _, data = merchant_client
    settings = get_settings()
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "SCHOOL_PAYMENT_CALLBACK_URL", "http://127.0.0.1:8000/api/payments/iyzico/callback")
    monkeypatch.setattr(settings, "SCHOOL_PAYMENT_PORTAL_URL", "http://127.0.0.1:5173")
    live = await configure(client, data["user"], body())
    assert live.status_code == 503, live.text
    sandbox = await configure(client, data["user"], body(environment="SANDBOX"))
    assert sandbox.status_code == 200 and sandbox.json()["data"]["available"] is True, sandbox.text
    too_long = await configure(client, data["user"], body(secret_key="DO-NOT-ECHO-SECRET"*200))
    assert too_long.status_code == 422 and "DO-NOT-ECHO-SECRET" not in too_long.text
