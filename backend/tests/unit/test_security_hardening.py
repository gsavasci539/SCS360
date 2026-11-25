from io import BytesIO
from zipfile import ZipFile

import pytest
from fastapi import FastAPI, UploadFile
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.core.exceptions import ValidationException
from app.core.middleware import SecurityHeadersMiddleware
from app.routers.files_receipts import _validate_upload


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
        CORS_ORIGINS="https://school.example",
        PASSWORD_RESET_URL="https://school.example/reset-password",
        RATE_LIMIT_STORAGE_URI="rediss://:a-unique-rate-limit-secret-with-more-than-32-characters@redis.example:6379/0",
        _env_file=None,
    )

    assert settings.APP_ENV == "production"
    assert settings.api_docs_enabled is False


@pytest.mark.parametrize("storage_uri", [
    "memory://",
    "redis://rate-limit-store:6379/0",
    "rediss://:REPLACE_WITH_32_PLUS_URL_SAFE_RANDOM_CHARACTERS@redis.example:6379/0",
    "rediss://:a-unique-rate-limit-secret-with-more-than-32-characters@localhost:6379/0",
    "redis://:short@rate-limit-store:6379/0",
    "http://user:password@rate-limit-store:6379/0",
])
def test_production_requires_authenticated_shared_rate_limit_storage(storage_uri):
    with pytest.raises(ValidationError, match="shared Redis rate-limit storage"):
        Settings(
            APP_ENV="production",
            JWT_SECRET_KEY="a-unique-production-secret-with-more-than-32-characters",
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
            CORS_ORIGINS=origin,
            PASSWORD_RESET_URL="https://school.example/reset-password",
            _env_file=None,
        )


def test_production_requires_https_password_reset_url_even_without_mail_delivery():
    with pytest.raises(ValidationError, match="PASSWORD_RESET_URL"):
        Settings(
            APP_ENV="production",
            JWT_SECRET_KEY="a-unique-production-secret-with-more-than-32-characters",
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
