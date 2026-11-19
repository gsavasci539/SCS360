"""Private message files addressed by the persisted message ID and content hash."""
import asyncio
import os
import re
from dataclasses import dataclass
from hashlib import sha256
from uuid import UUID, uuid4

from fastapi import UploadFile
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.core.exceptions import NotFoundException
from app.infrastructure.storage.local_storage import LocalFileStorage
from app.infrastructure.storage.uploads import read_upload


@dataclass(frozen=True)
class MessageUpload:
    name: str
    content: bytes
    digest: str


async def message_upload(file: UploadFile) -> MessageUpload:
    name, content = await read_upload(file, {"pdf", "png", "jpg", "jpeg"})
    return MessageUpload(name, content, sha256(content).hexdigest())


def attachment_path(message_id: UUID, digest: str):
    if not re.fullmatch(r"[a-f0-9]{64}", digest):
        return None
    storage = LocalFileStorage(get_settings().PRIVATE_UPLOAD_DIR)
    return storage.get_full_path(f"messages/{message_id}/{digest}")


def message_attachment_response(message):
    if message is None or not message.attachment_name or not message.attachment_sha256:
        raise NotFoundException("Mesaj eki bulunamadı")
    path = attachment_path(message.id, message.attachment_sha256)
    if path is None or not path.is_file():
        raise NotFoundException("Mesaj eki bulunamadı")
    return FileResponse(path, filename=message.attachment_name, media_type="application/octet-stream",
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


async def save_message_attachment(message_id: UUID, upload: MessageUpload) -> None:
    target = attachment_path(message_id, upload.digest)
    assert target is not None

    def persist():
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f"{uuid4().hex}.tmp")
        try:
            temporary.write_bytes(upload.content)
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)

    await asyncio.to_thread(persist)
