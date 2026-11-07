"""Offline payment configuration checks. Never expose credentials or call a provider."""
from collections.abc import Mapping
from urllib.parse import urlparse
from uuid import UUID

from cryptography.fernet import Fernet


SANDBOX_URL = "https://sandbox-api.iyzipay.com"
LIVE_URL = "https://api.iyzipay.com"
TARGETS = ("saas", "school")


def value(source, name, default=""):
    result = source.get(name, default) if isinstance(source, Mapping) else getattr(source, name, default)
    return result if result is not None else default


def enabled(source, name):
    raw = value(source, name, False)
    return raw is True or (isinstance(raw, str) and raw.strip().lower() in {"true", "1", "yes", "on"})


def configuration(source, target):
    """Return field names/statuses only; no raw secrets, callback addresses or tokens."""
    if target not in TARGETS:
        raise ValueError("Unknown payment target")
    prefix = "SAAS_IYZICO_" if target == "saas" else "IYZICO_"
    flag = "SAAS_PAYMENT_ENABLED" if target == "saas" else "IYZICO_PAYMENT_ENABLED"
    required = [prefix + "API_KEY", prefix + "SECRET_KEY", prefix + "CALLBACK_URL"]
    required += ["SAAS_PORTAL_URL", "SAAS_CHECKOUT_ENCRYPTION_KEY"] if target == "saas" else ["IYZICO_ORGANIZATION_ID"]
    missing = [field for field in required if not str(value(source, field)).strip()]
    invalid, warnings = [], []
    environment = str(value(source, "APP_ENV", "development")).strip().lower()
    base = str(value(source, prefix + "BASE_URL", SANDBOX_URL)).rstrip("/")
    mode = "sandbox" if base == SANDBOX_URL else "live" if base == LIVE_URL else "unknown"
    if mode == "unknown":
        invalid.append(prefix + "BASE_URL")
    blocked = environment in {"production", "staging"} and mode == "sandbox"
    if blocked:
        warnings.append("SANDBOX_BLOCKED_IN_DEPLOYED_ENVIRONMENT")

    def address(field, path, *, portal=False):
        raw = str(value(source, field))
        if not raw:
            return
        try:
            parsed = urlparse(raw)
            _ = parsed.port
            local = environment in {"development", "test"} and parsed.hostname in {"localhost", "127.0.0.1"}
            valid_scheme = parsed.scheme == "https" or (local and parsed.scheme == "http")
            valid_path = parsed.path in {"", "/"} if portal else parsed.path == path
            good = valid_scheme and parsed.hostname and valid_path and not any((parsed.username, parsed.password, parsed.query, parsed.fragment))
            good = good and not any(character.isspace() or character == "\\" for character in raw)
            if not good:
                invalid.append(field)
            elif local:
                warnings.append("PUBLIC_HTTPS_CALLBACK_REQUIRED_FOR_PROVIDER_ACCEPTANCE" if not portal else "LOCAL_PORTAL_ONLY")
        except ValueError:
            invalid.append(field)

    address(prefix + "CALLBACK_URL", "/api/subscription/iyzico/callback" if target == "saas" else "/api/payments/iyzico/callback")
    organization_id = None
    if target == "saas":
        address("SAAS_PORTAL_URL", "", portal=True)
        if value(source, "SAAS_CHECKOUT_ENCRYPTION_KEY"):
            try:
                Fernet(str(value(source, "SAAS_CHECKOUT_ENCRYPTION_KEY")).encode())
            except (ValueError, TypeError, UnicodeEncodeError):
                invalid.append("SAAS_CHECKOUT_ENCRYPTION_KEY")
    elif value(source, "IYZICO_ORGANIZATION_ID"):
        try:
            organization_id = str(UUID(str(value(source, "IYZICO_ORGANIZATION_ID"))))
        except (ValueError, TypeError):
            invalid.append("IYZICO_ORGANIZATION_ID")
    configured = not missing and not invalid and not blocked
    active = enabled(source, flag)
    state = "blocked_environment" if blocked else "needs_configuration" if missing or invalid else "sandbox_configured" if mode == "sandbox" else "live_configured"
    return {"target": target, "state": state, "mode": mode, "enabled": active, "configured": configured,
        "available": active and configured, "activation_field": flag, "missing_fields": missing, "invalid_fields": invalid,
        "warnings": warnings, "organization_id": organization_id, "provider_verified": False}


def report(source):
    return {"scope": "offline_configuration_only", "provider_verified": False,
        "saas": configuration(source, "saas"), "school": configuration(source, "school")}


def public_state(source, target):
    """Minimal customer-facing status without installation details or school IDs."""
    result = configuration(source, target)
    return {"available": result["available"], "mode": result["mode"] if result["available"] else None,
        "provider_verified": False}
