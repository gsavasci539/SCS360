"""Print deployment readiness flags without exposing credentials.

Use --require-integrations for a release that includes all external providers.
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


async def inspect(require_integrations, *, max_scan_rows=250_000):
    # Register the same model graph as the running API without executing its
    # lifespan, seeds, migrations or external-provider delivery.
    import app.main  # noqa: F401
    from alembic.script import ScriptDirectory
    from app.core.config import get_settings
    from app.core.database import Base, engine
    from app.core.release_integrity import inspect_release_integrity
    settings = get_settings()
    engine.echo = False
    checks = {
        "production_environment": settings.APP_ENV == "production",
        "postgresql_database": settings.DATABASE_URL.startswith("postgresql+asyncpg://"),
        "https_cors_origins": bool(settings.cors_origins_list) and all(origin.startswith("https://") for origin in settings.cors_origins_list),
        "strong_jwt_secret": len(settings.JWT_SECRET_KEY) >= 32 and settings.JWT_SECRET_KEY != "development-only-change-me",
        "https_password_reset": settings.PASSWORD_RESET_URL.startswith("https://"),
        "schema_current": False,
        "database_integrity": False,
    }
    providers = {
        "smtp": bool(settings.SMTP_HOST and settings.SMTP_HOST != "smtp.example.com" and settings.SMTP_FROM_EMAIL and settings.SMTP_USER and settings.SMTP_PASSWORD),
        "sms": all([settings.SMS_API_URL, settings.SMS_USERNAME, settings.SMS_PASSWORD, settings.SMS_HEADER]),
        "whatsapp": all([settings.WHATSAPP_ACCESS_TOKEN, settings.WHATSAPP_PHONE_NUMBER_ID]),
        "iyzico": all([settings.IYZICO_API_KEY, settings.IYZICO_SECRET_KEY, settings.IYZICO_CALLBACK_URL]),
        "notification_delivery_enabled": settings.NOTIFICATION_DELIVERY_ENABLED,
        "notification_webhook_configured": bool(settings.NOTIFICATION_WEBHOOK_SECRET),
    }
    integrity = {"ready": False, "snapshot_read_only": False,
        "issues": [{"check": "scan", "reason": "scan_failed", "count": 1}]}
    try:
        expected = ScriptDirectory(str(Path(__file__).resolve().parents[1] / "alembic")).get_current_head()
        integrity = await inspect_release_integrity(engine, Base.metadata, expected_revision=expected,
            max_scan_rows=max_scan_rows)
        checks["schema_current"] = integrity.get("schema_current") is True
        checks["database_integrity"] = integrity.get("ready") is True
    except Exception:
        pass
    finally:
        await engine.dispose()
    ready = all(checks.values()) and (all(providers.values()) if require_integrations else True)
    print(json.dumps({"ready": ready, "scope": "application_and_integrations" if require_integrations else "application_only",
        "checks": checks, "provider_configuration": providers,
        "database_integrity": integrity,
        "provider_live_acceptance": "requires separate sandbox/delivery verification"}, ensure_ascii=False, indent=2))
    return 0 if ready else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-integrations", action="store_true")
    parser.add_argument("--max-scan-rows", type=int, default=250_000,
        help="Maximum aggregate physical rows for the read-only integrity scan; exceeding it fails readiness.")
    args = parser.parse_args()
    try:
        sys.exit(asyncio.run(inspect(args.require_integrations, max_scan_rows=args.max_scan_rows)))
    except Exception:
        print(json.dumps({"ready": False, "configuration_valid": False,
            "message": "Production environment variables are missing or invalid"}))
        sys.exit(1)
