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
    tenant: TenantContext = Depends(PermissionChecker("outbox.read", "notification.read")),
    db: AsyncSession = Depends(get_db, scope="function")):
    rows = await outbox_service.records(db, tenant, channel, status, search)
    return success_response(paginate(rows[(page - 1) * page_size:page * page_size], len(rows), page, page_size))


@router.get("/{message_id}")
async def get_outbox_message(message_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("outbox.read", "notification.read")),
    db: AsyncSession = Depends(get_db, scope="function")):
    return success_response(outbox_service.serialize(*(await outbox_service.get(db, tenant, message_id))))


@router.post("/retry/{message_id}")
async def retry_outbox_message(message_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("notification.write")),
    db: AsyncSession = Depends(get_db, scope="function")):
    return success_response(await outbox_service.retry(db, tenant, message_id), "İleti yeniden gönderim kuyruğuna alındı")


@router.delete("/{message_id}")
async def delete_outbox_message(message_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("notification.write")),
    db: AsyncSession = Depends(get_db, scope="function")):
    from app.core.exceptions import ConflictException
    from datetime import UTC, datetime
    recipient, job = await outbox_service.get(db, tenant, message_id)
    if job.locked_until and job.locked_until.replace(tzinfo=UTC) > datetime.now(UTC):
        raise ConflictException("İşlenen gönderim silinemez")
    await db.delete(recipient)
    return success_response(message="Gönderim kaydı silindi")
