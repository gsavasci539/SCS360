from __future__ import annotations
from datetime import UTC, date, datetime
from decimal import Decimal
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, HTTPException, Header
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.schemas.common import (
    AppointmentCreate,
    AppointmentStatusUpdate,
    BulkDailyReportCreate,
    BusCheckInRequest,
    BusRouteCreate,
    BusTelemetryUpdate,
    CanteenPOSPurchaseRequest,
    CanteenProductCreate,
    CanteenRestrictionUpdate,
    CanteenTopupRequest,
    ClassScheduleUpdate,
    DailyReportCreate,
    DutyRosterCreate,
    ExpenseCreate,
    HomeworkCreate,
    HomeworkGradeRequest,
    HomeworkSubmitRequest,
    LibraryBookCreate,
    LibraryBorrowRequest,
    ParentNoticeCreate,
    ParentNoticeStatusUpdate,
    StaffLeaveRequestCreate,
    StaffLeaveReviewRequest,
)
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import NotFoundException, ValidationException
from app.core.permissions import PermissionChecker
from app.core.responses import paginate, success_response
from app.core.tenant import TenantContext
from app.infrastructure.models.models import User

router = APIRouter(tags=["Operations & ERP Modules"])

# Operational adapters share the same persistent services as the main modules.














async def live_parent_notices(db: AsyncSession, tenant: TenantContext) -> list[dict[str, Any]]:
    if not tenant.has_permission("health.read"):
        return []
    from app.application.services.infirmary_service import medicine_request_status, instructions
    from app.domain.entities.health import MedicationSchedule
    from app.infrastructure.models.models import Student

    conditions = []
    if tenant.organization_id:
        conditions.append(Student.organization_id == tenant.organization_id)
    if tenant.branch_ids:
        conditions.append(Student.branch_id.in_(tenant.branch_ids))

    query = (
        select(MedicationSchedule, Student)
        .join(Student, MedicationSchedule.student_id == Student.id)
        .order_by(MedicationSchedule.created_at.desc())
    )
    if conditions:
        query = query.where(and_(*conditions))

    result = await db.execute(query)
    notices = []
    for schedule, student in result:
        status = medicine_request_status(schedule)
        notices.append({
            "id": str(schedule.id),
            "student_id": str(student.id),
            "student_name": f"{student.first_name} {student.last_name}",
            "type": "MEDICINE",
            "title": f"{student.first_name} {student.last_name} - {schedule.medication_name}",
            "content": f"{schedule.dosage} / {schedule.frequency}",
            "details": {
                "medicine_name": schedule.medication_name,
                "dosage": schedule.dosage,
                "time": schedule.frequency,
                "instructions": instructions(schedule),
            },
            "status": status,
            "response_notes": None,
            "created_at": schedule.created_at.isoformat() if schedule.created_at else None,
        })
    return notices



# ==================== 1. GİDERLER (EXPENSES) ====================

@router.get("/api/expenses/branch-options")
async def expense_branch_options(
    page: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=100),
    branch_id: uuid.UUID | None = None,
    tenant: TenantContext = Depends(PermissionChecker("finance.write")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    from app.infrastructure.models.models import Branch
    from app.infrastructure.repositories.base import BaseRepository
    from app.core.responses import paginate
    repo = BaseRepository(db, tenant)
    query = repo._branch_filter(repo._org_filter(select(Branch), Branch), Branch).where(Branch.deleted_at.is_(None))
    if branch_id is not None:
        await repo.get_by_id(branch_id, Branch)
        query = query.where(Branch.id == branch_id)
    rows, total = await repo.paginate(query.order_by(Branch.name, Branch.id), page, page_size)
    return success_response({**paginate([{"id": str(row.id), "name": row.name} for row in rows], total, page, page_size),
        "allows_organization_wide": branch_id is None})


@router.get("/api/expenses")
async def list_expenses(
    category: str | None = None,
    branch_id: uuid.UUID | None = None,
    page: int | None = Query(None, ge=1),
    page_size: int = Query(100, ge=1, le=100),
    tenant: TenantContext = Depends(PermissionChecker("finance.read")),
    db: AsyncSession = Depends(get_db, scope="function")
):
    from app.application.services import operations_service
    return success_response(await operations_service.expenses(db, tenant, category, branch_id, page, page_size))


@router.post("/api/expenses")
async def create_expense(
    body: ExpenseCreate,
    tenant: TenantContext = Depends(PermissionChecker("finance.write")),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function")
):
    from app.application.services import operations_service
    return success_response(await operations_service.create_expense(db, tenant, body), "Gider kaydedildi")


@router.delete("/api/expenses/{expense_id}")
async def delete_expense(
    expense_id: str,
    tenant: TenantContext = Depends(PermissionChecker("finance.write")),
    db: AsyncSession = Depends(get_db, scope="function")
):
    from app.application.services.operations_service import identifier
    from app.infrastructure.repositories.base import BaseRepository
    from app.infrastructure.models.models import Expense
    repo = BaseRepository(db, tenant)
    await repo.soft_delete(await repo.get_by_id(identifier(expense_id), Expense))
    return success_response(message="Gider silindi")


# ==================== 2. RANDEVULAR (APPOINTMENTS) ====================

@router.get("/api/appointments")
async def list_appointments(
    status: str | None = None,
    tenant: TenantContext = Depends(PermissionChecker("appointments.read")),
    db: AsyncSession = Depends(get_db, scope="function")
):
    from app.application.services import appointment_service
    return success_response(await appointment_service.records(db, tenant, status))


@router.post("/api/appointments")
async def create_appointment(
    body: AppointmentCreate,
    tenant: TenantContext = Depends(PermissionChecker("appointments.write")),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function")
):
    from app.application.services import appointment_service
    return success_response(await appointment_service.create(db, tenant, body), "Görüşme randevusu oluşturuldu")


@router.patch("/api/appointments/{appointment_id}/status")
async def update_appointment_status(
    appointment_id: str,
    body: AppointmentStatusUpdate,
    tenant: TenantContext = Depends(PermissionChecker("appointments.write")),
    db: AsyncSession = Depends(get_db, scope="function")
):
    from app.application.services import appointment_service
    return success_response(await appointment_service.update_status(db, tenant, appointment_id, body))


@router.delete("/api/appointments/{appointment_id}")
async def delete_appointment(
    appointment_id: str,
    tenant: TenantContext = Depends(PermissionChecker("appointments.write")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    from app.application.services import appointment_service
    await appointment_service.delete(db, tenant, appointment_id)
    return success_response(message="Randevu silindi")


# ==================== 3. SERVİS & ULAŞIM (TRANSPORT) ====================

@router.get("/api/transport/routes")
async def list_bus_routes(
    tenant: TenantContext = Depends(PermissionChecker("student.read")),
    db: AsyncSession = Depends(get_db, scope="function")
):
    from app.application.services import transport_service
    return success_response(await transport_service.records(db, tenant))


@router.post("/api/transport/routes")
async def create_bus_route(
    body: BusRouteCreate,
    tenant: TenantContext = Depends(PermissionChecker("student.write")),
    db: AsyncSession = Depends(get_db, scope="function")
):
    from app.application.services import transport_service
    return success_response(await transport_service.create(db, tenant, body))


@router.put("/api/transport/routes/{route_id}/telemetry")
async def update_bus_telemetry(
    route_id: str,
    body: BusTelemetryUpdate,
    tenant: TenantContext = Depends(PermissionChecker("student.write")),
    db: AsyncSession = Depends(get_db, scope="function")
):
    from app.application.services import transport_service
    return success_response(await transport_service.telemetry(db, tenant, route_id, body))


@router.post("/api/transport/routes/{route_id}/checkin")
async def bus_student_checkin(
    route_id: str,
    body: BusCheckInRequest,
    tenant: TenantContext = Depends(PermissionChecker("student.write")),
    db: AsyncSession = Depends(get_db, scope="function")
):
    from app.application.services import transport_service
    return success_response(await transport_service.checkin(db, tenant, route_id, body.student_id, body.is_morning, body.is_boarded))


# ==================== 4. KANTİN & DİJİTAL CÜZDAN ====================

@router.get("/api/canteen/wallet/{student_id}")
async def get_canteen_wallet(
    student_id: str,
    tenant: TenantContext = Depends(PermissionChecker("canteen.read", "canteen.manage", "finance.read")),
    db: AsyncSession = Depends(get_db, scope="function")
):
    from app.application.services import canteen_wallet_service as wallets
    return success_response(wallets.serialize(*(await wallets.wallet(db, tenant, student_id))))


@router.post("/api/canteen/wallet/topup")
async def topup_canteen_wallet(
    body: CanteenTopupRequest,
    tenant: TenantContext = Depends(PermissionChecker("canteen.write", "canteen.manage", "finance.write")),
    db: AsyncSession = Depends(get_db, scope="function")
):
    from app.application.services import canteen_wallet_service as wallets
    return success_response(await wallets.topup(db, tenant, body.student_id, body.amount, body.payment_method), "Bakiye yüklendi")


@router.put("/api/canteen/wallet/restrictions")
async def update_canteen_restrictions(
    body: CanteenRestrictionUpdate,
    tenant: TenantContext = Depends(PermissionChecker("canteen.write", "canteen.manage", "finance.write")),
    db: AsyncSession = Depends(get_db, scope="function")
):
    from app.application.services import canteen_wallet_service as wallets
    return success_response(await wallets.restrictions(db, tenant, body))


@router.post("/api/canteen/pos/purchase")
async def pos_canteen_purchase(
    body: CanteenPOSPurchaseRequest,
    tenant: TenantContext = Depends(PermissionChecker("canteen.write", "canteen.manage", "finance.write")),
    db: AsyncSession = Depends(get_db, scope="function")
):
    from app.application.services import canteen_wallet_service as wallets
    return success_response(await wallets.purchase(db, tenant, body.student_id,
        price=body.price, quantity=body.quantity, name=body.item_name, category=body.category))


@router.get("/api/canteen/transactions")
async def list_canteen_transactions(
    student_id: str | None = None,
    tenant: TenantContext = Depends(PermissionChecker("canteen.read", "canteen.manage", "finance.read")),
    db: AsyncSession = Depends(get_db, scope="function")
):
    from app.application.services import canteen_wallet_service as wallets
    return success_response(await wallets.transactions(db, tenant, student_id))


# ==================== 5. ÖDEV & NOTLANDIRMA (HOMEWORK) ====================











# ==================== 6. KÜTÜPHANE & KİTAP ZİMMET ====================

@router.get("/api/library/books")
async def list_library_books(
    search: str | None = None,
    category: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    page: int | None = Query(None, ge=1),
    page_size: int | None = Query(None, ge=1, le=1000),
    skip: int | None = Query(None, ge=0),
    tenant: TenantContext = Depends(PermissionChecker("library.read")),
    db: AsyncSession = Depends(get_db, scope="function")
):
    from app.application.services import library_service
    return success_response(await library_service.books(db, tenant, search, category,
        limit=limit, offset=offset, page=page, page_size=page_size, skip=skip))


@router.post("/api/library/books")
async def create_library_book(
    body: LibraryBookCreate,
    tenant: TenantContext = Depends(PermissionChecker("library.write")),
    db: AsyncSession = Depends(get_db, scope="function")
):
    from app.application.services import library_service
    return success_response(await library_service.create_book(db, tenant, body), "Kitap kataloğa eklendi")


@router.get("/api/library/loans")
async def list_library_loans(
    status: str | None = None,
    tenant: TenantContext = Depends(PermissionChecker("library.read")),
    db: AsyncSession = Depends(get_db, scope="function")
):
    from app.application.services import library_service
    return success_response(await library_service.loans(db, tenant, status))


@router.post("/api/library/loans/borrow")
async def borrow_library_book(
    body: LibraryBorrowRequest,
    tenant: TenantContext = Depends(PermissionChecker("library.write")),
    db: AsyncSession = Depends(get_db, scope="function")
):
    from app.application.services import library_service
    return success_response(await library_service.borrow(db, tenant, body), "Kitap ödünç verildi")


@router.put("/api/library/loans/{loan_id}/return")
async def return_library_book(
    loan_id: str,
    tenant: TenantContext = Depends(PermissionChecker("library.write")),
    db: AsyncSession = Depends(get_db, scope="function")
):
    from app.application.services import library_service
    return success_response(await library_service.return_book(db, tenant, loan_id), "Kitap teslim alındı")


@router.post("/api/library/loans/{loan_id}/remind")
async def remind_library_loan(
    loan_id: str,
    tenant: TenantContext = Depends(PermissionChecker("library.write")),
    db: AsyncSession = Depends(get_db, scope="function")
):
    from app.core.exceptions import AppException

    # No delivery/outbox implementation exists for this operation yet.
    # Fail closed for every loan ID without disclosing record existence.
    raise AppException(
        "Kütüphane hatırlatma gönderimi henüz kullanıma açık değil. Bildirim gönderilmedi.",
        status_code=503,
    )


# ==================== 7. PERSONEL İK & NÖBET ÇİZELGESİ ====================

@router.get("/api/staff/duty-rosters")
async def list_duty_rosters(
    day_of_week: str | None = None,
    tenant: TenantContext = Depends(PermissionChecker("user.read")),
    db: AsyncSession = Depends(get_db, scope="function")
):
    from app.application.services import operations_service
    return success_response(await operations_service.records(db, tenant, "DUTY_ROSTER", day=day_of_week))


@router.post("/api/staff/duty-rosters")
async def create_duty_roster(
    body: DutyRosterCreate,
    tenant: TenantContext = Depends(PermissionChecker("user.write")),
    db: AsyncSession = Depends(get_db, scope="function")
):
    from app.application.services import operations_service
    return success_response(await operations_service.duty(db, tenant, body))


@router.get("/api/staff/leave-requests")
async def list_leave_requests(
    status: str | None = None,
    tenant: TenantContext = Depends(PermissionChecker("user.read")),
    db: AsyncSession = Depends(get_db, scope="function")
):
    from app.application.services import operations_service
    return success_response(await operations_service.records(db, tenant, "STAFF_LEAVE", status=status))


@router.post("/api/staff/leave-requests")
async def create_leave_request(
    body: StaffLeaveRequestCreate,
    tenant: TenantContext = Depends(PermissionChecker("user.read")),
    db: AsyncSession = Depends(get_db, scope="function")
):
    from app.application.services import operations_service
    return success_response(await operations_service.leave(db, tenant, body))


@router.put("/api/staff/leave-requests/{request_id}/review")
async def review_leave_request(
    request_id: str,
    body: StaffLeaveReviewRequest,
    tenant: TenantContext = Depends(PermissionChecker("user.write")),
    db: AsyncSession = Depends(get_db, scope="function")
):
    from app.application.services import operations_service
    return success_response(await operations_service.review_leave(db, tenant, request_id, body))


# ==================== 8. GÜNLÜK KARNE (DAILY REPORTS) ====================







# ==================== 9. VELİ BİLDİRİMLERİ (PARENT NOTICES) ====================

@router.get("/api/parent/notices")
async def list_parent_notices(
    type: str | None = None,
    tenant: TenantContext = Depends(PermissionChecker("student.read")),
    db: AsyncSession = Depends(get_db, scope="function")
):
    from app.routers.parent_notices import notice_query, parent_notice_to_dict
    stored = [dict(parent_notice_to_dict(row, student), title=row.type, content=row.description, details={},
        response_notes=None) for row, student in (await db.execute(await notice_query(db, tenant))).all()]
    items = await live_parent_notices(db, tenant) + stored
    return success_response([row for row in items if not type or row["type"] == type])


@router.post("/api/parent/notices")
async def create_parent_notice(
    body: ParentNoticeCreate,
    tenant: TenantContext = Depends(PermissionChecker("student.write")),
    db: AsyncSession = Depends(get_db, scope="function")
):
    from app.infrastructure.models.models import ParentNotice, Student
    from app.infrastructure.repositories.base import BaseRepository
    from app.core.student_access import require_student_access
    from app.application.services.operations_service import identifier
    student = await BaseRepository(db, tenant).get_by_id(identifier(body.student_id), Student)
    await require_student_access(db, tenant, student.id)
    notice = ParentNotice(organization_id=student.organization_id, student_id=student.id,
        created_by=tenant.user_id, type=body.type, description=f"{body.title}: {body.content}", status="PENDING")
    db.add(notice); await db.flush()
    return success_response({"id": str(notice.id), "type": notice.type, "status": notice.status})


@router.patch("/api/parent/notices/{notice_id}/status")
async def update_parent_notice_status(
    notice_id: str,
    body: ParentNoticeStatusUpdate,
    tenant: TenantContext = Depends(PermissionChecker("student.write")),
    db: AsyncSession = Depends(get_db, scope="function")
):
    from app.routers.parent_notices import update_parent_notice, ParentNoticeUpdate
    from app.application.services.operations_service import identifier
    statuses = {"GIVEN": "COMPLETED", "RECEIVED": "PENDING"}
    return await update_parent_notice(identifier(notice_id), ParentNoticeUpdate(
        status=statuses.get(body.status, body.status)), tenant, None, db)


# ==================== 10. DERS PROGRAMI (CLASS SCHEDULE) ====================

@router.get("/api/classes/{class_id}/schedule")
async def get_class_schedule(
    class_id: str,
    tenant: TenantContext = Depends(PermissionChecker("class.read")),
    db: AsyncSession = Depends(get_db, scope="function")
):
    from app.application.services import operations_service
    return success_response(await operations_service.class_schedule(db, tenant, class_id))


@router.put("/api/classes/{class_id}/schedule")
async def update_class_schedule(
    class_id: str,
    body: ClassScheduleUpdate,
    tenant: TenantContext = Depends(PermissionChecker("class.write")),
    db: AsyncSession = Depends(get_db, scope="function")
):
    from app.application.services import operations_service
    return success_response(await operations_service.class_schedule(db, tenant, class_id, body.schedule_data))


@router.get("/api/teachers/{teacher_id}/schedule")
async def get_teacher_schedule(
    teacher_id: str,
    tenant: TenantContext = Depends(PermissionChecker("user.read")),
    db: AsyncSession = Depends(get_db, scope="function")
):
    from app.application.services import operations_service
    return success_response(await operations_service.teacher_schedule(db, tenant, teacher_id))


# ==================== 11. FİNANS ANALİTİĞİ ====================

@router.get("/api/finance/analytics")
async def get_finance_analytics(
    tenant: TenantContext = Depends(PermissionChecker("finance.read")),
    db: AsyncSession = Depends(get_db, scope="function")
):
    from app.application.services import operations_service
    return success_response(await operations_service.finance_analytics(db, tenant))


# ==================== 12. OUTBOX & BİLDİRİM YÖNETİMİ ====================






@router.post("/api/webhooks/sms-status")
async def webhook_sms_status(payload: dict, webhook_secret: str | None = Header(None, alias="X-Webhook-Secret"),
    db: AsyncSession = Depends(get_db, scope="function")):
    import hmac
    from app.core.config import get_settings
    from app.core.exceptions import AppException
    from app.infrastructure.models.models import NotificationRecipient, NotificationStatus
    from app.application.services.operations_service import identifier
    configured = get_settings().NOTIFICATION_WEBHOOK_SECRET
    if not configured:
        raise AppException("Bildirim webhook bağlantısı yapılandırılmamış", status_code=503)
    if not hmac.compare_digest(configured, webhook_secret or ""):
        raise HTTPException(status_code=403, detail="Webhook kimliği doğrulanamadı")
    recipient = await db.get(NotificationRecipient, identifier(payload.get("recipient_id")))
    if recipient is None:
        raise NotFoundException("Gönderim kaydı bulunamadı")
    if payload.get("status") not in {"DELIVERED", "FAILED"}:
        raise ValidationException("Geçersiz teslim durumu")
    recipient.provider_response = dict(recipient.provider_response or {}, delivery_status=payload["status"],
        delivery_updated_at=datetime.now(UTC).isoformat())
    if payload["status"] == "FAILED":
        recipient.status = NotificationStatus.FAILED
        recipient.error_message = "Sağlayıcı teslim edilemediğini bildirdi"
    return success_response({"received": True}, "Teslim raporu kaydedildi")


@router.get("/api/notifications/unread-count")
async def get_unread_notifications_count(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function")
):
    from app.infrastructure.models.models import NotificationRecipient, NotificationStatus, Parent
    from sqlalchemy import func
    permitted_parents = select(Parent.id).where(Parent.user_id == user.id, Parent.organization_id == user.organization_id)
    count = (await db.execute(select(func.count()).select_from(NotificationRecipient).where(
        (NotificationRecipient.user_id == user.id) | NotificationRecipient.parent_id.in_(permitted_parents),
        NotificationRecipient.status == NotificationStatus.SENT, NotificationRecipient.read_at.is_(None)))).scalar_one()
    return success_response({"unread_count": count})


@router.patch("/api/notifications/mark-all-read")
async def mark_all_notifications_read(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function")
):
    from app.infrastructure.models.models import NotificationRecipient, NotificationStatus, Parent
    from sqlalchemy import update
    permitted_parents = select(Parent.id).where(Parent.user_id == user.id, Parent.organization_id == user.organization_id)
    await db.execute(update(NotificationRecipient).where(
        (NotificationRecipient.user_id == user.id) | NotificationRecipient.parent_id.in_(permitted_parents),
        NotificationRecipient.status == NotificationStatus.SENT, NotificationRecipient.read_at.is_(None))
        .values(read_at=datetime.now(UTC)))
    return success_response(message="Bildirimler okundu olarak kaydedildi")


# ==================== 13. KULLANICI PROFİL & FCM TOKEN ====================

@router.patch("/api/users/{user_id}/fcm-token")
async def update_user_fcm_token(
    user_id: str,
    payload: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function")
):
    import hashlib
    from app.infrastructure.models.models import UserDeviceToken
    from app.application.services.operations_service import identifier
    if identifier(user_id) != user.id:
        raise HTTPException(status_code=403, detail="Yalnızca kendi cihazınızı kaydedebilirsiniz")
    token = payload.get("fcm_token") or payload.get("token")
    if not isinstance(token, str) or not 16 <= len(token) <= 4096:
        raise ValidationException("Geçerli bir cihaz token bilgisi gerekli")
    digest = hashlib.sha256(token.encode()).hexdigest()
    row = (await db.execute(select(UserDeviceToken).where(UserDeviceToken.token_hash == digest))).scalar_one_or_none()
    if row is None:
        row = UserDeviceToken(user_id=user.id, token_hash=digest, token=token)
        db.add(row)
    elif row.user_id != user.id:
        raise HTTPException(status_code=409, detail="Cihaz başka bir hesaba kayıtlı")
    return success_response(message="Cihaz kaydedildi")


@router.put("/api/users/{user_id}/avatar")
async def update_user_avatar(
    user_id: str,
    payload: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function")
):
    from app.application.services.operations_service import identifier
    from urllib.parse import urlparse
    if identifier(user_id) != user.id:
        raise HTTPException(status_code=403, detail="Yalnızca kendi profilinizi güncelleyebilirsiniz")
    value = payload.get("avatar_url")
    if not isinstance(value, str) or len(value) > 500 or not (value.startswith("/api/files/") or urlparse(value).scheme == "https"):
        raise ValidationException("Geçerli bir profil görseli adresi gerekli")
    user.avatar_url = value
    return success_response({"avatar_url": user.avatar_url}, "Profil fotoğrafı kaydedildi")
