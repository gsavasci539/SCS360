from uuid import UUID
from typing import Optional
from datetime import datetime
from pydantic import BaseModel

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_tenant_context
from app.core.permissions import PermissionChecker
from app.core.responses import success_response, paginate
from app.core.tenant import TenantContext
from app.domain.entities.user import User
from app.infrastructure.repositories.base import BaseRepository

router = APIRouter(prefix="/api/parent-notices", tags=["Parent Notices"])


class ParentNoticeCreate(BaseModel):
    student_id: UUID
    type: str
    description: Optional[str] = None


class ParentNoticeUpdate(BaseModel):
    type: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


# Simple in-memory model for now (can be replaced with proper entity later)
class ParentNotice:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.student_id = kwargs.get('student_id')
        self.student_name = kwargs.get('student_name', 'Bilinmeyen Öğrenci')
        self.type = kwargs.get('type')
        self.description = kwargs.get('description')
        self.status = kwargs.get('status', 'pending')
        self.organization_id = kwargs.get('organization_id')
        self.created_at = kwargs.get('created_at', datetime.utcnow())
        self.created_by = kwargs.get('created_by')


def parent_notice_to_dict(notice: ParentNotice) -> dict:
    return {
        "id": str(notice.id) if notice.id else None,
        "student_name": notice.student_name,
        "type": notice.type,
        "description": notice.description,
        "status": notice.status,
        "created_at": notice.created_at.isoformat() if notice.created_at else None,
    }


# Temporary storage (in production, use database)
_parent_notices_storage = []


@router.get("")
async def list_parent_notices(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    search: Optional[str] = None,
    tenant: TenantContext = Depends(PermissionChecker("parent_notices.read")),
    db: AsyncSession = Depends(get_db),
):
    # Filter by organization
    filtered = [n for n in _parent_notices_storage if n.organization_id == tenant.organization_id]
    
    if search:
        filtered = [n for n in filtered if search.lower() in n.student_name.lower() or (n.description and search.lower() in n.description.lower())]
    
    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size
    items = filtered[start:end]
    
    return success_response(paginate([parent_notice_to_dict(n) for n in items], total, page, page_size))


@router.post("")
async def create_parent_notice(
    body: ParentNoticeCreate,
    tenant: TenantContext = Depends(PermissionChecker("parent_notices.write")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Get student name (simplified - in production, query from student table)
    student_name = "Öğrenci"  # Placeholder
    
    notice = ParentNotice(
        student_id=body.student_id,
        student_name=student_name,
        type=body.type,
        description=body.description,
        organization_id=tenant.organization_id,
        created_by=tenant.user_id,
        created_at=datetime.utcnow()
    )
    
    # Generate simple ID
    import uuid
    notice.id = uuid.uuid4()
    
    _parent_notices_storage.append(notice)
    
    return success_response(parent_notice_to_dict(notice), "Veli talebi oluşturuldu")


@router.get("/{notice_id}")
async def get_parent_notice(
    notice_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("parent_notices.read")),
    db: AsyncSession = Depends(get_db),
):
    notice = next((n for n in _parent_notices_storage if str(n.id) == str(notice_id) and n.organization_id == tenant.organization_id), None)
    
    if not notice:
        return success_response(None, "Veli talebi bulunamadı", success=False)
    
    return success_response(parent_notice_to_dict(notice))


@router.put("/{notice_id}")
async def update_parent_notice(
    notice_id: UUID,
    body: ParentNoticeUpdate,
    tenant: TenantContext = Depends(PermissionChecker("parent_notices.write")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    notice = next((n for n in _parent_notices_storage if str(n.id) == str(notice_id) and n.organization_id == tenant.organization_id), None)
    
    if not notice:
        return success_response(None, "Veli talebi bulunamadı", success=False)
    
    if body.type:
        notice.type = body.type
    if body.description is not None:
        notice.description = body.description
    if body.status:
        notice.status = body.status
    
    return success_response(parent_notice_to_dict(notice), "Veli talebi güncellendi")


@router.delete("/{notice_id}")
async def delete_parent_notice(
    notice_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("parent_notices.write")),
    db: AsyncSession = Depends(get_db),
):
    global _parent_notices_storage
    _parent_notices_storage = [n for n in _parent_notices_storage if str(n.id) != str(notice_id)]
    
    return success_response(message="Veli talebi silindi")
