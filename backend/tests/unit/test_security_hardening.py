from io import BytesIO
from zipfile import ZipFile

import pytest
from fastapi import UploadFile
from pydantic import ValidationError

from app.core.config import Settings
from app.core.exceptions import ValidationException
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
        _env_file=None,
    )

    assert settings.APP_ENV == "production"


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
