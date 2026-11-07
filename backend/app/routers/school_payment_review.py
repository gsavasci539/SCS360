from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.application.schemas.school_payment_review import SchoolPaymentReview
from app.application.services import school_payment_review as service
from app.core.database import get_db
from app.core.exceptions import ConflictException
from app.core.dependencies import get_tenant_context
from app.core.responses import success_response
from app.core.tenant import TenantContext

router = APIRouter(tags=["School payment review"])


@router.get("/api/payments/iyzico/reviews")
async def reviews(response: Response, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    tenant: TenantContext = Depends(get_tenant_context), db: AsyncSession = Depends(get_db, scope="function")):
    response.headers["Cache-Control"] = "no-store"
    return success_response(await service.listing(db, tenant, page, page_size))


@router.get("/api/payments/iyzico/checkouts/{checkout_id}/review")
async def review_detail(checkout_id: UUID, response: Response, tenant: TenantContext = Depends(get_tenant_context), db: AsyncSession = Depends(get_db, scope="function")):
    response.headers["Cache-Control"] = "no-store"
    return success_response(await service.metadata(db, tenant, await service.load(db, tenant, checkout_id)))


@router.post("/api/payments/iyzico/checkouts/{checkout_id}/review")
async def resolve_review(checkout_id: UUID, body: SchoolPaymentReview, response: Response,
    tenant: TenantContext = Depends(get_tenant_context), db: AsyncSession = Depends(get_db, scope="function")):
    response.headers["Cache-Control"] = "no-store"
    try:
        return success_response(await service.review(db, tenant, checkout_id, body))
    except IntegrityError:
        # The database dependency rolls back the entire ledger transaction.
        raise ConflictException("İstek veya mutabakat referansı başka bir işlemde kullanılmış") from None
