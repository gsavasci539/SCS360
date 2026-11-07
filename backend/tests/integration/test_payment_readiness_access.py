from types import SimpleNamespace

from cryptography.fernet import Fernet

from app.core.security import create_access_token
from app.infrastructure.models.models import User
from app.routers import platform
from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401


async def test_only_platform_root_can_read_safe_payment_setup_metadata(materials_client, monkeypatch):
    client, sessions, data = materials_client
    async with sessions() as db:
        root = User(email="payment-root@acceptance.invalid", password_hash="unused", first_name="Root", last_name="Test",
            organization_id=data["org"].id, is_super_admin=True)
        db.add(root); await db.commit()
    cipher = Fernet.generate_key().decode()
    source = SimpleNamespace(APP_ENV="development", SAAS_PAYMENT_ENABLED=True,
        SAAS_IYZICO_API_KEY="never-return-this-api-key", SAAS_IYZICO_SECRET_KEY="never-return-this-secret-key",
        SAAS_IYZICO_BASE_URL="https://sandbox-api.iyzipay.com", SAAS_IYZICO_CALLBACK_URL="https://callback.acceptance.invalid/api/subscription/iyzico/callback",
        SAAS_PORTAL_URL="https://portal.acceptance.invalid", SAAS_CHECKOUT_ENCRYPTION_KEY=cipher)
    monkeypatch.setattr(platform.service, "get_settings", lambda: source)
    denied_parent = await client.get("/api/platform/payment-readiness", headers=headers(data["user"]))
    denied_teacher = await client.get("/api/platform/payment-readiness", headers=headers(data["teacher"]))
    assert denied_parent.status_code == denied_teacher.status_code == 403
    allowed = await client.get("/api/platform/payment-readiness", headers={"Authorization": "Bearer " + create_access_token(root.id)})
    assert allowed.status_code == 200, allowed.text
    result = allowed.json()["data"]
    assert result["saas"]["state"] == "sandbox_configured" and result["saas"]["available"] is True
    assert result["school"]["state"] == "needs_configuration"
    assert result["provider_verified"] is False
    for secret in (source.SAAS_IYZICO_API_KEY, source.SAAS_IYZICO_SECRET_KEY, cipher,
            source.SAAS_IYZICO_CALLBACK_URL, source.SAAS_PORTAL_URL):
        assert secret not in allowed.text
