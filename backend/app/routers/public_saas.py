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
