"""
Omnichannel Communication Module API
Handles SMS providers, broadcast jobs, and delivery reports
"""
from datetime import datetime, date
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.responses import success_response
from app.core.security import PermissionChecker, TenantContext
from app.domain.entities import User, Branch, Class

router = APIRouter(prefix="/api/communications", tags=["Communications"])


# ==================== Schemas ====================

class BroadcastJobCreate(BaseModel):
    title: str = Field(..., max_length=255)
    message_content: str = Field(..., description="Message content with variables like {ogrenci_adi}")
    target_audience: str = Field(..., description="ALL_PARENTS, BRANCH_PARENTS, CLASS_PARENTS, SINGLE_STUDENT, ALL_TEACHERS, ALL_STAFF")
    target_class_id: Optional[UUID] = None
    target_branch_id: Optional[UUID] = None
    target_role: Optional[str] = Field(None, description="OWNER, ADMIN, TEACHER, PARENT, STAFF")
    channel: str = Field(default="SMS", description="SMS, WHATSAPP, EMAIL")
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
    status: Optional[str] = Field(None, description="DRAFT, QUEUED, SENDING, COMPLETED, FAILED, CANCELLED")

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
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("communications.read"))
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
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("communications.write"))
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
    status: Optional[str] = Query(None),
    created_by: Optional[UUID] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("communications.read"))
):
    """Get broadcast jobs with filtering"""
    from app.domain.entities.communications import BroadcastJob
    
    query = select(BroadcastJob)
    
    conditions = []
    if status:
        conditions.append(BroadcastJob.status == status.upper())
    if created_by:
        conditions.append(BroadcastJob.created_by == created_by)
    if start_date:
        conditions.append(BroadcastJob.created_at >= start_date)
    if end_date:
        conditions.append(BroadcastJob.created_at <= end_date.replace(hour=23, minute=59, second=59))
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(BroadcastJob.created_at.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    jobs = result.scalars().all()
    
    enriched_jobs = []
    for job in jobs:
        # Get created by name
        created_by_name = None
        if job.created_by:
            user_result = await db.execute(
                select(User).where(User.id == job.created_by)
            )
            user = user_result.scalar_one_or_none()
            if user:
                created_by_name = f"{user.first_name} {user.last_name}"
        
        # Get target class name
        target_class_name = None
        if job.target_class_id:
            class_result = await db.execute(
                select(Class).where(Class.id == job.target_class_id)
            )
            cls = class_result.scalar_one_or_none()
            if cls:
                target_class_name = cls.name
        
        # Get target branch name
        target_branch_name = None
        if job.target_branch_id:
            branch_result = await db.execute(
                select(Branch).where(Branch.id == job.target_branch_id)
            )
            branch = branch_result.scalar_one_or_none()
            if branch:
                target_branch_name = branch.name
        
        enriched_jobs.append({
            "id": str(job.id),
            "title": job.title,
            "message_content": job.message_content,
            "target_audience": job.target_audience,
            "target_class_id": str(job.target_class_id) if job.target_class_id else None,
            "target_class_name": target_class_name,
            "target_branch_id": str(job.target_branch_id) if job.target_branch_id else None,
            "target_branch_name": target_branch_name,
            "channel": job.channel,
            "scheduled_for": job.scheduled_for.isoformat() if job.scheduled_for else None,
            "status": job.status,
            "total_recipients": job.total_recipients,
            "sent_count": job.sent_count,
            "failed_count": job.failed_count,
            "created_by": str(job.created_by) if job.created_by else None,
            "created_by_name": created_by_name,
            "created_at": job.created_at.isoformat(),
            "sent_at": job.sent_at.isoformat() if job.sent_at else None
        })
    
    return success_response(enriched_jobs)


@router.post("/broadcast-jobs")
async def create_broadcast_job(
    job: BroadcastJobCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("communications.write"))
):
    """Create a new broadcast job"""
    from app.domain.entities.communications import BroadcastJob

    # Calculate recipients count based on target audience
    total_recipients = 0
    if job.target_audience == "ALL_PARENTS":
        total_recipients = 100  # Placeholder
    elif job.target_audience == "CLASS_PARENTS" and job.target_class_id:
        total_recipients = 30  # Placeholder
    elif job.target_audience == "BRANCH_PARENTS" and job.target_branch_id:
        total_recipients = 50  # Placeholder
    elif job.target_audience == "ALL_TEACHERS":
        total_recipients = 25  # Placeholder
    elif job.target_audience == "ALL_STAFF":
        total_recipients = 40  # Placeholder

    new_job = BroadcastJob(
        title=job.title,
        message_content=job.message_content,
        target_audience=job.target_audience.upper(),
        target_class_id=job.target_class_id,
        target_branch_id=job.target_branch_id,
        target_role=job.target_role,
        channel=job.channel.upper(),
        scheduled_for=job.scheduled_for,
        status="DRAFT",
        total_recipients=total_recipients,
        sent_count=0,
        failed_count=0,
        created_by=None  # Will be set from current user context
    )
    db.add(new_job)
    await db.commit()
    await db.refresh(new_job)

    return success_response({
        "id": str(new_job.id),
        "title": new_job.title,
        "status": new_job.status,
        "total_recipients": new_job.total_recipients,
        "created_at": new_job.created_at.isoformat()
    })


@router.put("/broadcast-jobs/{job_id}")
async def update_broadcast_job(
    job_id: UUID,
    job: BroadcastJobUpdate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("communications.write"))
):
    """Update a broadcast job"""
    from app.domain.entities.communications import BroadcastJob
    
    result = await db.execute(
        select(BroadcastJob).where(BroadcastJob.id == job_id)
    )
    existing_job = result.scalar_one_or_none()
    
    if not existing_job:
        raise HTTPException(status_code=404, detail="Broadcast job not found")
    
    if job.title:
        existing_job.title = job.title
    if job.message_content:
        existing_job.message_content = job.message_content
    if job.target_audience:
        existing_job.target_audience = job.target_audience.upper()
    if job.target_class_id:
        existing_job.target_class_id = job.target_class_id
    if job.target_branch_id:
        existing_job.target_branch_id = job.target_branch_id
    if job.target_role:
        existing_job.target_role = job.target_role
    if job.channel:
        existing_job.channel = job.channel.upper()
    if job.scheduled_for:
        existing_job.scheduled_for = job.scheduled_for
    if job.status:
        existing_job.status = job.status.upper()
    
    await db.commit()
    
    return success_response({
        "id": str(existing_job.id),
        "status": existing_job.status,
        "updated_at": existing_job.updated_at.isoformat()
    })


@router.post("/broadcast-jobs/{job_id}/send")
async def send_broadcast_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("communications.write"))
):
    """Send a broadcast job (queue for processing)"""
    from app.domain.entities.communications import BroadcastJob, DeliveryReport
    
    result = await db.execute(
        select(BroadcastJob).where(BroadcastJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Broadcast job not found")
    
    if job.status != "DRAFT":
        raise HTTPException(status_code=400, detail="Job can only be sent from DRAFT status")
    
    # Update job status
    job.status = "QUEUED"
    
    # TODO: Queue job for background processing
    # For now, we'll simulate sending
    job.status = "SENDING"
    job.sent_at = datetime.utcnow()
    
    # Create delivery reports (simplified)
    # In real implementation, would get actual recipient list
    for i in range(job.total_recipients):
        new_report = DeliveryReport(
            broadcast_job_id=job.id,
            recipient_phone=f"+9055555555{i:04d}",
            recipient_name=f"Parent {i+1}",
            status="SENT",
            sent_at=datetime.utcnow()
        )
        db.add(new_report)
    
    job.sent_count = job.total_recipients
    job.status = "COMPLETED"
    
    await db.commit()
    
    return success_response({
        "id": str(job.id),
        "status": job.status,
        "sent_count": job.sent_count,
        "sent_at": job.sent_at.isoformat()
    })


@router.delete("/broadcast-jobs/{job_id}")
async def cancel_broadcast_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("communications.write"))
):
    """Cancel a broadcast job"""
    from app.domain.entities.communications import BroadcastJob
    
    result = await db.execute(
        select(BroadcastJob).where(BroadcastJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Broadcast job not found")
    
    if job.status in ["COMPLETED", "SENDING"]:
        raise HTTPException(status_code=400, detail="Cannot cancel completed or sending jobs")
    
    job.status = "CANCELLED"
    
    await db.commit()
    
    return success_response({
        "id": str(job.id),
        "status": "CANCELLED",
        "message": "Broadcast job cancelled successfully"
    })


# ==================== Delivery Reports Endpoints ====================

@router.get("/delivery-reports")
async def get_delivery_reports(
    broadcast_job_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("communications.read"))
):
    """Get delivery reports with filtering"""
    from app.domain.entities.communications import DeliveryReport
    
    query = select(DeliveryReport)
    
    conditions = []
    if broadcast_job_id:
        conditions.append(DeliveryReport.broadcast_job_id == broadcast_job_id)
    if status:
        conditions.append(DeliveryReport.status == status.upper())
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(DeliveryReport.created_at.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    reports = result.scalars().all()
    
    enriched_reports = []
    for report in reports:
        enriched_reports.append({
            "id": str(report.id),
            "broadcast_job_id": str(report.broadcast_job_id),
            "recipient_phone": report.recipient_phone,
            "recipient_name": report.recipient_name,
            "status": report.status,
            "provider_response": report.provider_response,
            "error_message": report.error_message,
            "sent_at": report.sent_at.isoformat() if report.sent_at else None,
            "delivered_at": report.delivered_at.isoformat() if report.delivered_at else None,
            "created_at": report.created_at.isoformat()
        })
    
    return success_response(enriched_reports)


@router.get("/broadcast-jobs/{job_id}/delivery-summary")
async def get_delivery_summary(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("communications.read"))
):
    """Get delivery summary for a broadcast job"""
    from app.domain.entities.communications import DeliveryReport
    
    result = await db.execute(
        select(DeliveryReport).where(DeliveryReport.broadcast_job_id == job_id)
    )
    reports = result.scalars().all()
    
    # Calculate summary
    total = len(reports)
    sent = sum(1 for r in reports if r.status == "SENT")
    delivered = sum(1 for r in reports if r.status == "DELIVERED")
    failed = sum(1 for r in reports if r.status in ["FAILED", "BOUNCED"])
    pending = sum(1 for r in reports if r.status == "PENDING")
    
    return success_response({
        "broadcast_job_id": str(job_id),
        "total": total,
        "sent": sent,
        "delivered": delivered,
        "failed": failed,
        "pending": pending,
        "delivery_rate": (delivered / total * 100) if total > 0 else 0
    })


# ==================== Message Templates Endpoints ====================

@router.get("/message-templates")
async def get_message_templates(
    channel: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
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
            "content": template.content,
            "channel": template.channel,
            "variables": template.variables,
            "is_active": template.is_active,
            "created_at": template.created_at.isoformat()
        })
    
    return success_response(enriched_templates)


@router.post("/message-templates")
async def create_message_template(
    template: MessageTemplateCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("communications.write"))
):
    """Create a new message template"""
    from app.domain.entities.message_template import MessageTemplate
    
    new_template = MessageTemplate(
        name=template.name,
        subject=template.subject,
        content=template.content,
        channel=template.channel.upper(),
        variables=template.variables or [],
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
