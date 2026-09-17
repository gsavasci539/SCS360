from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path

from app.infrastructure.storage import FileService
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.permissions import require_permission
from app.core.responses import success_response
from app.domain.entities.user import User

router = APIRouter(prefix="/api/files", tags=["Files"])


@router.post("/upload")
@require_permission("files.upload")
async def upload_file(
    file: UploadFile = File(...),
    subfolder: str = "general",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    file_service = FileService()
    
    try:
        file_path, file_url = await file_service.upload_file(file, subfolder)
        return success_response({
            "file_path": file_path,
            "file_url": file_url,
            "filename": file.filename
        }, "Dosya yüklendi")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dosya yükleme hatası: {str(e)}")


@router.delete("/{file_path:path}")
@require_permission("files.delete")
async def delete_file(
    file_path: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    file_service = FileService()
    
    # Security: Ensure file is within upload directory
    from app.core.config import get_settings
    settings = get_settings()
    upload_dir = Path(settings.UPLOAD_DIR).resolve()
    target_path = (upload_dir / file_path).resolve()
    
    if not str(target_path).startswith(str(upload_dir)):
        raise HTTPException(status_code=403, detail="İzin verilmeyen dosya yolu")
    
    deleted = file_service.delete_file(str(target_path))
    
    if deleted:
        return success_response(message="Dosya silindi")
    else:
        raise HTTPException(status_code=404, detail="Dosya bulunamadı")


@router.get("/{file_path:path}")
async def get_file(
    file_path: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    file_service = FileService()
    
    # Security: Ensure file is within upload directory
    from app.core.config import get_settings
    settings = get_settings()
    upload_dir = Path(settings.UPLOAD_DIR).resolve()
    target_path = (upload_dir / file_path).resolve()
    
    if not str(target_path).startswith(str(upload_dir)):
        raise HTTPException(status_code=403, detail="İzin verilmeyen dosya yolu")
    
    file_obj = file_service.get_file(str(target_path))
    
    if not file_obj:
        raise HTTPException(status_code=404, detail="Dosya bulunamadı")
    
    return FileResponse(file_obj)
