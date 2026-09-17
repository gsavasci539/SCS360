from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from app.application.schemas import AnnouncementCreate, AnnouncementUpdate, AnnouncementResponse
from app.repositories import AnnouncementRepository
from app.core.database import get_db
from app.core.dependencies import get_current_user, get_tenant_context
from app.core.permissions import require_permission, PermissionChecker
from app.core.responses import success_response
from app.domain.entities.user import User
from app.core.tenant import TenantContext

router = APIRouter(prefix="/api/announcements", tags=["Announcements"])


@router.post("", response_model=AnnouncementResponse)
@require_permission("announcements.create")
async def create_announcement(
    announcement: AnnouncementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = AnnouncementRepository()
    announcement_data = announcement.model_dump()
    announcement_data["created_by"] = current_user.id
    announcement_data["organization_id"] = current_user.organization_id
    
    db_announcement = await repo.create(db, announcement_data)
    
    # TODO: Create notification jobs for recipients
    
    return success_response(db_announcement, "Duyuru oluşturuldu")


@router.get("", response_model=list[AnnouncementResponse])
async def list_announcements(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    branch_id: Optional[UUID] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("announcements.read"))
):
    repo = AnnouncementRepository()
    
    if branch_id:
        announcements = await repo.get_by_branch(db, branch_id, skip, limit)
    elif status:
        announcements = await repo.get_by_status(db, tenant.organization_id, status)
    else:
        announcements = await repo.get_by_organization(db, tenant.organization_id, skip, limit)
    
    return success_response(announcements)


@router.get("/{announcement_id}", response_model=AnnouncementResponse)
async def get_announcement(
    announcement_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("announcements.read"))
):
    repo = AnnouncementRepository()
    announcement = await repo.get(db, announcement_id)
    
    if not announcement or announcement.organization_id != tenant.organization_id:
        return success_response(None, "Duyuru bulunamadı", success=False)
    
    return success_response(announcement)


@router.put("/{announcement_id}", response_model=AnnouncementResponse)
async def update_announcement(
    announcement_id: UUID,
    announcement: AnnouncementUpdate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("announcements.write"))
):
    repo = AnnouncementRepository()
    db_announcement = await repo.get(db, announcement_id)
    
    if not db_announcement or db_announcement.organization_id != tenant.organization_id:
        return success_response(None, "Duyuru bulunamadı", success=False)
    
    announcement_data = announcement.model_dump(exclude_unset=True)
    announcement_data["updated_by"] = tenant.user_id
    
    updated_announcement = await repo.update(db, db_announcement, announcement_data)
    return success_response(updated_announcement, "Duyuru güncellendi")


@router.delete("/{announcement_id}")
async def delete_announcement(
    announcement_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("announcements.write"))
):
    repo = AnnouncementRepository()
    db_announcement = await repo.get(db, announcement_id)
    
    if not db_announcement or db_announcement.organization_id != tenant.organization_id:
        return success_response(None, "Duyuru bulunamadı", success=False)
    
    await repo.delete(db, announcement_id)
    return success_response(message="Duyuru silindi")


@router.post("/{announcement_id}/send")
async def send_announcement(
    announcement_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = AnnouncementRepository()
    db_announcement = await repo.get(db, announcement_id)
    
    if not db_announcement or db_announcement.organization_id != current_user.organization_id:
        return success_response(None, "Duyuru bulunamadı", success=False)
    
    # TODO: Send announcement to recipients via notification jobs
    
    return success_response(message="Duyuru gönderildi")
