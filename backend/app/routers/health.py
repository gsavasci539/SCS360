from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.responses import success_response

router = APIRouter(prefix="/api", tags=["Health"])


@router.get("/health")
async def health():
    return {"status": "ok", **success_response({"status": "healthy"})}


@router.get("/ready")
async def ready(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return success_response({"status": "ready", "database": "connected"})
    except Exception as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={"success": False, "message": "Veritabanı bağlantısı başarısız", "errors": [str(e)]},
        )
