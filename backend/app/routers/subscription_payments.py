from uuid import UUID

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.schemas.saas import SubscriptionCheckoutStart, SubscriptionPaymentReview
from app.application.services import subscription_checkout_service as service
from app.application.services.saas_gateway import get_saas_gateway
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_super_admin
from app.core.exceptions import AppException
from app.core.rate_limit import get_client_ip, limiter
from app.core.responses import success_response
from app.infrastructure.models.models import User

router = APIRouter(tags=["Subscription payments"])


def no_store(response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"


@router.post("/api/subscription/invoices/{invoice_id}/activate-free")
async def activate_free(response: Response, invoice_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db, scope="function")):
    no_store(response)
    return success_response(await service.activate_free(db, user, invoice_id))


@router.post("/api/subscription/invoices/{invoice_id}/checkout")
@limiter.limit("5/minute")
async def initialize(request: Request, response: Response, invoice_id: UUID, body: SubscriptionCheckoutStart,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db, scope="function"), gateway=Depends(get_saas_gateway)):
    no_store(response)
    data = await service.initialize(db, user, invoice_id, body, get_client_ip(request), gateway)
    if data["status"] == "INITIALIZING":
        response.status_code = 202
    return success_response(data)


@router.post("/api/subscription/invoices/{invoice_id}/resume")
async def resume(response: Response, invoice_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db, scope="function"), gateway=Depends(get_saas_gateway)):
    no_store(response)
    return success_response(await service.resume(db, user, invoice_id, gateway))


@router.post("/api/subscription/invoices/{invoice_id}/payment-status")
@limiter.limit("30/minute")
async def payment_status(request: Request, response: Response, invoice_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db, scope="function"), gateway=Depends(get_saas_gateway)):
    no_store(response)
    return success_response(await service.check_status(db, user, invoice_id, gateway))


@router.post("/api/subscription/iyzico/callback")
async def callback(token: str = Form(min_length=1, max_length=2048), db: AsyncSession = Depends(get_db, scope="function"), gateway=Depends(get_saas_gateway)):
    try:
        await service.reconcile(db, token, gateway)
    except AppException as exc:
        if exc.status_code not in {502, 503}:
            raise
    return RedirectResponse(gateway.return_url(), status_code=303, headers={"Cache-Control": "no-store", "Pragma": "no-cache"})


@router.post("/api/platform/invoices/{invoice_id}/payment-status")
async def platform_status(response: Response, invoice_id: UUID, user: User = Depends(require_super_admin), db: AsyncSession = Depends(get_db, scope="function"), gateway=Depends(get_saas_gateway)):
    no_store(response)
    return success_response(await service.check_status(db, user, invoice_id, gateway, platform_user=True))


@router.post("/api/platform/invoices/{invoice_id}/review")
async def review(response: Response, invoice_id: UUID, body: SubscriptionPaymentReview, user: User = Depends(require_super_admin), db: AsyncSession = Depends(get_db, scope="function")):
    no_store(response)
    return success_response(await service.review(db, user, invoice_id, body))
