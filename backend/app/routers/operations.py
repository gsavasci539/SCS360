from datetime import UTC, date, datetime
from decimal import Decimal
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
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

# In-memory operational store with realistic mock persistence for extended ERP entities
_EXPENSES: list[dict[str, Any]] = [
    {
        "id": "exp-001",
        "organization_id": "org-default",
        "branch_id": "branch-001",
        "category": "Kira",
        "title": "Ağustos Ayı Ana Bina Kira Bedeli",
        "amount": "45000.00",
        "date": "2026-08-01",
        "receipt_url": "https://okul360.com/receipts/kira-08.pdf",
        "created_at": "2026-08-01T09:00:00Z"
    },
    {
        "id": "exp-002",
        "organization_id": "org-default",
        "branch_id": "branch-001",
        "category": "Mutfak",
        "title": "Haftalık Organik Sebze & Meyve Alımı",
        "amount": "12850.50",
        "date": "2026-08-15",
        "receipt_url": "https://okul360.com/receipts/mutfak-08.pdf",
        "created_at": "2026-08-15T11:30:00Z"
    }
]

_APPOINTMENTS: list[dict[str, Any]] = [
    {
        "id": "apt-001",
        "teacher_id": "usr-teacher-1",
        "teacher_name": "Ayşe Yılmaz",
        "subject": "Matematik Öğretmeni",
        "parent_id": "par-001",
        "parent_name": "Mehmet Demir",
        "student_id": "std-001",
        "student_name": "Zeynep Demir",
        "date": "2026-08-28",
        "time_slot": "14:30 - 15:00",
        "type": "IN_PERSON",
        "status": "CONFIRMED",
        "notes": "1. dönem matematik gelişimi ve sınav hazırlığı görüşmesi",
        "feedback_notes": None,
        "meeting_link": "https://meet.google.com/okul360-ptc-001",
        "created_at": "2026-08-25T10:00:00Z"
    }
]

_BUS_ROUTES: list[dict[str, Any]] = [
    {
        "id": "bus-001",
        "branch_id": "branch-001",
        "route_name": "1. Hat (Kadıköy - Ataşehir)",
        "plate_number": "34 OKL 360",
        "driver_name": "Ahmet Şahin",
        "driver_phone": "+90 532 555 1020",
        "hostess_name": "Fatma Can",
        "hostess_phone": "+90 533 555 3040",
        "current_lat": 40.9912,
        "current_lng": 29.0234,
        "speed_kmh": 42,
        "last_passed_stop": "Ataşehir Migros Durağı",
        "next_stop": "Batı Ataşehir Konutları",
        "estimated_arrival_minutes": 8,
        "students": [
            {"student_id": "std-001", "student_name": "Zeynep Demir", "stop_name": "Batı Ataşehir", "is_morning_boarded": True, "is_evening_boarded": False}
        ]
    }
]

_CANTEEN_WALLETS: dict[str, dict[str, Any]] = {
    "std-001": {
        "student_id": "std-001",
        "current_balance": 350.0,
        "daily_limit": 100.0,
        "today_spent": 25.0,
        "restricted_categories": ["Gazlı İçecek", "Enerji İçeceği"],
        "restricted_allergens": ["Fıstık", "Gluten"]
    }
}

_CANTEEN_TRANSACTIONS: list[dict[str, Any]] = [
    {
        "id": "tx-001",
        "student_id": "std-001",
        "amount": 25.0,
        "type": "PURCHASE",
        "item_name": "Kaşarlı Tost + Ayran",
        "date": "2026-08-25 10:15",
        "status": "APPROVED"
    },
    {
        "id": "tx-002",
        "student_id": "std-001",
        "amount": 200.0,
        "type": "TOPUP",
        "item_name": "Kredi Kartı Yükleme",
        "date": "2026-08-24 08:30",
        "status": "APPROVED"
    }
]

_HOMEWORK_LIST: list[dict[str, Any]] = [
    {
        "id": "hw-001",
        "class_id": "cls-001",
        "class_name": "5-A",
        "title": "Doğal Sayılar ve Basamak Değeri Testi",
        "subject": "Matematik",
        "description": "Sayfa 45-48 arasındaki alıştırmalar çözülecek ve sisteme yüklenecektir.",
        "due_date": "2026-08-30",
        "attachment_url": "https://okul360.com/homework/mat-5a-01.pdf",
        "created_at": "2026-08-25T08:00:00Z"
    }
]

_HOMEWORK_SUBMISSIONS: list[dict[str, Any]] = [
    {
        "id": "sub-001",
        "homework_id": "hw-001",
        "student_id": "std-001",
        "student_name": "Zeynep Demir",
        "student_number": "2026-045",
        "submission_text": "Ödevimi tamamladım, sorular çözüldü.",
        "attachment_file_name": "zeynep_matematik_odev.pdf",
        "attachment_file_size_mb": 1.4,
        "submitted_at": "2026-08-25 19:40",
        "status": "GRADED",
        "score": 95,
        "teacher_feedback": "Aferin Zeynep, işlem adımların çok düzenli."
    }
]

_LIBRARY_BOOKS: list[dict[str, Any]] = [
    {
        "id": "bk-001",
        "title": "Küçük Prens",
        "author": "Antoine de Saint-Exupéry",
        "category": "Dünya Klasikleri",
        "isbn": "978-9750738609",
        "barcode": "9789750738609",
        "total_copies": 5,
        "available_copies": 4
    },
    {
        "id": "bk-002",
        "title": "Nutuk",
        "author": "Mustafa Kemal Atatürk",
        "category": "Tarih",
        "isbn": "978-9751600003",
        "barcode": "9789751600003",
        "total_copies": 10,
        "available_copies": 8
    }
]

_LIBRARY_LOANS: list[dict[str, Any]] = [
    {
        "id": "loan-001",
        "book_id": "bk-001",
        "book_title": "Küçük Prens",
        "student_id": "std-001",
        "student_name": "Zeynep Demir",
        "student_number": "2026-045",
        "class_name": "5-A",
        "borrow_date": "2026-08-15",
        "due_date": "2026-08-29",
        "return_date": None,
        "status": "BORROWED",
        "fine_amount": 0.0
    }
]

_DUTY_ROSTERS: list[dict[str, Any]] = [
    {
        "id": "duty-001",
        "branch_id": "branch-001",
        "teacher_id": "usr-teacher-1",
        "teacher_name": "Ayşe Yılmaz",
        "day_of_week": "Pazartesi",
        "duty_location": "A Blok 1. Kat Koridoru",
        "start_time": "08:30",
        "end_time": "16:30"
    },
    {
        "id": "duty-002",
        "branch_id": "branch-001",
        "teacher_id": "usr-teacher-2",
        "teacher_name": "Mustafa Kaya",
        "day_of_week": "Salı",
        "duty_location": "Okul Bahçesi & Yemekhane",
        "start_time": "08:30",
        "end_time": "16:30"
    }
]

_STAFF_LEAVES: list[dict[str, Any]] = [
    {
        "id": "leave-001",
        "staff_id": "usr-teacher-1",
        "staff_name": "Ayşe Yılmaz",
        "leave_type": "Mazeret İzni",
        "start_date": "2026-09-02",
        "end_date": "2026-09-03",
        "days_count": 2,
        "reason": "Resmi daire işlemleri",
        "status": "APPROVED",
        "admin_comment": "Onaylandı, ders telafisi planlanmıştır."
    }
]

_DAILY_REPORTS: list[dict[str, Any]] = [
    {
        "id": "rep-001",
        "student_id": "std-001",
        "date": "2026-08-25",
        "meal_breakfast": "TAM",
        "meal_lunch": "TAM",
        "meal_snack": "YARIM",
        "sleep_status": "UYUDU (1.5 Saat)",
        "mood": "Çok Neşeli & Aktif",
        "activities": "Robotik kodlama ve drama oyunları yapıldı.",
        "teacher_notes": "Grup etkinliklerinde liderlik sergiledi."
    }
]

_PARENT_NOTICES: list[dict[str, Any]] = [
    {
        "id": "notice-001",
        "student_id": "std-001",
        "type": "MEDICINE",
        "title": "Alerji Şurubu",
        "content": "Öğle yemeğinden sonra 1 ölçek (5ml) verilecektir.",
        "details": {"medicine_name": "Aerius", "dosage": "5ml", "time": "13:00"},
        "status": "GIVEN",
        "response_notes": "13:05'te hemşire gözetiminde verildi.",
        "created_at": "2026-08-25T07:30:00Z"
    }
]

_CLASS_SCHEDULES: dict[str, list[dict[str, Any]]] = {
    "cls-001": [
        {"day": "Pazartesi", "periods": [
            {"time": "09:00 - 09:40", "subject": "Matematik", "teacher": "Ayşe Yılmaz"},
            {"time": "09:50 - 10:30", "subject": "Türkçe", "teacher": "Mehmet Kaya"},
            {"time": "10:40 - 11:20", "subject": "Fen Bilimleri", "teacher": "Zeynep Çelik"}
        ]},
        {"day": "Salı", "periods": [
            {"time": "09:00 - 09:40", "subject": "İngilizce", "teacher": "John Smith"},
            {"time": "09:50 - 10:30", "subject": "Sosyal Bilgiler", "teacher": "Ali Vural"},
            {"time": "10:40 - 11:20", "subject": "Beden Eğitimi", "teacher": "Canan Er"}
        ]}
    ]
}


# ==================== 1. GİDERLER (EXPENSES) ====================

@router.get("/api/expenses")
async def list_expenses(
    category: str | None = None,
    tenant: TenantContext = Depends(PermissionChecker("finance.read")),
    db: AsyncSession = Depends(get_db)
):
    items = _EXPENSES
    if category:
        items = [e for e in items if e["category"] == category]
    return success_response(items)


@router.post("/api/expenses")
async def create_expense(
    body: ExpenseCreate,
    tenant: TenantContext = Depends(PermissionChecker("finance.write")),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    exp = {
        "id": f"exp-{uuid.uuid4().hex[:6]}",
        "organization_id": str(user.organization_id) if user.organization_id else "org-default",
        "branch_id": body.branch_id,
        "category": body.category,
        "title": body.title,
        "amount": str(Decimal(body.amount)),
        "date": body.date,
        "receipt_url": body.receipt_url,
        "created_at": datetime.now(UTC).isoformat()
    }
    _EXPENSES.insert(0, exp)
    return success_response(exp, "Gider başarıyla kaydedildi")


@router.delete("/api/expenses/{expense_id}")
async def delete_expense(
    expense_id: str,
    tenant: TenantContext = Depends(PermissionChecker("finance.write")),
    db: AsyncSession = Depends(get_db)
):
    global _EXPENSES
    _EXPENSES = [e for e in _EXPENSES if e["id"] != expense_id]
    return success_response(message="Gider kaydı silindi")


# ==================== 2. RANDEVULAR (APPOINTMENTS) ====================

@router.get("/api/appointments")
async def list_appointments(
    status: str | None = None,
    tenant: TenantContext = Depends(PermissionChecker("student.read")),
    db: AsyncSession = Depends(get_db)
):
    items = _APPOINTMENTS
    if status:
        items = [a for a in items if a["status"] == status]
    return success_response(items)


@router.post("/api/appointments")
async def create_appointment(
    body: AppointmentCreate,
    tenant: TenantContext = Depends(PermissionChecker("student.write")),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    apt = {
        "id": f"apt-{uuid.uuid4().hex[:6]}",
        "teacher_id": body.teacher_id,
        "teacher_name": body.teacher_name,
        "subject": body.subject,
        "parent_id": str(user.id),
        "parent_name": f"{user.first_name} {user.last_name}",
        "student_id": "std-001",
        "student_name": "Kayıtlı Öğrenci",
        "date": body.date,
        "time_slot": body.time_slot,
        "type": body.type,
        "status": "CONFIRMED",
        "notes": body.notes,
        "feedback_notes": None,
        "meeting_link": f"https://meet.google.com/okul360-{uuid.uuid4().hex[:4]}",
        "created_at": datetime.now(UTC).isoformat()
    }
    _APPOINTMENTS.insert(0, apt)
    return success_response(apt, "Görüşme randevusu oluşturuldu")


@router.patch("/api/appointments/{appointment_id}/status")
async def update_appointment_status(
    appointment_id: str,
    body: AppointmentStatusUpdate,
    tenant: TenantContext = Depends(PermissionChecker("student.write")),
    db: AsyncSession = Depends(get_db)
):
    for a in _APPOINTMENTS:
        if a["id"] == appointment_id:
            a["status"] = body.status
            if body.feedback_notes:
                a["feedback_notes"] = body.feedback_notes
            return success_response(a, "Randevu durumu güncellendi")
    raise NotFoundException("Randevu bulunamadı")


# ==================== 3. SERVİS & ULAŞIM (TRANSPORT) ====================

@router.get("/api/transport/routes")
async def list_bus_routes(
    tenant: TenantContext = Depends(PermissionChecker("student.read")),
    db: AsyncSession = Depends(get_db)
):
    return success_response(_BUS_ROUTES)


@router.post("/api/transport/routes")
async def create_bus_route(
    body: BusRouteCreate,
    tenant: TenantContext = Depends(PermissionChecker("student.write")),
    db: AsyncSession = Depends(get_db)
):
    route = {
        "id": f"bus-{uuid.uuid4().hex[:6]}",
        "branch_id": body.branch_id,
        "route_name": body.route_name,
        "plate_number": body.plate_number,
        "driver_name": body.driver_name,
        "driver_phone": body.driver_phone,
        "hostess_name": body.hostess_name,
        "hostess_phone": body.hostess_phone,
        "current_lat": 41.0082,
        "current_lng": 28.9784,
        "speed_kmh": 0,
        "last_passed_stop": "Okul Ana Kampüs",
        "next_stop": "1. Durak",
        "estimated_arrival_minutes": 15,
        "students": []
    }
    _BUS_ROUTES.append(route)
    return success_response(route, "Servis güzergahı tanımlandı")


@router.put("/api/transport/routes/{route_id}/telemetry")
async def update_bus_telemetry(
    route_id: str,
    body: BusTelemetryUpdate,
    tenant: TenantContext = Depends(PermissionChecker("student.write")),
    db: AsyncSession = Depends(get_db)
):
    for r in _BUS_ROUTES:
        if r["id"] == route_id:
            r["current_lat"] = body.current_lat
            r["current_lng"] = body.current_lng
            r["speed_kmh"] = body.speed_kmh
            r["last_passed_stop"] = body.last_passed_stop
            r["next_stop"] = body.next_stop
            r["estimated_arrival_minutes"] = body.estimated_arrival_minutes
            return success_response(r, "Telemetri güncellendi")
    raise NotFoundException("Servis hattı bulunamadı")


@router.post("/api/transport/routes/{route_id}/checkin")
async def bus_student_checkin(
    route_id: str,
    body: BusCheckInRequest,
    tenant: TenantContext = Depends(PermissionChecker("student.write")),
    db: AsyncSession = Depends(get_db)
):
    for r in _BUS_ROUTES:
        if r["id"] == route_id:
            for s in r.get("students", []):
                if s["student_id"] == body.student_id:
                    if body.is_morning:
                        s["is_morning_boarded"] = body.is_boarded
                    else:
                        s["is_evening_boarded"] = body.is_boarded
                    return success_response(s, "Öğrenci servis biniş kaydı güncellendi")
    return success_response(message="Kayıt işlendi")


# ==================== 4. KANTİN & DİJİTAL CÜZDAN ====================

@router.get("/api/canteen/wallet/{student_id}")
async def get_canteen_wallet(
    student_id: str,
    tenant: TenantContext = Depends(PermissionChecker("finance.read")),
    db: AsyncSession = Depends(get_db)
):
    wallet = _CANTEEN_WALLETS.get(student_id, {
        "student_id": student_id,
        "current_balance": 250.0,
        "daily_limit": 100.0,
        "today_spent": 0.0,
        "restricted_categories": [],
        "restricted_allergens": []
    })
    return success_response(wallet)


@router.post("/api/canteen/wallet/topup")
async def topup_canteen_wallet(
    body: CanteenTopupRequest,
    tenant: TenantContext = Depends(PermissionChecker("finance.write")),
    db: AsyncSession = Depends(get_db)
):
    if body.amount <= 0:
        raise ValidationException("Yükleme tutarı 0'dan büyük olmalıdır")
    if body.student_id not in _CANTEEN_WALLETS:
        _CANTEEN_WALLETS[body.student_id] = {
            "student_id": body.student_id,
            "current_balance": 0.0,
            "daily_limit": 100.0,
            "today_spent": 0.0,
            "restricted_categories": [],
            "restricted_allergens": []
        }
    _CANTEEN_WALLETS[body.student_id]["current_balance"] += body.amount
    tx = {
        "id": f"tx-{uuid.uuid4().hex[:6]}",
        "student_id": body.student_id,
        "amount": body.amount,
        "type": "TOPUP",
        "item_name": f"{body.payment_method} Bakiye Yükleme",
        "date": datetime.now(UTC).strftime("%Y-%m-%d %H:%M"),
        "status": "APPROVED"
    }
    _CANTEEN_TRANSACTIONS.insert(0, tx)
    return success_response(_CANTEEN_WALLETS[body.student_id], f"₺{body.amount} bakiye yüklendi")


@router.put("/api/canteen/wallet/restrictions")
async def update_canteen_restrictions(
    body: CanteenRestrictionUpdate,
    tenant: TenantContext = Depends(PermissionChecker("finance.write")),
    db: AsyncSession = Depends(get_db)
):
    if body.student_id not in _CANTEEN_WALLETS:
        _CANTEEN_WALLETS[body.student_id] = {
            "student_id": body.student_id,
            "current_balance": 100.0,
            "daily_limit": body.daily_limit,
            "today_spent": 0.0,
            "restricted_categories": body.restricted_categories,
            "restricted_allergens": body.restricted_allergens
        }
    else:
        w = _CANTEEN_WALLETS[body.student_id]
        w["daily_limit"] = body.daily_limit
        w["restricted_categories"] = body.restricted_categories
        w["restricted_allergens"] = body.restricted_allergens
    return success_response(_CANTEEN_WALLETS[body.student_id], "Kantin kısıtlamaları güncellendi")


@router.post("/api/canteen/pos/purchase")
async def pos_canteen_purchase(
    body: CanteenPOSPurchaseRequest,
    tenant: TenantContext = Depends(PermissionChecker("finance.write")),
    db: AsyncSession = Depends(get_db)
):
    total = body.price * body.quantity
    wallet = _CANTEEN_WALLETS.get(body.student_id)
    if wallet and wallet["current_balance"] < total:
        raise ValidationException("Yetersiz bakiye")
    if wallet:
        wallet["current_balance"] -= total
        wallet["today_spent"] += total
    tx = {
        "id": f"tx-{uuid.uuid4().hex[:6]}",
        "student_id": body.student_id,
        "amount": total,
        "type": "PURCHASE",
        "item_name": f"{body.quantity}x {body.item_name}",
        "date": datetime.now(UTC).strftime("%Y-%m-%d %H:%M"),
        "status": "APPROVED"
    }
    _CANTEEN_TRANSACTIONS.insert(0, tx)
    return success_response(tx, "Kantin satışı başarıyla tamamlandı")


@router.get("/api/canteen/transactions")
async def list_canteen_transactions(
    student_id: str | None = None,
    tenant: TenantContext = Depends(PermissionChecker("finance.read")),
    db: AsyncSession = Depends(get_db)
):
    items = _CANTEEN_TRANSACTIONS
    if student_id:
        items = [t for t in items if t["student_id"] == student_id]
    return success_response(items)


# ==================== 5. ÖDEV & NOTLANDIRMA (HOMEWORK) ====================

@router.get("/api/homework")
async def list_homework(
    class_id: str | None = None,
    tenant: TenantContext = Depends(PermissionChecker("student.read")),
    db: AsyncSession = Depends(get_db)
):
    items = _HOMEWORK_LIST
    if class_id:
        items = [h for h in items if h["class_id"] == class_id]
    return success_response(items)


@router.post("/api/homework")
async def create_homework(
    body: HomeworkCreate,
    tenant: TenantContext = Depends(PermissionChecker("student.write")),
    db: AsyncSession = Depends(get_db)
):
    hw = {
        "id": f"hw-{uuid.uuid4().hex[:6]}",
        "class_id": body.class_id,
        "class_name": "5-A",
        "title": body.title,
        "subject": body.subject,
        "description": body.description,
        "due_date": body.due_date,
        "attachment_url": body.attachment_url,
        "created_at": datetime.now(UTC).isoformat()
    }
    _HOMEWORK_LIST.insert(0, hw)
    return success_response(hw, "Ödev başarıyla tanımlandı")


@router.get("/api/homework/submissions")
async def list_homework_submissions(
    homework_id: str | None = None,
    tenant: TenantContext = Depends(PermissionChecker("student.read")),
    db: AsyncSession = Depends(get_db)
):
    items = _HOMEWORK_SUBMISSIONS
    if homework_id:
        items = [s for s in items if s["homework_id"] == homework_id]
    return success_response(items)


@router.post("/api/homework/{homework_id}/submit")
async def submit_homework(
    homework_id: str,
    body: HomeworkSubmitRequest,
    tenant: TenantContext = Depends(PermissionChecker("student.write")),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    sub = {
        "id": f"sub-{uuid.uuid4().hex[:6]}",
        "homework_id": homework_id,
        "student_id": body.student_id,
        "student_name": f"{user.first_name} {user.last_name}",
        "student_number": "2026-045",
        "submission_text": body.submission_text or "Ödev teslim edildi",
        "attachment_file_name": body.file_name or "odev_teslim.pdf",
        "attachment_file_size_mb": body.file_size_mb or 1.2,
        "submitted_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M"),
        "status": "SUBMITTED",
        "score": None,
        "teacher_feedback": None
    }
    _HOMEWORK_SUBMISSIONS.insert(0, sub)
    return success_response(sub, "Ödev teslim edildi")


@router.put("/api/homework/submissions/{submission_id}/grade")
async def grade_homework_submission(
    submission_id: str,
    body: HomeworkGradeRequest,
    tenant: TenantContext = Depends(PermissionChecker("student.write")),
    db: AsyncSession = Depends(get_db)
):
    for s in _HOMEWORK_SUBMISSIONS:
        if s["id"] == submission_id:
            s["score"] = body.score
            s["teacher_feedback"] = body.teacher_feedback
            s["status"] = "GRADED"
            return success_response(s, "Ödev notlandırıldı")
    raise NotFoundException("Ödev teslimi bulunamadı")


# ==================== 6. KÜTÜPHANE & KİTAP ZİMMET ====================

@router.get("/api/library/books")
async def list_library_books(
    search: str | None = None,
    category: str | None = None,
    tenant: TenantContext = Depends(PermissionChecker("student.read")),
    db: AsyncSession = Depends(get_db)
):
    items = _LIBRARY_BOOKS
    if search:
        items = [b for b in items if search.lower() in b["title"].lower() or search.lower() in b["author"].lower()]
    if category:
        items = [b for b in items if b["category"] == category]
    return success_response(items)


@router.post("/api/library/books")
async def create_library_book(
    body: LibraryBookCreate,
    tenant: TenantContext = Depends(PermissionChecker("student.write")),
    db: AsyncSession = Depends(get_db)
):
    bk = {
        "id": f"bk-{uuid.uuid4().hex[:6]}",
        "title": body.title,
        "author": body.author,
        "category": body.category,
        "isbn": body.isbn,
        "barcode": body.barcode,
        "total_copies": body.total_copies,
        "available_copies": body.total_copies
    }
    _LIBRARY_BOOKS.insert(0, bk)
    return success_response(bk, "Kitap kataloğa eklendi")


@router.get("/api/library/loans")
async def list_library_loans(
    status: str | None = None,
    tenant: TenantContext = Depends(PermissionChecker("student.read")),
    db: AsyncSession = Depends(get_db)
):
    items = _LIBRARY_LOANS
    if status:
        items = [l for l in items if l["status"] == status]
    return success_response(items)


@router.post("/api/library/loans/borrow")
async def borrow_library_book(
    body: LibraryBorrowRequest,
    tenant: TenantContext = Depends(PermissionChecker("student.write")),
    db: AsyncSession = Depends(get_db)
):
    for b in _LIBRARY_BOOKS:
        if b["id"] == body.book_id:
            if b["available_copies"] <= 0:
                raise ValidationException("Kitabın uygun kopyası bulunmamaktadır")
            b["available_copies"] -= 1
            loan = {
                "id": f"loan-{uuid.uuid4().hex[:6]}",
                "book_id": b["id"],
                "book_title": b["title"],
                "student_id": body.student_id,
                "student_name": body.student_name,
                "student_number": body.student_number,
                "class_name": body.class_name,
                "borrow_date": datetime.now(UTC).strftime("%Y-%m-%d"),
                "due_date": (datetime.now(UTC).date()).isoformat(),
                "return_date": None,
                "status": "BORROWED",
                "fine_amount": 0.0
            }
            _LIBRARY_LOANS.insert(0, loan)
            return success_response(loan, "Kitap ödünç verildi")
    raise NotFoundException("Kitap bulunamadı")


@router.put("/api/library/loans/{loan_id}/return")
async def return_library_book(
    loan_id: str,
    tenant: TenantContext = Depends(PermissionChecker("student.write")),
    db: AsyncSession = Depends(get_db)
):
    for l in _LIBRARY_LOANS:
        if l["id"] == loan_id:
            l["return_date"] = datetime.now(UTC).strftime("%Y-%m-%d")
            l["status"] = "RETURNED"
            for b in _LIBRARY_BOOKS:
                if b["id"] == l["book_id"]:
                    b["available_copies"] += 1
            return success_response(l, "Kitap teslim alındı")
    raise NotFoundException("Ödünç kaydı bulunamadı")


@router.post("/api/library/loans/{loan_id}/remind")
async def remind_library_loan(
    loan_id: str,
    tenant: TenantContext = Depends(PermissionChecker("student.write")),
    db: AsyncSession = Depends(get_db)
):
    return success_response(message="Veli ve öğrenciye iade hatırlatma bildirimi gönderildi")


# ==================== 7. PERSONEL İK & NÖBET ÇİZELGESİ ====================

@router.get("/api/staff/duty-rosters")
async def list_duty_rosters(
    day_of_week: str | None = None,
    tenant: TenantContext = Depends(PermissionChecker("user.read")),
    db: AsyncSession = Depends(get_db)
):
    items = _DUTY_ROSTERS
    if day_of_week:
        items = [d for d in items if d["day_of_week"] == day_of_week]
    return success_response(items)


@router.post("/api/staff/duty-rosters")
async def create_duty_roster(
    body: DutyRosterCreate,
    tenant: TenantContext = Depends(PermissionChecker("user.write")),
    db: AsyncSession = Depends(get_db)
):
    roster = {
        "id": f"duty-{uuid.uuid4().hex[:6]}",
        "branch_id": body.branch_id,
        "teacher_id": body.teacher_id,
        "teacher_name": body.teacher_name,
        "day_of_week": body.day_of_week,
        "duty_location": body.duty_location,
        "start_time": body.start_time,
        "end_time": body.end_time
    }
    _DUTY_ROSTERS.append(roster)
    return success_response(roster, "Nöbet görevi tanımlandı")


@router.get("/api/staff/leave-requests")
async def list_leave_requests(
    status: str | None = None,
    tenant: TenantContext = Depends(PermissionChecker("user.read")),
    db: AsyncSession = Depends(get_db)
):
    items = _STAFF_LEAVES
    if status:
        items = [l for l in items if l["status"] == status]
    return success_response(items)


@router.post("/api/staff/leave-requests")
async def create_leave_request(
    body: StaffLeaveRequestCreate,
    tenant: TenantContext = Depends(PermissionChecker("user.read")),
    db: AsyncSession = Depends(get_db)
):
    req = {
        "id": f"leave-{uuid.uuid4().hex[:6]}",
        "staff_id": body.staff_id,
        "staff_name": body.staff_name,
        "leave_type": body.leave_type,
        "start_date": body.start_date,
        "end_date": body.end_date,
        "days_count": body.days_count,
        "reason": body.reason,
        "status": "PENDING",
        "admin_comment": None
    }
    _STAFF_LEAVES.insert(0, req)
    return success_response(req, "İzin talebi onaya sunuldu")


@router.put("/api/staff/leave-requests/{request_id}/review")
async def review_leave_request(
    request_id: str,
    body: StaffLeaveReviewRequest,
    tenant: TenantContext = Depends(PermissionChecker("user.write")),
    db: AsyncSession = Depends(get_db)
):
    for l in _STAFF_LEAVES:
        if l["id"] == request_id:
            l["status"] = body.status
            l["admin_comment"] = body.admin_comment
            return success_response(l, "İzin talebi değerlendirildi")
    raise NotFoundException("İzin talebi bulunamadı")


# ==================== 8. GÜNLÜK KARNE (DAILY REPORTS) ====================

@router.get("/api/daily-reports")
async def list_daily_reports(
    student_id: str | None = None,
    report_date: str | None = None,
    tenant: TenantContext = Depends(PermissionChecker("student.read")),
    db: AsyncSession = Depends(get_db)
):
    items = _DAILY_REPORTS
    if student_id:
        items = [r for r in items if r["student_id"] == student_id]
    if report_date:
        items = [r for r in items if r["date"] == report_date]
    return success_response(items)


@router.post("/api/daily-reports")
async def create_daily_report(
    body: DailyReportCreate,
    tenant: TenantContext = Depends(PermissionChecker("student.write")),
    db: AsyncSession = Depends(get_db)
):
    rep = {
        "id": f"rep-{uuid.uuid4().hex[:6]}",
        "student_id": body.student_id,
        "date": body.date,
        "meal_breakfast": body.meal_breakfast,
        "meal_lunch": body.meal_lunch,
        "meal_snack": body.meal_snack,
        "sleep_status": body.sleep_status,
        "mood": body.mood,
        "activities": body.activities,
        "teacher_notes": body.teacher_notes
    }
    _DAILY_REPORTS.insert(0, rep)
    return success_response(rep, "Günlük karne kaydedildi")


@router.post("/api/daily-reports/bulk")
async def create_bulk_daily_report(
    body: BulkDailyReportCreate,
    tenant: TenantContext = Depends(PermissionChecker("student.write")),
    db: AsyncSession = Depends(get_db)
):
    return success_response(message="Sınıfın tüm öğrencileri için günlük gelişim raporu kaydedildi")


# ==================== 9. VELİ BİLDİRİMLERİ (PARENT NOTICES) ====================

@router.get("/api/parent/notices")
async def list_parent_notices(
    type: str | None = None,
    tenant: TenantContext = Depends(PermissionChecker("student.read")),
    db: AsyncSession = Depends(get_db)
):
    items = _PARENT_NOTICES
    if type:
        items = [n for n in items if n["type"] == type]
    return success_response(items)


@router.post("/api/parent/notices")
async def create_parent_notice(
    body: ParentNoticeCreate,
    tenant: TenantContext = Depends(PermissionChecker("student.write")),
    db: AsyncSession = Depends(get_db)
):
    notice = {
        "id": f"notice-{uuid.uuid4().hex[:6]}",
        "student_id": body.student_id,
        "type": body.type,
        "title": body.title,
        "content": body.content,
        "details": body.details,
        "status": "RECEIVED",
        "response_notes": None,
        "created_at": datetime.now(UTC).isoformat()
    }
    _PARENT_NOTICES.insert(0, notice)
    return success_response(notice, "Veli bildirimi oluşturuldu")


@router.patch("/api/parent/notices/{notice_id}/status")
async def update_parent_notice_status(
    notice_id: str,
    body: ParentNoticeStatusUpdate,
    tenant: TenantContext = Depends(PermissionChecker("student.write")),
    db: AsyncSession = Depends(get_db)
):
    for n in _PARENT_NOTICES:
        if n["id"] == notice_id:
            n["status"] = body.status
            n["response_notes"] = body.response_notes
            return success_response(n, "Bildirim durumu güncellendi")
    raise NotFoundException("Bildirim bulunamadı")


# ==================== 10. DERS PROGRAMI (CLASS SCHEDULE) ====================

@router.get("/api/classes/{class_id}/schedule")
async def get_class_schedule(
    class_id: str,
    tenant: TenantContext = Depends(PermissionChecker("class.read")),
    db: AsyncSession = Depends(get_db)
):
    schedule = _CLASS_SCHEDULES.get(class_id, _CLASS_SCHEDULES.get("cls-001", []))
    return success_response(schedule)


@router.put("/api/classes/{class_id}/schedule")
async def update_class_schedule(
    class_id: str,
    body: ClassScheduleUpdate,
    tenant: TenantContext = Depends(PermissionChecker("class.write")),
    db: AsyncSession = Depends(get_db)
):
    _CLASS_SCHEDULES[class_id] = body.schedule_data
    return success_response(body.schedule_data, "Ders programı güncellendi")


@router.get("/api/teachers/{teacher_id}/schedule")
async def get_teacher_schedule(
    teacher_id: str,
    tenant: TenantContext = Depends(PermissionChecker("user.read")),
    db: AsyncSession = Depends(get_db)
):
    schedule = [
        {"day": "Pazartesi", "periods": [{"time": "09:00 - 09:40", "class_name": "5-A", "subject": "Matematik"}, {"time": "11:30 - 12:10", "class_name": "6-B", "subject": "Matematik"}]},
        {"day": "Salı", "periods": [{"time": "10:40 - 11:20", "class_name": "5-A", "subject": "Geometri"}, {"time": "13:30 - 14:10", "class_name": "7-A", "subject": "Matematik"}]},
        {"day": "Çarşamba", "periods": [{"time": "09:00 - 09:40", "class_name": "8-A", "subject": "LGS Hazırlık"}]},
        {"day": "Perşembe", "periods": [{"time": "14:20 - 15:00", "class_name": "5-B", "subject": "Matematik"}]},
        {"day": "Cuma", "periods": [{"time": "09:50 - 10:30", "class_name": "6-A", "subject": "Matematik"}]}
    ]
    return success_response(schedule)


# ==================== 11. FİNANS ANALİTİĞİ ====================

@router.get("/api/finance/analytics")
async def get_finance_analytics(
    tenant: TenantContext = Depends(PermissionChecker("finance.read")),
    db: AsyncSession = Depends(get_db)
):
    analytics = {
        "monthly_accrued": 850000.0,
        "monthly_collected": 720000.0,
        "collection_rate_percent": 84.7,
        "total_remaining_receivable": 130000.0,
        "monthly_expenses": 285000.0,
        "net_operating_margin": 435000.0,
        "breakdown": {
            "tuition": 620000.0,
            "canteen": 45000.0,
            "transport": 110000.0,
            "books_materials": 75000.0
        },
        "expense_breakdown": {
            "salaries": 180000.0,
            "rent": 45000.0,
            "kitchen": 28000.0,
            "utilities": 18000.0,
            "materials": 14000.0
        }
    }
    return success_response(analytics)


# ==================== 12. OUTBOX & BİLDİRİM YÖNETİMİ ====================

_OUTBOX_LOGS: list[dict[str, Any]] = [
    {
        "id": "ob-001",
        "channel": "SMS",
        "recipient": "+905321112233",
        "recipient_name": "Mehmet Demir",
        "message": "Sayın Velimiz, Zeynep Demir bugün saat 08:45'te okula giriş yapmıştır.",
        "status": "DELIVERED",
        "sent_at": "2026-08-25T08:45:12Z",
        "delivery_time": "2026-08-25T08:45:15Z"
    },
    {
        "id": "ob-002",
        "channel": "WHATSAPP",
        "recipient": "+905335557788",
        "recipient_name": "Ayşe Kaya",
        "message": "Sayın Velimiz, yarın saat 14:30'daki Veli-Öğretmen randevunuz onaylanmıştır.",
        "status": "DELIVERED",
        "sent_at": "2026-08-25T11:00:00Z",
        "delivery_time": "2026-08-25T11:00:04Z"
    }
]

@router.get("/api/outbox")
async def list_outbox_logs(
    channel: str | None = None,
    status: str | None = None,
    tenant: TenantContext = Depends(PermissionChecker("notification.read")),
    db: AsyncSession = Depends(get_db)
):
    items = _OUTBOX_LOGS
    if channel:
        items = [i for i in items if i["channel"] == channel]
    if status:
        items = [i for i in items if i["status"] == status]
    return success_response(items)


@router.post("/api/outbox/retry/{outbox_id}")
async def retry_outbox_message(
    outbox_id: str,
    tenant: TenantContext = Depends(PermissionChecker("notification.write")),
    db: AsyncSession = Depends(get_db)
):
    for i in _OUTBOX_LOGS:
        if i["id"] == outbox_id:
            i["status"] = "DELIVERED"
            i["sent_at"] = datetime.now(UTC).isoformat()
            return success_response(i, "Mesaj yeniden başarıyla iletildi")
    raise NotFoundException("Kayıt bulunamadı")


@router.post("/api/webhooks/sms-status")
async def webhook_sms_status(payload: dict):
    return success_response({"received": True}, "DLR işlendi")


@router.get("/api/notifications/unread-count")
async def get_unread_notifications_count(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return success_response({"unread_count": 3})


@router.patch("/api/notifications/mark-all-read")
async def mark_all_notifications_read(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return success_response(message="Tüm bildirimler okundu olarak işaretlendi")


# ==================== 13. KULLANICI PROFİL & FCM TOKEN ====================

@router.patch("/api/users/{user_id}/fcm-token")
async def update_user_fcm_token(
    user_id: str,
    payload: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return success_response(message="FCM Token başarıyla güncellendi")


@router.put("/api/users/{user_id}/avatar")
async def update_user_avatar(
    user_id: str,
    payload: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return success_response({"avatar_url": payload.get("avatar_url")}, "Profil fotoğrafı güncellendi")

