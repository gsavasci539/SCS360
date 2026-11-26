from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pytest
from fastapi import FastAPI, UploadFile
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.core.exceptions import ValidationException
from app.core.middleware import SecurityHeadersMiddleware
from app.core.web_session import ACCESS_COOKIE
from app.routers.files_receipts import _validate_upload

TEST_ORG_TAX_KEY = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="


def test_production_rejects_placeholder_jwt_secret():
    with pytest.raises(ValidationError):
        Settings(
            APP_ENV="production",
            JWT_SECRET_KEY="replace-with-a-long-random-secret",
            _env_file=None,
        )


def test_production_accepts_strong_jwt_secret():
    settings = Settings(
        APP_ENV="production",
        JWT_SECRET_KEY="a-unique-production-secret-with-more-than-32-characters",
        ORGANIZATION_TAX_NUMBER_ENCRYPTION_KEY=TEST_ORG_TAX_KEY,
        CORS_ORIGINS="https://school.example",
        PASSWORD_RESET_URL="https://school.example/reset-password",
        RATE_LIMIT_STORAGE_URI="rediss://:a-unique-rate-limit-secret-with-more-than-32-characters@redis.example:6379/0",
        _env_file=None,
    )

    assert settings.APP_ENV == "production"
    assert settings.api_docs_enabled is False


def test_production_allows_plain_redis_only_for_private_compose_service():
    settings = Settings(
        APP_ENV="production",
        JWT_SECRET_KEY="a-unique-production-secret-with-more-than-32-characters",
        ORGANIZATION_TAX_NUMBER_ENCRYPTION_KEY=TEST_ORG_TAX_KEY,
        CORS_ORIGINS="https://school.example",
        PASSWORD_RESET_URL="https://school.example/reset-password",
        RATE_LIMIT_STORAGE_URI="redis://:a-unique-rate-limit-secret-with-more-than-32-characters@rate-limit-store:6379/0",
        _env_file=None,
    )

    assert settings.RATE_LIMIT_STORAGE_URI.startswith("redis://")


@pytest.mark.parametrize("storage_uri", [
    "memory://",
    "redis://rate-limit-store:6379/0",
    "redis://:a-unique-rate-limit-secret-with-more-than-32-characters@redis.example:6379/0",
    "rediss://:REPLACE_WITH_32_PLUS_URL_SAFE_RANDOM_CHARACTERS@redis.example:6379/0",
    "rediss://:a-unique-rate-limit-secret-with-more-than-32-characters@localhost:6379/0",
    "redis://:short@rate-limit-store:6379/0",
    "http://user:password@rate-limit-store:6379/0",
])
def test_production_requires_authenticated_shared_rate_limit_storage(storage_uri):
    with pytest.raises(ValidationError, match="TLS Redis or the private Compose rate-limit store"):
        Settings(
            APP_ENV="production",
            JWT_SECRET_KEY="a-unique-production-secret-with-more-than-32-characters",
            ORGANIZATION_TAX_NUMBER_ENCRYPTION_KEY=TEST_ORG_TAX_KEY,
            CORS_ORIGINS="https://school.example",
            PASSWORD_RESET_URL="https://school.example/reset-password",
            RATE_LIMIT_STORAGE_URI=storage_uri,
            _env_file=None,
        )


@pytest.mark.parametrize("origin", [
    "http://school.example",
    "https://localhost:5173",
    "https://school.example/path",
    "https://user:password@school.example",
])
def test_production_rejects_non_exact_or_insecure_cors_origins(origin):
    with pytest.raises(ValidationError):
        Settings(
            APP_ENV="production",
            JWT_SECRET_KEY="a-unique-production-secret-with-more-than-32-characters",
            ORGANIZATION_TAX_NUMBER_ENCRYPTION_KEY=TEST_ORG_TAX_KEY,
            CORS_ORIGINS=origin,
            PASSWORD_RESET_URL="https://school.example/reset-password",
            _env_file=None,
        )


def test_production_requires_https_password_reset_url_even_without_mail_delivery():
    with pytest.raises(ValidationError, match="PASSWORD_RESET_URL"):
        Settings(
            APP_ENV="production",
            JWT_SECRET_KEY="a-unique-production-secret-with-more-than-32-characters",
            ORGANIZATION_TAX_NUMBER_ENCRYPTION_KEY=TEST_ORG_TAX_KEY,
            CORS_ORIGINS="https://school.example",
            PASSWORD_RESET_URL="http://school.example/reset-password",
            RATE_LIMIT_STORAGE_URI="rediss://:a-unique-rate-limit-secret-with-more-than-32-characters@redis.example:6379/0",
            NOTIFICATION_DELIVERY_ENABLED=False,
            _env_file=None,
        )


def test_production_requires_https_payment_callbacks_when_enabled():
    with pytest.raises(ValidationError, match="School payment callback"):
        Settings(
            APP_ENV="production",
            JWT_SECRET_KEY="a-unique-production-secret-with-more-than-32-characters",
            ORGANIZATION_TAX_NUMBER_ENCRYPTION_KEY=TEST_ORG_TAX_KEY,
            CORS_ORIGINS="https://school.example",
            PASSWORD_RESET_URL="https://school.example/reset-password",
            RATE_LIMIT_STORAGE_URI="rediss://:a-unique-rate-limit-secret-with-more-than-32-characters@redis.example:6379/0",
            IYZICO_PAYMENT_ENABLED=True,
            SCHOOL_PAYMENT_CALLBACK_URL="http://school.example/callback",
            _env_file=None,
        )


def test_security_headers_protect_api_responses_from_caching_and_sniffing():
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/api/private")
    def private_data():
        return {"ok": True}

    response = TestClient(app).get("/api/private")

    assert response.headers["cache-control"] == "no-store, max-age=0"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"


def test_csrf_rejection_keeps_api_security_headers():
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.post("/api/private")
    def private_write():
        return {"ok": True}

    client = TestClient(app)
    client.cookies.set(ACCESS_COOKIE, "session")
    response = client.post("/api/private")

    assert response.status_code == 403
    assert response.headers["permissions-policy"] == "camera=(), microphone=(), geolocation=()"
    assert response.headers["cache-control"] == "no-store, max-age=0"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"


def test_frontend_nginx_keeps_security_headers_on_immutable_assets():
    repo_root = Path(__file__).resolve().parents[3]
    config = (repo_root / "frontend" / "nginx.conf").read_text(encoding="utf-8")
    assets = config.split("location /assets/ {", 1)[1].split("\n  }", 1)[0]

    assert "server_tokens off;" in config
    assert 'Strict-Transport-Security "max-age=31536000; includeSubDomains" always;' in config
    assert "proxy_hide_header Server;" in config
    assert "proxy_hide_header X-Powered-By;" in config
    for header in (
        "Strict-Transport-Security",
        "Content-Security-Policy",
        "X-Content-Type-Options",
        "X-Frame-Options",
        "Referrer-Policy",
        "Permissions-Policy",
    ):
        assert f"add_header {header} " in assets


def test_public_nginx_emits_a_single_authoritative_security_header_set():
    repo_root = Path(__file__).resolve().parents[3]
    config = (repo_root / "nginx" / "default.conf").read_text(encoding="utf-8")

    for header in (
        "Server",
        "X-Powered-By",
        "Strict-Transport-Security",
        "Content-Security-Policy",
        "X-Content-Type-Options",
        "X-Frame-Options",
        "Referrer-Policy",
        "Permissions-Policy",
    ):
        assert config.count(f"proxy_hide_header {header};") == 1


def test_public_nginx_rejects_unknown_host_headers():
    repo_root = Path(__file__).resolve().parents[3]
    config = (repo_root / "nginx" / "default.conf").read_text(encoding="utf-8")

    assert "listen 80 default_server;" in config
    assert "server_name _;\n    return 444;" in config
    assert "server_name scs360.com.tr scs.bytebridge.com.tr;" in config


def test_upload_rejects_extension_content_mismatch():
    upload = UploadFile(file=BytesIO(b"not a pdf"), filename="record.pdf")

    with pytest.raises(ValidationException, match="içeriği"):
        _validate_upload(upload, b"not a pdf")


def test_upload_accepts_minimal_docx_structure():
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
        archive.writestr("word/document.xml", "<document />")
    content = buffer.getvalue()
    upload = UploadFile(file=BytesIO(content), filename="record.docx")

    _validate_upload(upload, content)
