"""Private student conversation attachments shared by teacher and admin routes."""
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services import student_chat_messages, teacher_chat_service
from app.core.database import get_db
from app.core.permissions import PermissionChecker
from app.core.responses import success_response
from app.core.tenant import TenantContext
from app.infrastructure.storage.message_attachments import message_upload

router = APIRouter()


@router.post("/chat/{student_id}/send-file")
async def send_chat_file(
    student_id: UUID,
    file: UploadFile = File(),
    request_id: UUID = Form(),
    message: str = Form(default="", max_length=10000),
    parent_id: UUID | None = None,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("messaging.send")),
):
    upload = await message_upload(file)
    return success_response(await teacher_chat_service.send(db, tenant, student_id, message, parent_id,
        request_id, upload))


@router.get("/chat/{student_id}/sent/{message_id}")
async def get_chat_receipt(
    student_id: UUID,
    message_id: UUID,
    parent_id: UUID | None = None,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("messaging.send")),
):
    _, _, thread = await teacher_chat_service.thread(db, tenant, student_id, parent_id)
    return success_response(await student_chat_messages.receipt(db, thread, tenant.user_id, message_id))


@router.get("/chat/{student_id}/attachments/{message_id}")
async def download_chat_attachment(
    student_id: UUID,
    message_id: UUID,
    parent_id: UUID | None = None,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("messaging.read")),
):
    _, _, thread = await teacher_chat_service.thread(db, tenant, student_id, parent_id)
    return await student_chat_messages.download(db, thread, message_id)
