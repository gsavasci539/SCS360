import json
from uuid import uuid4

from cryptography.fernet import Fernet
import pytest

from app.application.services.payment_readiness import configuration, public_state, report


def settings(target="saas"):
    prefix = "SAAS_IYZICO_" if target == "saas" else "IYZICO_"
    return {"APP_ENV": "development", prefix + "BASE_URL": "https://sandbox-api.iyzipay.com",
        prefix + "API_KEY": "private-key-do-not-expose", prefix + "SECRET_KEY": "private-secret-do-not-expose",
        prefix + "CALLBACK_URL": "https://acceptance.invalid/api/subscription/iyzico/callback" if target == "saas" else "https://acceptance.invalid/api/payments/iyzico/callback",
        "SAAS_PAYMENT_ENABLED" if target == "saas" else "IYZICO_PAYMENT_ENABLED": True,
        "SAAS_PORTAL_URL": "https://portal.acceptance.invalid", "SAAS_CHECKOUT_ENCRYPTION_KEY": Fernet.generate_key().decode(),
        "IYZICO_ORGANIZATION_ID": str(uuid4())}


def test_missing_settings_report_names_only_and_do_not_claim_provider_verification():
    result = report({"APP_ENV": "development"})
    assert result["saas"]["state"] == "needs_configuration"
    assert "SAAS_IYZICO_API_KEY" in result["saas"]["missing_fields"]
    assert "IYZICO_ORGANIZATION_ID" in result["school"]["missing_fields"]
    assert result["provider_verified"] is False
    assert result["saas"]["available"] is False


@pytest.mark.parametrize("target", ["saas", "school"])
def test_configured_sandbox_is_enabled_only_by_flag_and_exposes_no_secret(target):
    source = settings(target)
    result = configuration(source, target)
    assert result["state"] == "sandbox_configured" and result["available"] is True
    assert result["provider_verified"] is False
    encoded = json.dumps(result)
    assert "private-key-do-not-expose" not in encoded and "private-secret-do-not-expose" not in encoded
    assert source["SAAS_CHECKOUT_ENCRYPTION_KEY"] not in encoded
    source[result["activation_field"]] = False
    assert configuration(source, target)["available"] is False
    assert public_state(source, target) == {"available": False, "mode": None, "provider_verified": False}


@pytest.mark.parametrize("environment", ["production", "staging"])
@pytest.mark.parametrize("target", ["saas", "school"])
def test_sandbox_cannot_be_ready_in_deployed_environments(environment, target):
    source = {**settings(target), "APP_ENV": environment}
    result = configuration(source, target)
    assert result["state"] == "blocked_environment"
    assert result["configured"] is False and result["available"] is False


@pytest.mark.parametrize("field,bad", [
    ("SAAS_IYZICO_CALLBACK_URL", "https://acceptance.invalid/incorrect"),
    ("SAAS_IYZICO_CALLBACK_URL", "https://user:secret@acceptance.invalid/api/subscription/iyzico/callback"),
    ("SAAS_PORTAL_URL", "https://acceptance.invalid/path"),
    ("SAAS_CHECKOUT_ENCRYPTION_KEY", "not-fernet"),
    ("SAAS_IYZICO_BASE_URL", "https://sandbox-api.iyzipay.com.attacker.invalid"),
])
def test_invalid_settings_have_safe_explicit_field_names(field, bad):
    result = configuration({**settings(), field: bad}, "saas")
    assert result["available"] is False and field in result["invalid_fields"]
    assert bad not in json.dumps(result)


def test_local_callback_is_distinguished_from_external_provider_acceptance():
    source = {**settings(), "SAAS_IYZICO_CALLBACK_URL": "http://127.0.0.1:8000/api/subscription/iyzico/callback",
        "SAAS_PORTAL_URL": "http://127.0.0.1:5173"}
    result = configuration(source, "saas")
    assert result["available"] is True
    assert "PUBLIC_HTTPS_CALLBACK_REQUIRED_FOR_PROVIDER_ACCEPTANCE" in result["warnings"]
    assert result["provider_verified"] is False
