"""Private student conversation attachments shared by teacher and admin routes."""
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services import student_chat_messages, teacher_chat_service
from app.core.database import get_db
from app.core.permissions import PermissionChecker
from app.core.responses import paginate, success_response
from app.core.tenant import TenantContext
from app.infrastructure.storage.message_attachments import message_upload

router = APIRouter()


@router.get("/chat-branches", dependencies=[Depends(PermissionChecker("students.read"))])
async def chat_branches(
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("messaging.read")),
):
    return success_response(await teacher_chat_service.contact_branches(db, tenant))


@router.get("/chat-contacts")
async def chat_contacts(
    branch_id: UUID | None = None,
    search: str = Query("", max_length=120),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("messaging.read")),
    student_access: TenantContext = Depends(PermissionChecker("students.read")),
):
    rows, total = await teacher_chat_service.contacts(db, tenant, branch_id, page, page_size, search)
    return success_response(paginate(rows, total, page, page_size))


@router.post("/chat/{student_id}/send-file")
async def send_chat_file(
    student_id: UUID,
    file: UploadFile = File(),
    request_id: UUID = Form(),
    message: str = Form(default="", max_length=10000),
    parent_id: UUID | None = None,
    branch_id: UUID | None = None,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("messaging.send")),
):
    upload = await message_upload(file)
    return success_response(await teacher_chat_service.send(db, tenant, student_id, message, parent_id,
        request_id, upload, branch_id=branch_id))


@router.get("/chat/{student_id}/sent/{message_id}")
async def get_chat_receipt(
    student_id: UUID,
    message_id: UUID,
    parent_id: UUID | None = None,
    branch_id: UUID | None = None,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("messaging.send")),
):
    _, _, thread = await teacher_chat_service.thread(db, tenant, student_id, parent_id, branch_id=branch_id)
    return success_response(await student_chat_messages.receipt(db, thread, tenant.user_id, message_id))


@router.get("/chat/{student_id}/attachments/{message_id}")
async def download_chat_attachment(
    student_id: UUID,
    message_id: UUID,
    parent_id: UUID | None = None,
    branch_id: UUID | None = None,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("messaging.read")),
):
    _, _, thread = await teacher_chat_service.thread(db, tenant, student_id, parent_id, branch_id=branch_id)
    return await student_chat_messages.download(db, thread, message_id)
