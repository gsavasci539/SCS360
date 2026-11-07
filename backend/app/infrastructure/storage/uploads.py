"""Bounded multipart reads shared by document upload endpoints."""
from io import BytesIO
from zipfile import BadZipFile, ZipFile

from fastapi import UploadFile

from app.core.config import get_settings
from app.core.exceptions import ValidationException


def upload_name(file: UploadFile) -> str:
    name = (file.filename or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not name or len(name) > 255 or any(ord(char) < 32 for char in name):
        raise ValidationException("Geçerli bir dosya adı gerekli")
    return name


async def read_upload(file: UploadFile, extensions: set[str] | None = None) -> tuple[str, bytes]:
    settings = get_settings()
    name = upload_name(file)
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    allowed = extensions if extensions is not None else set(settings.allowed_file_types_list)
    if ext not in allowed:
        raise ValidationException("İzin verilmeyen dosya türü")
    # A single over-limit chunk is sufficient; never read an unbounded upload.
    content = await file.read(settings.max_upload_size_bytes + 1)
    if len(content) > settings.max_upload_size_bytes:
        raise ValidationException(f"Dosya boyutu {settings.MAX_UPLOAD_SIZE_MB}MB limitini aşıyor")
    if not content:
        raise ValidationException("Boş dosya yüklenemez")
    signatures = {"pdf": b"%PDF-", "jpg": b"\xff\xd8\xff", "jpeg": b"\xff\xd8\xff",
        "png": b"\x89PNG\r\n\x1a\n"}
    if ext in signatures and not content.startswith(signatures[ext]):
        raise ValidationException("Dosya içeriği uzantısıyla eşleşmiyor")
    if ext in {"docx", "pptx"}:
        try:
            with ZipFile(BytesIO(content)) as archive:
                names = set(archive.namelist())
        except BadZipFile as exc:
            raise ValidationException("Geçersiz Office belgesi") from exc
        document = "word/document.xml" if ext == "docx" else "ppt/presentation.xml"
        if "[Content_Types].xml" not in names or document not in names:
            raise ValidationException("Geçersiz Office belgesi")
    return name, content
