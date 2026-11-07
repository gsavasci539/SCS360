from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.schemas.school_payment_merchant import SchoolPaymentMerchantUpdate
from app.application.services import school_payment_merchant as service
from app.core.database import get_db
from app.core.dependencies import get_tenant_context
from app.core.responses import success_response
from app.core.tenant import TenantContext

router = APIRouter(tags=["School payment merchant"])


@router.get("/api/payments/merchant")
async def merchant_status(response: Response, tenant: TenantContext = Depends(get_tenant_context), db: AsyncSession = Depends(get_db, scope="function")):
    response.headers["Cache-Control"] = "no-store"
    return success_response(await service.status(db, tenant))


@router.put("/api/payments/merchant")
async def update_merchant(body: SchoolPaymentMerchantUpdate, response: Response, tenant: TenantContext = Depends(get_tenant_context), db: AsyncSession = Depends(get_db, scope="function")):
    response.headers["Cache-Control"] = "no-store"
    return success_response(await service.update(db, tenant, body), "Okul ödeme ayarları kaydedildi")
