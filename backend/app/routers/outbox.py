from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services import outbox_service
from app.core.database import get_db
from app.core.permissions import PermissionChecker
from app.core.responses import paginate, success_response
from app.core.tenant import TenantContext
from app.infrastructure.models.models import NotificationChannel, NotificationStatus

router = APIRouter(prefix="/api/outbox", tags=["Outbox"])


@router.get("")
@router.get("/")
async def list_outbox_messages(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    search: str | None = None, channel: NotificationChannel | None = None, status: NotificationStatus | None = None,
    branch_id: UUID | None = None,
    tenant: TenantContext = Depends(PermissionChecker("outbox.read", "notification.read")),
    db: AsyncSession = Depends(get_db, scope="function")):
    total = await outbox_service.count(db, tenant, channel, status, search, branch_id)
    rows = await outbox_service.records(db, tenant, channel, status, search, branch_id=branch_id,
        limit=page_size, offset=(page - 1) * page_size)
    return success_response(paginate(rows, total, page, page_size))


@router.get("/{message_id}")
async def get_outbox_message(message_id: UUID, branch_id: UUID | None = None,
    tenant: TenantContext = Depends(PermissionChecker("outbox.read", "notification.read")),
    db: AsyncSession = Depends(get_db, scope="function")):
    return success_response(outbox_service.serialize(*(await outbox_service.get(db, tenant, message_id, branch_id))))


@router.post("/retry/{message_id}")
async def retry_outbox_message(message_id: UUID, branch_id: UUID | None = None,
    tenant: TenantContext = Depends(PermissionChecker("notification.write")),
    db: AsyncSession = Depends(get_db, scope="function")):
    return success_response(await outbox_service.retry(db, tenant, message_id, branch_id), "İleti yeniden gönderim kuyruğuna alındı")


@router.delete("/{message_id}")
async def delete_outbox_message(message_id: UUID, branch_id: UUID | None = None,
    tenant: TenantContext = Depends(PermissionChecker("notification.write")),
    db: AsyncSession = Depends(get_db, scope="function")):
    await outbox_service.remove(db, tenant, message_id, branch_id)
    return success_response(message="Gönderim kaydı silindi")
