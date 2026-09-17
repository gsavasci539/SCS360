from html import escape
from io import BytesIO
from uuid import UUID
from zipfile import BadZipFile, ZipFile

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import NotFoundException, ValidationException
from app.core.permissions import PermissionChecker
from app.core.responses import success_response
from app.core.tenant import TenantContext
from app.infrastructure.models.models import (
    Branch,
    FileCategory,
    NotificationChannel,
    NotificationJob,
    NotificationRecipient,
    Organization,
    Parent,
    Payment,
    Receipt,
    Student,
    StudentFile,
    StudentParent,
    User,
)
from app.infrastructure.pdf.receipt_pdf import generate_receipt_pdf
from app.infrastructure.repositories.base import BaseRepository
from app.infrastructure.storage.local_storage import LocalFileStorage

router = APIRouter(tags=["Files & Receipts"])
settings = get_settings()


def _validate_upload(file: UploadFile, content: bytes) -> None:
    if len(content) > settings.max_upload_size_bytes:
        raise ValidationException(f"Dosya boyutu {settings.MAX_UPLOAD_SIZE_MB}MB limitini aşıyor")
    ext = (file.filename or "").rsplit(".", 1)[-1].lower() if file.filename else ""
    if ext not in settings.allowed_file_types_list:
        raise ValidationException(f"İzin verilmeyen dosya türü: {ext}")
    signatures = {
        "pdf": (b"%PDF-",),
        "jpg": (b"\xff\xd8\xff",),
        "jpeg": (b"\xff\xd8\xff",),
        "png": (b"\x89PNG\r\n\x1a\n",),
    }
    if ext in signatures and not content.startswith(signatures[ext]):
        raise ValidationException("Dosya içeriği uzantısıyla eşleşmiyor")
    if ext == "docx":
        try:
            with ZipFile(BytesIO(content)) as archive:
                names = set(archive.namelist())
        except BadZipFile as exc:
            raise ValidationException("Geçersiz DOCX dosyası") from exc
        if "[Content_Types].xml" not in names or "word/document.xml" not in names:
            raise ValidationException("Geçersiz DOCX dosyası")


async def _build_receipt_context(db: AsyncSession, receipt: Receipt) -> dict:
    payment = (
        await db.execute(select(Payment).where(Payment.id == receipt.payment_id))
    ).scalar_one_or_none()
    
    # Use receipt.student_id if payment not found
    student_id = payment.student_id if payment else receipt.student_id
    student = (
        await db.execute(select(Student).where(Student.id == student_id))
    ).scalar_one_or_none()
    
    org = (
        await db.execute(select(Organization).where(Organization.id == receipt.organization_id))
    ).scalar_one_or_none()
    
    # Get branch from receipt or student
    branch = None
    if receipt.branch_id:
        branch_result = await db.execute(
            select(Branch).where(Branch.id == str(receipt.branch_id))
        )
        branch = branch_result.scalar_one_or_none()
    if not branch and student and student.branch_id:
        branch_result = await db.execute(
            select(Branch).where(Branch.id == str(student.branch_id))
        )
        branch = branch_result.scalar_one_or_none()
    
    receiver = None
    if payment and payment.received_by:
        receiver = (
            await db.execute(select(User).where(User.id == payment.received_by))
        ).scalar_one_or_none()
    elif receipt.issued_by:
        receiver = (
            await db.execute(select(User).where(User.id == receipt.issued_by))
        ).scalar_one_or_none()

    parent_name = ""
    if student:
        parent_result = await db.execute(
            select(Parent)
            .join(StudentParent, StudentParent.parent_id == Parent.id)
            .where(StudentParent.student_id == student.id, StudentParent.is_primary.is_(True))
            .limit(1)
        )
        parent = parent_result.scalar_one_or_none()
        if parent:
            parent_name = f"{parent.first_name} {parent.last_name}"

    # Handle payment_method - could be enum or string
    payment_method_str = ""
    if payment:
        if hasattr(payment.payment_method, 'value'):
            payment_method_str = payment.payment_method.value
        else:
            payment_method_str = str(payment.payment_method)
    elif receipt:
        payment_method_str = "Nakit"  # Default fallback

    # Handle amount
    amount_str = str(payment.amount) if payment else "0.00"

    return {
        "organization_name": org.legal_name if org and org.legal_name else (org.name if org else "Okul Yönetim Sistemi"),
        "branch_name": branch.name if branch else "",
        "receipt_number": receipt.receipt_number,
        "issued_at": receipt.issued_at.strftime("%d.%m.%Y %H:%M") if receipt.issued_at else "",
        "student_name": f"{student.first_name} {student.last_name}" if student else "",
        "student_number": student.student_number if student else "",
        "parent_name": parent_name,
        "amount": amount_str,
        "payment_method": payment_method_str,
        "remaining_debt": str(receipt.remaining_debt) if receipt.remaining_debt is not None else "0.00",
        "received_by": f"{receiver.first_name} {receiver.last_name}" if receiver else "Sistem",
    }


@router.get("/api/students/{student_id}/files")
async def list_student_files(
    student_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("student.read")),
    db: AsyncSession = Depends(get_db),
):
    repo = BaseRepository(db, tenant)
    await repo.get_by_id(student_id, Student)
    result = await db.execute(
        select(StudentFile)
        .where(
            StudentFile.student_id == student_id,
            StudentFile.deleted_at.is_(None),
        )
        .order_by(StudentFile.created_at.desc())
    )
    files = result.scalars().all()
    return success_response(
        [
            {
                "id": str(f.id),
                "category": f.category.value,
                "file_name": f.file_name,
                "original_name": f.original_name,
                "mime_type": f.mime_type,
                "file_size": f.file_size,
                "created_at": f.created_at.isoformat(),
            }
            for f in files
        ]
    )


@router.post("/api/students/{student_id}/files")
async def upload_student_file(
    student_id: UUID,
    category: str = Form("OTHER"),
    file: UploadFile = File(...),
    tenant: TenantContext = Depends(PermissionChecker("student.write")),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = BaseRepository(db, tenant)
    student = await repo.get_by_id(student_id, Student)
    content = await file.read()
    _validate_upload(file, content)

    storage = LocalFileStorage()
    subfolder = f"students/{student_id}"
    storage_path = await storage.save_async(content, file.filename or "file", subfolder)

    student_file = StudentFile(
        organization_id=student.organization_id,
        branch_id=student.branch_id,
        student_id=student_id,
        category=FileCategory(category),
        file_name=storage_path.split("/")[-1],
        original_name=file.filename or "file",
        mime_type=file.content_type or "application/octet-stream",
        file_size=len(content),
        storage_path=storage_path,
        uploaded_by=user.id,
    )
    db.add(student_file)
    await db.flush()
    return success_response({"id": str(student_file.id)}, "Dosya yüklendi")


@router.delete("/api/students/{student_id}/files/{file_id}")
async def delete_student_file(
    student_id: UUID,
    file_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("student.write")),
    db: AsyncSession = Depends(get_db),
):
    repo = BaseRepository(db, tenant)
    await repo.get_by_id(student_id, Student)
    result = await db.execute(
        select(StudentFile).where(
            StudentFile.id == file_id,
            StudentFile.student_id == student_id,
            StudentFile.deleted_at.is_(None),
        )
    )
    student_file = result.scalar_one_or_none()
    if not student_file:
        raise NotFoundException("Dosya bulunamadı")
    await repo.soft_delete(student_file)
    return success_response(message="Dosya silindi")


@router.get("/api/students/{student_id}/files/{file_id}/download")
async def download_student_file(
    student_id: UUID,
    file_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("student.read")),
    db: AsyncSession = Depends(get_db),
):
    repo = BaseRepository(db, tenant)
    await repo.get_by_id(student_id, Student)
    result = await db.execute(
        select(StudentFile).where(
            StudentFile.id == file_id,
            StudentFile.student_id == student_id,
            StudentFile.deleted_at.is_(None),
        )
    )
    student_file = result.scalar_one_or_none()
    if not student_file:
        raise NotFoundException("Dosya bulunamadı")
    storage = LocalFileStorage()
    full_path = storage.get_full_path(student_file.storage_path)
    if not full_path.exists():
        raise NotFoundException("Dosya diskte bulunamadı")
    return FileResponse(
        path=str(full_path),
        filename=student_file.original_name,
        media_type=student_file.mime_type,
    )


@router.get("/api/receipts")
async def list_receipts(
    student_id: UUID | None = None,
    skip: int = 0,
    limit: int = 100,
    tenant: TenantContext = Depends(PermissionChecker("receipt.read")),
    db: AsyncSession = Depends(get_db),
):
    """List receipts with optional student filter"""
    from app.repositories.receipt_repository import ReceiptRepository
    
    repo = ReceiptRepository()
    
    if student_id:
        receipts = await repo.get_by_student(db, student_id, skip, limit)
    else:
        receipts = await repo.get_by_organization(db, tenant.organization_id, skip, limit)
    
    return success_response([
        {
            "id": str(r.id),
            "receipt_number": r.receipt_number,
            "student_id": str(r.student_id),
            "payment_id": str(r.payment_id),
            "issued_at": r.issued_at.isoformat(),
            "remaining_debt": str(r.remaining_debt),
            "status": r.status.value if r.status else None,
        }
        for r in receipts
    ])


@router.get("/api/receipts/{receipt_id}")
async def get_receipt(
    receipt_id: str,
    tenant: TenantContext = Depends(PermissionChecker("receipt.read")),
    db: AsyncSession = Depends(get_db),
):
    """Get receipt details"""
    # Try with hyphens first
    receipt_result = await db.execute(
        select(Receipt).where(Receipt.id == receipt_id)
    )
    receipt = receipt_result.scalar_one_or_none()
    
    # If not found, try without hyphens
    if not receipt:
        receipt_id_clean = receipt_id.replace("-", "")
        receipt_result = await db.execute(
            select(Receipt).where(Receipt.id == receipt_id_clean)
        )
        receipt = receipt_result.scalar_one_or_none()
    
    if not receipt:
        raise NotFoundException("Makbuz bulunamadı")
    
    context = await _build_receipt_context(db, receipt)
    
    return success_response({
        "id": str(receipt.id),
        "receipt_number": receipt.receipt_number,
        "student_id": str(receipt.student_id),
        "payment_id": str(receipt.payment_id),
        "issued_at": receipt.issued_at.isoformat(),
        "remaining_debt": str(receipt.remaining_debt),
        "status": receipt.status.value if receipt.status else None,
        "pdf_path": receipt.pdf_path,
        **context
    })


@router.get("/api/receipts/{receipt_id}/pdf")
async def download_receipt_pdf(
    receipt_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("receipt.read")),
    db: AsyncSession = Depends(get_db),
):
    receipt_result = await db.execute(
        select(Receipt).where(Receipt.id == receipt_id)
    )
    receipt = receipt_result.scalar_one_or_none()
    
    if not receipt:
        raise NotFoundException("Makbuz bulunamadı")
    
    context = await _build_receipt_context(db, receipt)
    pdf_bytes = generate_receipt_pdf(context)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{receipt.receipt_number}.pdf"'},
    )


@router.get("/api/receipts/{receipt_id}/print")
async def print_receipt(
    receipt_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("receipt.read")),
    db: AsyncSession = Depends(get_db),
):
    receipt_result = await db.execute(
        select(Receipt).where(Receipt.id == receipt_id)
    )
    receipt = receipt_result.scalar_one_or_none()
    
    if not receipt:
        raise NotFoundException("Makbuz bulunamadı")
    
    raw_ctx = await _build_receipt_context(db, receipt)
    ctx = {key: escape(str(value), quote=True) for key, value in raw_ctx.items()}
    
    receipt_html = f"""
    <div class="receipt-header">
        <h3>{ctx['organization_name']}</h3>
        <span class="copy-type">VELİ KOPYASI</span>
    </div>
    <div class="receipt-title">
        <h2>TAHSİLAT MAKBUZU</h2>
    </div>
    <div class="receipt-info">
        <div class="info-row">
            <span class="label">Makbuz No:</span>
            <span class="value">{ctx['receipt_number']}</span>
        </div>
        <div class="info-row">
            <span class="label">Tarih:</span>
            <span class="value">{ctx['issued_at']}</span>
        </div>
    </div>
    <div class="receipt-details">
        <div class="detail-row">
            <span class="label">Şube:</span>
            <span class="value">{ctx['branch_name']}</span>
        </div>
        <div class="detail-row">
            <span class="label">Öğrenci:</span>
            <span class="value">{ctx['student_name']}</span>
        </div>
        <div class="detail-row">
            <span class="label">Veli:</span>
            <span class="value">{ctx['parent_name']}</span>
        </div>
        <div class="detail-row">
            <span class="label">Ödeme Tutarı:</span>
            <span class="value">{ctx['amount']} TL</span>
        </div>
        <div class="detail-row">
            <span class="label">Ödeme Yöntemi:</span>
            <span class="value">{ctx['payment_method']}</span>
        </div>
        <div class="detail-row">
            <span class="label">Kalan Borç:</span>
            <span class="value">{ctx['remaining_debt']} TL</span>
        </div>
        <div class="detail-row">
            <span class="label">Tahsilatı Alan:</span>
            <span class="value">{ctx['received_by']}</span>
        </div>
    </div>
    <div class="receipt-footer">
        <p>Bu belge resmi makbuz niteliğindedir.</p>
    </div>
    """
    
    management_html = receipt_html.replace("VELİ KOPYASI", "YÖNETİM KOPYASI")
    management_html = management_html.replace(
        '<div class="receipt-footer">\n        <p>Bu belge resmi makbuz niteliğindedir.</p>\n    </div>',
        '<div class="receipt-footer">\n        <p>Bu belge resmi makbuz niteliğindedir.</p>\n        <div class="signature-area">\n            <span class="label">İmza:</span>\n            <div class="signature-line"></div>\n        </div>\n    </div>'
    )
    
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Makbuz {ctx['receipt_number']}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ 
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    margin: 0;
    padding: 20px;
    min-height: 100vh;
}}
.page-container {{
    width: 210mm;
    height: 297mm;
    background: white;
    margin: 0 auto;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
    border-radius: 10px;
    overflow: hidden;
}}
.receipt-container {{
    width: 100%;
    height: 50%;
    padding: 15mm;
    border-bottom: 3px dashed #ddd;
    display: flex;
    flex-direction: column;
    position: relative;
}}
.receipt-container:last-child {{
    border-bottom: none;
}}
.receipt-header {{
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 12mm;
    border-radius: 8px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12mm;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}}
.receipt-header h3 {{
    font-size: 16px;
    font-weight: 700;
    margin: 0;
    letter-spacing: 0.5px;
}}
.copy-type {{
    font-size: 11px;
    font-weight: 700;
    color: white;
    background: rgba(255, 255, 255, 0.2);
    padding: 3mm 8mm;
    border-radius: 20px;
    backdrop-filter: blur(10px);
}}
.receipt-title {{
    text-align: center;
    margin-bottom: 12mm;
}}
.receipt-title h2 {{
    font-size: 18px;
    font-weight: 700;
    color: #333;
    letter-spacing: 1px;
    text-transform: uppercase;
}}
.receipt-info {{
    display: flex;
    justify-content: space-between;
    margin-bottom: 12mm;
    padding: 8mm;
    background: #f8f9fa;
    border-radius: 6px;
    border-left: 4px solid #667eea;
}}
.info-row {{
    display: flex;
    gap: 3mm;
    align-items: center;
}}
.info-row .label {{
    font-weight: 600;
    font-size: 10px;
    color: #555;
    text-transform: uppercase;
}}
.info-row .value {{
    font-size: 10px;
    color: #333;
    font-weight: 500;
}}
.receipt-details {{
    flex: 1;
}}
.detail-row {{
    display: flex;
    margin-bottom: 5mm;
    padding: 4mm 0;
    border-bottom: 1px solid #f0f0f0;
}}
.detail-row:last-child {{
    border-bottom: none;
}}
.detail-row .label {{
    font-weight: 600;
    font-size: 10px;
    color: #555;
    width: 30mm;
    text-transform: uppercase;
}}
.detail-row .value {{
    font-size: 10px;
    color: #333;
    font-weight: 500;
}}
.receipt-footer {{
    margin-top: auto;
    padding-top: 8mm;
    border-top: 2px solid #f0f0f0;
}}
.receipt-footer p {{
    font-size: 9px;
    color: #666;
    font-style: italic;
    margin-bottom: 6mm;
    text-align: center;
}}
.signature-area {{
    display: flex;
    align-items: center;
    gap: 3mm;
    justify-content: center;
}}
.signature-area .label {{
    font-size: 9px;
    font-weight: 600;
    color: #555;
}}
.signature-line {{
    flex: 1;
    height: 2px;
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    max-width: 40mm;
}}
.cut-line {{
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: repeating-linear-gradient(
        90deg,
        #ddd,
        #ddd 10px,
        transparent 10px,
        transparent 20px
    );
}}
@media print {{
    body {{ 
        background: white;
        padding: 0;
    }}
    .page-container {{ 
        box-shadow: none;
        border-radius: 0;
    }}
    @page {{
        size: A4 portrait;
        margin: 0;
    }}
}}
</style></head><body>
<div class="page-container">
    <div class="receipt-container">
        {receipt_html}
        <div class="cut-line"></div>
    </div>
    <div class="receipt-container">
        {management_html}
    </div>
</div>
<script>window.onload=function(){{window.print();}}</script>
</body></html>"""
    return HTMLResponse(content=html)


async def _queue_receipt_notification(
    db: AsyncSession,
    receipt: Receipt,
    channel: NotificationChannel,
    user: User,
    address: str,
    recipient_name: str,
) -> None:
    job = NotificationJob(
        organization_id=receipt.organization_id,
        branch_id=receipt.branch_id,
        channel=channel,
        subject=f"Makbuz: {receipt.receipt_number}",
        body=f"Makbuz numaranız: {receipt.receipt_number}",
        reference_type="receipt",
        reference_id=receipt.id,
        created_by=user.id,
    )
    db.add(job)
    await db.flush()
    db.add(
        NotificationRecipient(
            notification_job_id=job.id,
            recipient_name=recipient_name,
            recipient_address=address,
        )
    )


@router.post("/api/receipts/{receipt_id}/send-email")
async def send_receipt_email(
    receipt_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("receipt.write")),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    receipt_result = await db.execute(
        select(Receipt).where(Receipt.id == receipt_id)
    )
    receipt = receipt_result.scalar_one_or_none()
    
    if not receipt:
        raise NotFoundException("Makbuz bulunamadı")
    
    payment = (
        await db.execute(select(Payment).where(Payment.id == receipt.payment_id))
    ).scalar_one_or_none()
    
    if not payment:
        raise NotFoundException("Ödeme bulunamadı")
    
    parent = (
        await db.execute(
            select(Parent)
            .join(StudentParent, StudentParent.parent_id == Parent.id)
            .where(StudentParent.student_id == payment.student_id, Parent.email.isnot(None))
            .limit(1)
        )
    ).scalar_one_or_none()
    if not parent or not parent.email:
        raise ValidationException("Veli e-posta adresi bulunamadı")
    await _queue_receipt_notification(
        db,
        receipt,
        NotificationChannel.EMAIL,
        user,
        parent.email,
        f"{parent.first_name} {parent.last_name}",
    )
    return success_response(message="Makbuz e-posta kuyruğuna alındı")


@router.post("/api/receipts/{receipt_id}/send-sms")
async def send_receipt_sms(
    receipt_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("receipt.write")),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    receipt_result = await db.execute(
        select(Receipt).where(Receipt.id == receipt_id)
    )
    receipt = receipt_result.scalar_one_or_none()
    
    if not receipt:
        raise NotFoundException("Makbuz bulunamadı")
    
    payment = (
        await db.execute(select(Payment).where(Payment.id == receipt.payment_id))
    ).scalar_one_or_none()
    
    if not payment:
        raise NotFoundException("Ödeme bulunamadı")
    
    parent = (
        await db.execute(
            select(Parent)
            .join(StudentParent, StudentParent.parent_id == Parent.id)
            .where(StudentParent.student_id == payment.student_id)
            .limit(1)
        )
    ).scalar_one_or_none()
    phone = (parent.sms_phone or parent.phone) if parent else None
    if not phone:
        raise ValidationException("Veli telefon numarası bulunamadı")
    await _queue_receipt_notification(
        db,
        receipt,
        NotificationChannel.SMS,
        user,
        phone,
        f"{parent.first_name} {parent.last_name}" if parent else "",
    )
    return success_response(message="Makbuz SMS kuyruğuna alındı")


@router.post("/api/receipts/{receipt_id}/send-whatsapp")
async def send_receipt_whatsapp(
    receipt_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("receipt.write")),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    receipt_result = await db.execute(
        select(Receipt).where(Receipt.id == receipt_id)
    )
    receipt = receipt_result.scalar_one_or_none()
    
    if not receipt:
        raise NotFoundException("Makbuz bulunamadı")
    
    payment = (
        await db.execute(select(Payment).where(Payment.id == receipt.payment_id))
    ).scalar_one_or_none()
    
    if not payment:
        raise NotFoundException("Ödeme bulunamadı")
    
    parent = (
        await db.execute(
            select(Parent)
            .join(StudentParent, StudentParent.parent_id == Parent.id)
            .where(StudentParent.student_id == payment.student_id)
            .limit(1)
        )
    ).scalar_one_or_none()
    phone = (parent.whatsapp_phone or parent.phone) if parent else None
    if not phone:
        raise ValidationException("Veli WhatsApp numarası bulunamadı")
    await _queue_receipt_notification(
        db,
        receipt,
        NotificationChannel.WHATSAPP,
        user,
        phone,
        f"{parent.first_name} {parent.last_name}" if parent else "",
    )
    return success_response(message="Makbuz WhatsApp kuyruğuna alındı")
