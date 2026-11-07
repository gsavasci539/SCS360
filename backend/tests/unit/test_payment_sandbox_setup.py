import importlib.util
from pathlib import Path
from uuid import uuid4

from cryptography.fernet import Fernet
import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "configure_payment_sandbox.py"
spec = importlib.util.spec_from_file_location("acceptance_sandbox_setup", SCRIPT)
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    for field in ("APP_ENV", "SAAS_PAYMENT_ENABLED", "SAAS_IYZICO_BASE_URL", "SAAS_IYZICO_CALLBACK_URL",
            "SAAS_PORTAL_URL", "SAAS_CHECKOUT_ENCRYPTION_KEY", "IYZICO_BASE_URL", "IYZICO_CALLBACK_URL",
            "IYZICO_ORGANIZATION_ID", "IYZICO_PAYMENT_ENABLED"):
        monkeypatch.delenv(field, raising=False)


def test_missing_account_can_prepare_without_guessing_or_enabling_and_preserves_original_bytes(tmp_path):
    original = b'\xef\xbb\xbf# Existing settings\r\nAPP_ENV=development\r\nJWT_SECRET_KEY="keep $literal value" # keep comment\r\n'
    updated, result = setup.prepare(original, "saas", callback_url="https://callback.invalid/api/subscription/iyzico/callback",
        portal_url="http://127.0.0.1:5173")
    assert updated.startswith(original)
    assert b"SAAS_PAYMENT_ENABLED=false\r\n" in updated
    assert result["configuration"]["state"] == "needs_configuration" and not result["configuration"]["available"]
    assert "SAAS_IYZICO_API_KEY" in result["configuration"]["missing_fields"]
    path = tmp_path / ".env"
    path.write_bytes(original)
    assert setup.write_environment(path, original, updated)
    assert path.read_bytes() == updated
    backups = list(tmp_path.glob(".env.sandbox-backup-*"))
    assert len(backups) == 1 and backups[0].read_bytes() == original


def test_existing_cipher_credentials_comments_and_uuid_are_not_rotated():
    key = Fernet.generate_key().decode()
    original = (f'APP_ENV=test\nSAAS_CHECKOUT_ENCRYPTION_KEY="{key}" # retain\n'
        'SAAS_IYZICO_API_KEY="my-original-key" # unchanged\nSAAS_IYZICO_SECRET_KEY=original-secret\n').encode()
    updated, result = setup.prepare(original, "saas", callback_url="https://callback.invalid/api/subscription/iyzico/callback",
        portal_url="https://portal.invalid", activate=True)
    assert updated.startswith(original)
    assert "SAAS_CHECKOUT_ENCRYPTION_KEY" not in result["changed_fields"]
    assert key not in str(result) and "original-secret" not in str(result)
    assert result["configuration"]["available"] is True


def test_school_requires_explicit_valid_binding_and_never_reuses_saas_credentials():
    original = b"APP_ENV=development\nSAAS_IYZICO_API_KEY=platform-key\nSAAS_IYZICO_SECRET_KEY=platform-secret\n"
    with pytest.raises(setup.SetupError, match="UUID"):
        setup.prepare(original, "school")
    with pytest.raises(setup.SetupError, match="UUID"):
        setup.prepare(original, "school", organization_id="not-a-uuid")
    school = str(uuid4())
    updated, result = setup.prepare(original, "school", organization_id=school,
        callback_url="http://127.0.0.1:8000/api/payments/iyzico/callback")
    assert result["configuration"]["organization_id"] == school
    assert b"\nIYZICO_API_KEY=" not in updated and b"\nIYZICO_SECRET_KEY=" not in updated
    assert not result["configuration"]["available"]


@pytest.mark.parametrize("environment", ["production", "staging", "unexpected"])
def test_setup_never_switches_deployed_or_unknown_environment(environment):
    with pytest.raises(setup.SetupError, match="development/test"):
        setup.prepare(f"APP_ENV={environment}\n".encode(), "saas")


def test_explicit_activation_refuses_missing_credentials():
    with pytest.raises(setup.SetupError, match="eksik alanlar"):
        setup.prepare(b"APP_ENV=development\n", "saas", callback_url="https://callback.invalid/api/subscription/iyzico/callback",
            portal_url="http://127.0.0.1:5173", activate=True)


def test_existing_live_host_invalid_cipher_and_env_overrides_are_not_silently_changed(monkeypatch):
    with pytest.raises(setup.SetupError, match="BASE_URL"):
        setup.prepare(b"APP_ENV=development\nSAAS_IYZICO_BASE_URL=https://api.iyzipay.com\n", "saas")
    with pytest.raises(setup.SetupError, match="ENCRYPTION_KEY"):
        setup.prepare(b"APP_ENV=development\nSAAS_CHECKOUT_ENCRYPTION_KEY=broken\n", "saas")
    monkeypatch.setenv("SAAS_IYZICO_BASE_URL", "https://api.iyzipay.com")
    with pytest.raises(setup.SetupError, match="BASE_URL"):
        setup.prepare(b"APP_ENV=development\n", "saas")


def test_duplicate_target_lines_and_concurrent_changes_refuse_write(tmp_path):
    original = b"APP_ENV=development\nSAAS_IYZICO_CALLBACK_URL=\nSAAS_IYZICO_CALLBACK_URL=\n"
    with pytest.raises(setup.SetupError, match="birden"):
        setup.prepare(original, "saas", callback_url="https://callback.invalid/api/subscription/iyzico/callback")
    path = tmp_path / ".env"
    path.write_bytes(b"changed concurrently")
    with pytest.raises(setup.SetupError, match="değişti"):
        setup.write_environment(path, original, original + b"new")
    assert path.read_bytes() == b"changed concurrently"


def test_argument_errors_do_not_echo_accidentally_supplied_secrets(capsys):
    parser = setup.SafeParser(allow_abbrev=False)
    with pytest.raises(SystemExit):
        parser.parse_args(["--api-key", "never-log-this-private-key"])
    captured = capsys.readouterr()
    assert "never-log-this-private-key" not in captured.err + captured.out
    assert "Geçersiz seçenek" in captured.err
