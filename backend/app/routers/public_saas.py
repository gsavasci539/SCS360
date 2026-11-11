from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.schemas.saas import PublicSignup, TenantProvision
from app.application.services import platform_service
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.responses import success_response
from app.domain.entities.saas import SubscriptionPlan

router = APIRouter(tags=["Public SaaS"])


@router.get("/api/public/payment-capabilities")
async def payment_capabilities():
    from app.application.services.payment_providers import catalog
    return success_response({"membership": {"WEB": "HOSTED_CHECKOUT", "PWA": "HOSTED_CHECKOUT",
        "IOS": "STORE_BILLING_NOT_CONFIGURED", "ANDROID": "STORE_BILLING_NOT_CONFIGURED"},
        "institution_collection": {"channels": ["WEB", "PWA", "IOS", "ANDROID"],
            "scope": "SERVICES_CONSUMED_OUTSIDE_APP", "providers": catalog(),
            "bank_pos": "CRAFTGATE_CONNECTED_MERCHANT_POS", "direct_bank_adapter": "BANK_PROTOCOL_REQUIRED"},
        "membership_and_institution_accounts_separate": True})


@router.get("/api/public/plans")
@limiter.limit("60/minute")
async def public_plans(request: Request, db: AsyncSession = Depends(get_db, scope="function")):
    rows = (await db.execute(select(SubscriptionPlan).where(SubscriptionPlan.is_active.is_(True)).order_by(SubscriptionPlan.period_months, SubscriptionPlan.price, SubscriptionPlan.id))).scalars()
    return success_response([platform_service.plan_data(row) for row in rows])


@router.post("/api/public/signup")
@limiter.limit("3/minute")
async def signup(request: Request, body: PublicSignup, db: AsyncSession = Depends(get_db, scope="function")):
    # Public registration creates a pending customer, never a paid/trial membership.
    provision = TenantProvision(**body.model_dump())
    return success_response(await platform_service.provision(db, None, provision))
