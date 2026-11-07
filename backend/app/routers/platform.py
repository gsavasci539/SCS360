from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.schemas.saas import MembershipWrite, PlanWrite, TenantProvision, TenantStatusWrite, SubscriptionInvoiceCreate, VerifiedReceipt
from app.application.services import platform_service as service
from app.application.services import subscription_billing_service as billing
from app.application.services import subscription_checkout_service as checkouts
from app.application.services.saas_gateway import get_saas_gateway
from app.application.services.subscription_access import evaluate, for_user
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_super_admin
from app.core.responses import success_response
from app.domain.entities.saas import OrganizationSubscription, SubscriptionPlan, SubscriptionInvoice
from app.infrastructure.models.models import Organization, User

router = APIRouter(tags=["SaaS Platform"])


@router.get("/api/platform/payment-readiness")
async def payment_readiness(actor: User = Depends(require_super_admin)):
    from app.application.services.payment_readiness import report
    return success_response(report(service.get_settings()))


@router.get("/api/platform/plans")
async def plans(actor: User = Depends(require_super_admin), db: AsyncSession = Depends(get_db, scope="function")):
    rows = (await db.execute(select(SubscriptionPlan).order_by(SubscriptionPlan.name, SubscriptionPlan.id))).scalars()
    return success_response([service.plan_data(row) for row in rows])


@router.post("/api/platform/plans")
async def create_plan(body: PlanWrite, actor: User = Depends(require_super_admin), db: AsyncSession = Depends(get_db, scope="function")):
    return success_response(await service.create_plan(db, actor, body))


@router.post("/api/platform/tenants")
async def create_tenant(body: TenantProvision, actor: User = Depends(require_super_admin), db: AsyncSession = Depends(get_db, scope="function")):
    return success_response(await service.provision(db, actor, body))


@router.put("/api/platform/plans/{plan_id}")
async def update_plan(plan_id: UUID, body: PlanWrite, actor: User = Depends(require_super_admin), db: AsyncSession = Depends(get_db, scope="function")):
    plan = await service.get_plan(db, plan_id)
    for key, value in body.model_dump().items():
        setattr(plan, key, value)
    service.audit(db, actor, None, "PLAN_UPDATED", {"plan_id": str(plan.id)})
    await service.commit(db)
    return success_response(service.plan_data(plan))


@router.get("/api/platform/tenants")
async def tenants(search: str = Query("", max_length=100), limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
    actor: User = Depends(require_super_admin), db: AsyncSession = Depends(get_db, scope="function")):
    query = select(Organization).where(Organization.deleted_at.is_(None))
    if search.strip():
        query = query.where(Organization.name.ilike(f"%{search.strip()}%"))
    organizations = (await db.execute(query.order_by(Organization.name, Organization.id).limit(limit).offset(offset))).scalars().all()
    memberships = {row.organization_id: row for row in (await db.execute(select(OrganizationSubscription).where(
        OrganizationSubscription.organization_id.in_([org.id for org in organizations])))).scalars()}
    result = []
    for org in organizations:
        member = memberships.get(org.id)
        result.append({"id": str(org.id), "name": org.name, "is_active": org.is_active, "access": evaluate(member, active=org.is_active),
            "package": member.package_snapshot if member else None, "usage": await service.usage(db, org.id),
            "owner_user_id": str(member.owner_user_id) if member and member.owner_user_id else None,
            "period_start": service.utc(member.period_start).isoformat() if member and member.period_start else None})
    return success_response(result)


@router.get("/api/platform/summary")
async def platform_summary(actor: User = Depends(require_super_admin), db: AsyncSession = Depends(get_db, scope="function")):
    organizations = (await db.execute(select(Organization).where(Organization.deleted_at.is_(None)))).scalars().all()
    members = {row.organization_id: row for row in (await db.execute(select(OrganizationSubscription))).scalars()}
    states = [evaluate(members.get(org.id), active=org.is_active)["status"] for org in organizations]
    pending = (await db.execute(select(func.count(SubscriptionInvoice.id)).where(SubscriptionInvoice.status.in_(["PENDING", "PAYMENT_REVIEW", "PAID_REVIEW"])))).scalar_one()
    return success_response({"total_institutions": len(organizations), "active_memberships": states.count("ACTIVE"),
        "grace_memberships": states.count("GRACE"), "legacy_institutions": states.count("LEGACY"),
        "restricted_institutions": sum(state not in {"ACTIVE", "GRACE", "LEGACY"} for state in states), "pending_invoices": pending})


@router.get("/api/platform/tenants/{org_id}/workspace")
async def tenant_workspace(org_id: UUID, actor: User = Depends(require_super_admin), db: AsyncSession = Depends(get_db, scope="function")):
    org = (await db.execute(select(Organization).where(Organization.id == org_id, Organization.deleted_at.is_(None)))).scalar_one_or_none()
    if org is None:
        from app.core.exceptions import NotFoundException
        raise NotFoundException("Kurum bulunamadı")
    return success_response({"id": str(org.id), "name": org.name})


@router.get("/api/platform/tenants/{org_id}/users")
async def tenant_users(org_id: UUID, actor: User = Depends(require_super_admin), db: AsyncSession = Depends(get_db, scope="function")):
    rows = (await db.execute(select(User).where(User.organization_id == org_id, User.deleted_at.is_(None), User.status == "ACTIVE",
        User.is_super_admin.is_(False)).order_by(User.first_name, User.id).limit(1000))).scalars()
    return success_response([{"id": str(row.id), "name": f"{row.first_name} {row.last_name}", "email": row.email} for row in rows])


@router.put("/api/platform/tenants/{org_id}/subscription")
async def configure_membership(org_id: UUID, body: MembershipWrite, actor: User = Depends(require_super_admin), db: AsyncSession = Depends(get_db, scope="function")):
    return success_response(await service.set_membership(db, actor, org_id, body))


@router.patch("/api/platform/tenants/{org_id}/status")
async def tenant_status(org_id: UUID, body: TenantStatusWrite, actor: User = Depends(require_super_admin), db: AsyncSession = Depends(get_db, scope="function")):
    org = await service.set_account_status(db, actor, org_id, body.is_active)
    await service.commit(db)
    return success_response({"id": str(org.id), "is_active": org.is_active})


@router.get("/api/subscription/access")
async def subscription_access(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db, scope="function"), gateway=Depends(get_saas_gateway)):
    can_manage = await billing.can_manage(db, user)
    member = (await db.execute(select(OrganizationSubscription).where(OrganizationSubscription.organization_id == user.organization_id))).scalar_one_or_none() if user.organization_id else None
    return success_response({"organization_id": str(user.organization_id) if user.organization_id else None,
        "access": await for_user(db, user), "can_manage": can_manage,
        "online_payment_available": bool(can_manage and gateway.available()),
        **({"payment_instructions": service.get_settings().SAAS_PAYMENT_INSTRUCTIONS, "support_email": service.get_settings().SAAS_SUPPORT_EMAIL} if can_manage else {}),
        **({"usage": await service.usage(db, user.organization_id), "package": member.package_snapshot if member else None} if can_manage and user.organization_id else {})})


@router.get("/api/subscription/plans")
async def available_plans(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db, scope="function")):
    await billing.require_manager(db, user)
    rows = (await db.execute(select(SubscriptionPlan).where(SubscriptionPlan.is_active.is_(True)).order_by(SubscriptionPlan.name, SubscriptionPlan.id))).scalars()
    return success_response([service.plan_data(row) for row in rows])


@router.get("/api/subscription/invoices")
async def own_invoices(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0), user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db, scope="function")):
    await billing.require_manager(db, user)
    rows = (await db.execute(select(SubscriptionInvoice).where(SubscriptionInvoice.organization_id == user.organization_id)
        .order_by(SubscriptionInvoice.created_at.desc(), SubscriptionInvoice.id).limit(limit).offset(offset))).scalars()
    return success_response(await checkouts.list_data(db, rows, user))


@router.post("/api/subscription/invoices")
async def request_invoice(body: SubscriptionInvoiceCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db, scope="function")):
    return success_response(await billing.create_invoice(db, user, body))


@router.post("/api/subscription/invoices/{invoice_id}/cancel")
async def cancel_invoice(invoice_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db, scope="function")):
    return success_response(await billing.cancel_invoice(db, user, invoice_id))


@router.get("/api/platform/invoices")
async def platform_invoices(organization_id: UUID | None = None, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
    actor: User = Depends(require_super_admin), db: AsyncSession = Depends(get_db, scope="function")):
    query = select(SubscriptionInvoice)
    if organization_id:
        query = query.where(SubscriptionInvoice.organization_id == organization_id)
    rows = (await db.execute(query.order_by(SubscriptionInvoice.created_at.desc(), SubscriptionInvoice.id).limit(limit).offset(offset))).scalars()
    rows = list(rows)
    names = {org.id: org.name for org in (await db.execute(select(Organization).where(Organization.id.in_({row.organization_id for row in rows})))).scalars()}
    data = await checkouts.list_data(db, rows, actor)
    return success_response([{**row, "organization_name": names.get(UUID(row["organization_id"]))} for row in data])


@router.post("/api/platform/invoices/{invoice_id}/settle")
async def settle_receipt(invoice_id: UUID, body: VerifiedReceipt, actor: User = Depends(require_super_admin), db: AsyncSession = Depends(get_db, scope="function")):
    return success_response(await billing.settle_manual(db, actor, invoice_id, body))
