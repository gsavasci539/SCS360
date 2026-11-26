from __future__ import annotations

from pathlib import Path
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import PermissionChecker
from app.core.responses import success_response
from app.core.tenant import TenantContext
from app.infrastructure.models.models import Branch
from app.infrastructure.storage import FileService

router = APIRouter(prefix="/api/files", tags=["Files"])


def _resolve_scoped_file(file_path: str, tenant: TenantContext, upload_dir: Path) -> Path:
    """Resolve an organization/branch-owned upload without prefix-based path checks."""
    root = upload_dir.resolve()
    parts = file_path.replace("\\", "/").split("/")
    if (
        tenant.organization_id is None
        or len(parts) < 4
        or any(part in {"", ".", ".."} for part in parts)
        or any("\x00" in part for part in parts)
    ):
        raise HTTPException(status_code=404, detail="Dosya bulunamadı")

    try:
        file_organization_id = UUID(parts[0])
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Dosya bulunamadı") from exc
    if file_organization_id != tenant.organization_id:
        raise HTTPException(status_code=404, detail="Dosya bulunamadı")

    if parts[1] == "all":
        if not tenant.has_institution_wide_branch_access:
            raise HTTPException(status_code=404, detail="Dosya bulunamadı")
    else:
        try:
            file_branch_id = UUID(parts[1])
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="Dosya bulunamadı") from exc
        if not tenant.can_access_branch(file_branch_id):
            raise HTTPException(status_code=404, detail="Dosya bulunamadı")

    target = (root / Path(*parts)).resolve()
    if not target.is_relative_to(root):
        raise HTTPException(status_code=404, detail="Dosya bulunamadı")
    return target


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    subfolder: str = "general",
    branch_id: UUID | None = None,
    tenant: TenantContext = Depends(PermissionChecker("files.upload")),
    db: AsyncSession = Depends(get_db, scope="function")
):
    if tenant.organization_id is None:
        raise HTTPException(status_code=403, detail="Kurum kapsamı gerekli")
    if branch_id is not None:
        branch = (await db.execute(select(Branch.id).where(
            Branch.id == branch_id, Branch.organization_id == tenant.organization_id,
            Branch.deleted_at.is_(None),
        ))).scalar_one_or_none()
        if branch is None or not tenant.can_access_branch(branch_id):
            raise HTTPException(status_code=404, detail="Şube bulunamadı")
    elif not tenant.has_institution_wide_branch_access and tenant.branch_ids:
        if len(tenant.branch_ids) != 1:
            raise HTTPException(status_code=400, detail="Şube seçimi gerekli")
        branch_id = tenant.branch_ids[0]
    elif not tenant.has_institution_wide_branch_access:
        raise HTTPException(status_code=403, detail="Atanmış şube kapsamı gerekli")
    file_service = FileService()
    
    try:
        branch_scope = str(branch_id) if branch_id else "all"
        scoped_folder = f"{tenant.organization_id}/{branch_scope}/{subfolder}"
        file_path, _ = await file_service.upload_file(file, scoped_folder)
        relative_path = Path(file_path).relative_to(file_service.upload_dir.resolve()).as_posix()
        file_url = "/api/files/" + "/".join(quote(part, safe="") for part in relative_path.split("/"))
        return success_response({
            "file_path": relative_path,
            "file_url": file_url,
            "filename": file.filename
        }, "Dosya yüklendi")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Dosya yükleme hatası") from e


@router.delete("/{file_path:path}")
async def delete_file(
    file_path: str,
    tenant: TenantContext = Depends(PermissionChecker("files.delete")),
):
    file_service = FileService()
    target_path = _resolve_scoped_file(file_path, tenant, Path(file_service.settings.UPLOAD_DIR))
    
    deleted = file_service.delete_file(str(target_path))
    
    if deleted:
        return success_response(message="Dosya silindi")
    else:
        raise HTTPException(status_code=404, detail="Dosya bulunamadı")


@router.get("/{file_path:path}")
async def get_file(
    file_path: str,
    tenant: TenantContext = Depends(PermissionChecker("files.upload")),
):
    file_service = FileService()
    target_path = _resolve_scoped_file(file_path, tenant, Path(file_service.settings.UPLOAD_DIR))
    
    file_obj = file_service.get_file(str(target_path))
    
    if not file_obj:
        raise HTTPException(status_code=404, detail="Dosya bulunamadı")
    
    return FileResponse(
        file_obj,
        filename=file_obj.name,
        content_disposition_type="attachment",
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )
