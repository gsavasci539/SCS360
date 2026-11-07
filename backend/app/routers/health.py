from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.responses import success_response

router = APIRouter(prefix="/api", tags=["Health"])


@router.get("/health")
async def health():
    return {"status": "ok", **success_response({"status": "healthy"})}


@router.get("/ready")
async def ready(request: Request, db: AsyncSession = Depends(get_db, scope="function")):
    try:
        from alembic.script import ScriptDirectory
        from pathlib import Path
        expected = ScriptDirectory(str(Path(__file__).resolve().parents[2] / "alembic")).get_current_head()
        versions = set((await db.execute(text("SELECT version_num FROM alembic_version"))).scalars())
        if versions != {expected}:
            raise RuntimeError("Database migration is required")
        return success_response({"status": "ready", "database": "connected"})
    except Exception:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={"success": False, "message": "Veritabanı bağlantısı veya şema sürümü hazır değil", "errors": [],
                "data": None, "request_id": getattr(request.state, "request_id", None)},
        )
