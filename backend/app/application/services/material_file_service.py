"""Private material storage and parent visibility rules, including legacy files."""
import asyncio
import mimetypes
import os
from datetime import date
from pathlib import Path
from uuid import UUID, uuid4

from fastapi.responses import FileResponse
from sqlalchemy import and_, or_, select, update, func

from app.core.dates import school_today
from app.core.config import get_settings
from app.core.exceptions import NotFoundException
from app.domain.entities.materials import CourseMaterial
from app.infrastructure.models.models import ClassRoom, User


def download_url(material_id) -> str:
    return f"/api/materials/{material_id}/file"


def visible_to_child(student):
    owners = select(User.id).where(User.organization_id == student.organization_id, User.deleted_at.is_(None))
    classes = select(ClassRoom.id).where(ClassRoom.organization_id == student.organization_id)
    return and_(CourseMaterial.is_active.is_(True),
        or_(CourseMaterial.visible_from.is_(None), CourseMaterial.visible_from <= school_today()),
        or_(CourseMaterial.visible_until.is_(None), CourseMaterial.visible_until >= school_today()),
        or_(and_(CourseMaterial.visibility == "CLASS_ONLY", CourseMaterial.class_id == student.class_id)
            if student.class_id else False,
            and_(CourseMaterial.visibility == "PUBLIC",
                or_(CourseMaterial.class_id.in_(classes), CourseMaterial.teacher_id.in_(owners),
                    CourseMaterial.created_by.in_(owners)))))


def private_path(material_id) -> Path:
    root = Path(get_settings().PRIVATE_UPLOAD_DIR).resolve() / "materials"
    return root / str(UUID(str(material_id))) / "content"


async def save_content(material_id, content):
    def save():
        target = private_path(material_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(uuid4().hex + ".tmp")
        try:
            temporary.write_bytes(content)
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
    await asyncio.to_thread(save)


async def file_response(db, material):
    path = private_path(material.id)
    # Existing records retain their original storage location; never expose it publicly.
    if not path.is_file() and material.file_url.startswith("/uploads/materials/"):
        name = material.file_url.removeprefix("/uploads/materials/")
        if not name or "/" in name or "\\" in name or name in {".", ".."}:
            raise NotFoundException("Materyal dosyası bulunamadı")
        root = Path(get_settings().UPLOAD_DIR).resolve() / "materials"
        path = (root / name).resolve()
        if not path.is_relative_to(root):
            raise NotFoundException("Materyal dosyası bulunamadı")
    if not path.is_file():
        raise NotFoundException("Materyal dosyası bulunamadı")
    await db.execute(update(CourseMaterial).where(CourseMaterial.id == material.id)
        .values(download_count=func.coalesce(CourseMaterial.download_count, 0) + 1))
    await db.flush()
    return FileResponse(path, filename=material.file_name or "materyal",
        media_type=mimetypes.guess_type(material.file_name or "")[0] or "application/octet-stream",
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})
