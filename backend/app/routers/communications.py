"""
Omnichannel Communication Module API
Handles SMS providers, broadcast jobs, and delivery reports
"""
from datetime import datetime, date
from typing import Optional, List, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from pydantic import ValidationError as SchemaValidationError
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.responses import success_response
from app.core.permissions import PermissionChecker
from app.core.tenant import TenantContext
from app.domain.entities import User, Branch, Class
from app.application.services import broadcast_service
from app.core.exceptions import ValidationException

router = APIRouter(prefix="/api/communications", tags=["Communications"])


# ==================== Schemas ====================

class BroadcastJobCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    message_content: str = Field(..., min_length=1, max_length=10000)
    target_audience: Literal["ALL_PARENTS", "BRANCH_PARENTS", "CLASS_PARENTS", "ALL_TEACHERS", "ALL_STAFF"]
    target_class_id: Optional[UUID] = None
    target_branch_id: Optional[UUID] = None
    target_role: Optional[Literal["OWNER", "ADMIN", "TEACHER", "STAFF"]] = None
    channel: Literal["SMS", "WHATSAPP", "EMAIL"] = "SMS"
    scheduled_for: Optional[datetime] = None

class BroadcastJobUpdate(BaseModel):
    title: Optional[str] = None
    message_content: Optional[str] = None
    target_audience: Optional[str] = None
    target_class_id: Optional[UUID] = None
    target_branch_id: Optional[UUID] = None
    target_role: Optional[str] = None
    channel: Optional[str] = None
    scheduled_for: Optional[datetime] = None
    status: Optional[Literal["DRAFT"]] = None

class SMSProviderCreate(BaseModel):
    provider_name: str = Field(..., max_length=100)
    api_endpoint: Optional[str] = None
    api_key_encrypted: Optional[str] = None
    is_active: bool = Field(default=True)
    priority: int = Field(default=1)

class MessageTemplateCreate(BaseModel):
    name: str = Field(..., max_length=255)
    subject: Optional[str] = None
    content: str = Field(...)
    channel: str = Field(default="SMS")
    variables: Optional[List[str]] = None
    is_active: bool = Field(default=True)


# ==================== SMS Providers Endpoints ====================

@router.get("/sms-providers")
async def get_sms_providers(
    is_active: Optional[bool] = Query(True),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("super_admin"))
):
    """Get SMS providers"""
    from app.domain.entities.communications import SMSProvider
    
    query = select(SMSProvider)
    
    if is_active is not None:
        query = query.where(SMSProvider.is_active == is_active)
    
    query = query.order_by(SMSProvider.priority, SMSProvider.provider_name)
    
    result = await db.execute(query)
    providers = result.scalars().all()
    
    enriched_providers = []
    for provider in providers:
        enriched_providers.append({
            "id": str(provider.id),
            "provider_name": provider.provider_name,
            "api_endpoint": provider.api_endpoint,
            "is_active": provider.is_active,
            "priority": provider.priority,
            "created_at": provider.created_at.isoformat(),
            "updated_at": provider.updated_at.isoformat()
        })
    
    return success_response(enriched_providers)


@router.post("/sms-providers")
async def create_sms_provider(
    provider: SMSProviderCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("super_admin"))
):
    """Create a new SMS provider"""
    from app.domain.entities.communications import SMSProvider
    
    new_provider = SMSProvider(
        provider_name=provider.provider_name,
        api_endpoint=provider.api_endpoint,
        api_key_encrypted=provider.api_key_encrypted,
        is_active=provider.is_active,
        priority=provider.priority
    )
    db.add(new_provider)
    await db.commit()
    await db.refresh(new_provider)
    
    return success_response({
        "id": str(new_provider.id),
        "provider_name": new_provider.provider_name,
        "priority": new_provider.priority,
        "created_at": new_provider.created_at.isoformat()
    })


# ==================== Broadcast Jobs Endpoints ====================

@router.get("/broadcast-jobs")
async def get_broadcast_jobs(
    status: Optional[str] = Query(None), created_by: Optional[UUID] = Query(None),
    start_date: Optional[date] = Query(None), end_date: Optional[date] = Query(None),
    limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("communications.read")),
):
    return success_response(await broadcast_service.records(db, status, created_by, start_date, end_date, limit, offset))


@router.post("/broadcast-jobs")
async def create_broadcast_job(
    job: BroadcastJobCreate, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("communications.write")),
):
    return success_response(await broadcast_service.create(db, tenant, job), "Toplu ileti taslağı kaydedildi")


@router.put("/broadcast-jobs/{job_id}")
async def update_broadcast_job(
    job_id: UUID, job: BroadcastJobUpdate, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("communications.write")),
):
    current = await broadcast_service.get(db, job_id)
    config = await broadcast_service.configuration(db, current)
    values = {key: getattr(current, key) for key in ("title", "message_content", "target_audience",
        "target_class_id", "target_branch_id", "channel", "scheduled_for")}
    values["scheduled_for"] = broadcast_service.stored_schedule(current.scheduled_for)
    values["target_role"] = config.data.get("target_role") if config else None
    changes = job.model_dump(exclude_unset=True)
    changes.pop("status", None)
    values.update(changes)
    try:
        validated = BroadcastJobCreate.model_validate(values)
    except SchemaValidationError as exc:
        raise ValidationException("Toplu ileti alanları geçersiz") from exc
    return success_response(await broadcast_service.edit(db, tenant, current, validated))


@router.post("/broadcast-jobs/{job_id}/send")
async def send_broadcast_job(
    job_id: UUID, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("communications.write")),
):
    return success_response(await broadcast_service.send(db, tenant, job_id), "Toplu ileti gönderim kuyruğuna alındı")


@router.delete("/broadcast-jobs/{job_id}")
async def cancel_broadcast_job(
    job_id: UUID, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("communications.write")),
):
    return success_response(await broadcast_service.cancel(db, job_id), "Toplu ileti iptal edildi")

@router.get("/delivery-reports")
async def get_delivery_reports(
    broadcast_job_id: Optional[UUID] = Query(None), status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("communications.read")),
):
    from app.infrastructure.models.models import NotificationJob, NotificationRecipient
    query = select(NotificationRecipient, NotificationJob).join(NotificationJob,
        NotificationJob.id == NotificationRecipient.notification_job_id).where(NotificationJob.reference_type == "BROADCAST")
    if broadcast_job_id:
        await broadcast_service.get(db, broadcast_job_id)
        query = query.where(NotificationJob.reference_id == broadcast_job_id)
    if status:
        from app.infrastructure.models.models import NotificationStatus
        try:
            query = query.where(NotificationRecipient.status == NotificationStatus(status.upper()))
        except ValueError as exc:
            raise ValidationException("Geçersiz gönderim durumu") from exc
    rows = (await db.execute(query.order_by(NotificationRecipient.created_at.desc()).offset(offset).limit(limit))).all()
    return success_response([{"id": str(row.id), "broadcast_job_id": str(job.reference_id),
        "recipient_phone": row.recipient_address, "recipient_name": row.recipient_name, "status": row.status.value,
        "provider_response": row.provider_response, "error_message": row.error_message,
        "sent_at": row.sent_at.isoformat() if row.sent_at else None, "delivered_at": None,
        "created_at": row.created_at.isoformat()} for row, job in rows])


@router.get("/broadcast-jobs/{job_id}/delivery-summary")
async def get_delivery_summary(
    job_id: UUID, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("communications.read")),
):
    await broadcast_service.get(db, job_id)
    rows = await broadcast_service.delivery_rows(db, job_id)
    from app.infrastructure.models.models import NotificationStatus
    sent = sum(row.status == NotificationStatus.SENT for row in rows)
    failed = sum(row.status == NotificationStatus.FAILED for row in rows)
    pending = sum(row.status == NotificationStatus.PENDING for row in rows)
    return success_response({"broadcast_job_id": str(job_id), "total": len(rows), "sent": sent,
        "delivered": 0, "failed": failed, "pending": pending, "delivery_rate": 0})

@router.get("/message-templates")
async def get_message_templates(
    channel: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("communications.read"))
):
    """Get message templates"""
    from app.domain.entities.message_template import MessageTemplate
    
    query = select(MessageTemplate)
    
    if channel:
        query = query.where(MessageTemplate.channel == channel.upper())
    
    query = query.order_by(MessageTemplate.name).limit(limit).offset(offset)
    
    result = await db.execute(query)
    templates = result.scalars().all()
    
    enriched_templates = []
    for template in templates:
        enriched_templates.append({
            "id": str(template.id),
            "name": template.name,
            "subject": template.subject,
            "content": template.body_template,
            "channel": template.channel,
            "variables": [],
            "is_active": template.is_active,
            "created_at": template.created_at.isoformat()
        })
    
    return success_response(enriched_templates)


@router.post("/message-templates")
async def create_message_template(
    template: MessageTemplateCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("communications.write"))
):
    """Create a new message template"""
    from app.domain.entities.message_template import MessageTemplate
    
    new_template = MessageTemplate(
        name=template.name,
        subject=template.subject,
        organization_id=tenant.organization_id,
        code=f"custom-{uuid4()}",
        body_template=template.content,
        channel=template.channel.upper(),
        is_active=template.is_active
    )
    db.add(new_template)
    await db.commit()
    await db.refresh(new_template)
    
    return success_response({
        "id": str(new_template.id),
        "name": new_template.name,
        "channel": new_template.channel,
        "created_at": new_template.created_at.isoformat()
    })
