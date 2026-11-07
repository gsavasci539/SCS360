import asyncio
import uuid
from pathlib import Path

from app.core.exceptions import ValidationException

from app.core.config import get_settings

settings = get_settings()


class LocalFileStorage:
    def __init__(self, base_dir: str | None = None):
        self.base_dir = Path(base_dir or settings.UPLOAD_DIR).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, content: bytes, original_name: str, subfolder: str = "") -> str:
        ext = Path(original_name.replace("\\", "/").rsplit("/", 1)[-1]).suffix.lower()
        filename = f"{uuid.uuid4()}{ext}"
        target_dir = self.get_full_path(subfolder) if subfolder else self.base_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / filename
        path.write_bytes(content)
        return path.relative_to(self.base_dir).as_posix()

    def get_full_path(self, storage_path: str) -> Path:
        path = (self.base_dir / storage_path).resolve()
        if not path.is_relative_to(self.base_dir):
            raise ValidationException("İzin verilmeyen dosya yolu")
        return path

    async def save_async(self, content: bytes, original_name: str, subfolder: str = "") -> str:
        return await asyncio.to_thread(self.save, content, original_name, subfolder)
