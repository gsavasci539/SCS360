from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from typing import Optional, List
from uuid import UUID
from datetime import datetime, date, timedelta
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.permissions import PermissionChecker
from app.core.responses import success_response
from app.domain.entities.user import User
from app.core.tenant import TenantContext

router = APIRouter(prefix="/api/parent", tags=["Parent Portal"])


class ExcuseRequestCreate(BaseModel):
    start_date: date
    end_date: date
    reason_type: str = Field(..., description="ILLNESS, FAMILY, TRAVEL, OTHER")
    description: str


class MedicineRequestCreate(BaseModel):
    medicine_name: str
    dosage: str
    time_to_give: str
    instructions: Optional[str] = None


@router.get("/my-children")
async def get_parent_children(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.view_children"))
):
    """Get children of the current parent"""
    from app.infrastructure.models.models import StudentParent, Student, ClassRoom
    
    # Get parent ID from current user (assuming parent is linked to user)
    parent_result = await db.execute(
        select(StudentParent).where(StudentParent.parent_id == current_user.id)
    )
    parent_relations = parent_result.scalars().all()
    
    if not parent_relations:
        return success_response([])
    
    student_ids = [rel.student_id for rel in parent_relations]
    
    # Get student details
    students_result = await db.execute(
        select(Student, ClassRoom)
        .join(ClassRoom, Student.class_id == ClassRoom.id)
        .where(Student.id.in_(student_ids))
    )
    
    children_data = []
    for student, cls in students_result:
        children_data.append({
            "student_id": str(student.id),
            "student_number": student.student_number,
            "first_name": student.first_name,
            "last_name": student.last_name,
            "photo_url": student.photo_url,
            "class_id": str(cls.id) if cls else None,
            "class_name": cls.name if cls else None,
            "status": student.status,
            "is_primary": next((rel.is_primary for rel in parent_relations if rel.student_id == student.id), False)
        })
    
    return success_response(children_data)


@router.get("/child/{student_id}/today-status")
async def get_child_today_status(
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.view_daily_report"))
):
    """Get today's status for a specific child"""
    from app.infrastructure.models.models import (
        StudentParent, Student, AttendanceRecord, DailyDevelopmentReport
    )
    
    # Verify parent has access to this child
    parent_result = await db.execute(
        select(StudentParent).where(
            and_(
                StudentParent.parent_id == current_user.id,
                StudentParent.student_id == student_id
            )
        )
    )
    if not parent_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Bu öğrenciye erişiminiz yok")
    
    today = datetime.utcnow().date()
    day_of_week = today.strftime("%A").upper()
    
    # Get student info
    student_result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = student_result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Öğrenci bulunamadı")
    
    # Get today's attendance
    attendance_result = await db.execute(
        select(AttendanceRecord).where(
            and_(
                AttendanceRecord.student_id == student_id,
                AttendanceRecord.attendance_date == today
            )
        )
    )
    attendance = attendance_result.scalar_one_or_none()
    
    # Get today's daily report
    report_result = await db.execute(
        select(DailyDevelopmentReport).where(
            and_(
                DailyDevelopmentReport.student_id == student_id,
                DailyDevelopmentReport.date == today
            )
        )
    )
    daily_report = report_result.scalar_one_or_none()
    
    # Timetable entities are not yet persisted in this deployment.
    today_schedule = []
    
    return success_response({
        "student_id": str(student.id),
        "student_name": f"{student.first_name} {student.last_name}",
        "date": today.isoformat(),
        "attendance": {
            "status": attendance.status if attendance else None,
            "check_in_time": attendance.check_in_time.strftime("%H:%M") if attendance and attendance.check_in_time else None
        } if attendance else None,
        "daily_report": {
            "meal_status": daily_report.meal_status,
            "sleep_status": daily_report.sleep_status,
            "mood": daily_report.mood,
            "activities": daily_report.activities,
            "teacher_notes": daily_report.teacher_notes
        } if daily_report else None,
        "today_schedule": today_schedule
    })


@router.get("/child/{student_id}/timeline")
async def get_child_timeline(
    student_id: UUID,
    date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.view_daily_report"))
):
    """Get timeline for a specific child on a specific date"""
    from app.infrastructure.models.models import StudentParent, Student
    
    # Verify parent has access to this child
    parent_result = await db.execute(
        select(StudentParent).where(
            and_(
                StudentParent.parent_id == current_user.id,
                StudentParent.student_id == student_id
            )
        )
    )
    if not parent_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Bu öğrenciye erişiminiz yok")
    
    target_date = date or datetime.utcnow().date()
    
    # Get student info
    student_result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = student_result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Öğrenci bulunamadı")
    
    # This would be expanded to include various timeline events
    # For now, returning basic structure
    return success_response({
        "student_id": str(student.id),
        "student_name": f"{student.first_name} {student.last_name}",
        "date": target_date.isoformat(),
        "events": []  # Would include attendance, meals, activities, etc.
    })


@router.post("/child/{student_id}/excuse-request")
async def create_excuse_request(
    student_id: UUID,
    excuse_request: ExcuseRequestCreate,
    document_file: Optional[UploadFile] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.send_excuse"))
):
    """Create an excuse request for a child"""
    from app.infrastructure.models.models import StudentParent
    
    # Verify parent has access to this child
    parent_result = await db.execute(
        select(StudentParent).where(
            and_(
                StudentParent.parent_id == current_user.id,
                StudentParent.student_id == student_id
            )
        )
    )
    if not parent_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Bu öğrenciye erişiminiz yok")
    
    # This would create an excuse request record
    # For now, returning success response
    document_path = None
    if document_file:
        # Handle file upload
        document_path = f"/uploads/{document_file.filename}"
    
    return success_response({
        "student_id": str(student_id),
        "start_date": excuse_request.start_date.isoformat(),
        "end_date": excuse_request.end_date.isoformat(),
        "reason_type": excuse_request.reason_type,
        "description": excuse_request.description,
        "document_path": document_path,
        "status": "PENDING",
        "created_at": datetime.utcnow().isoformat()
    }, "Mazeret talebi oluşturuldu")


@router.get("/child/{student_id}/financial-invoices")
async def get_child_financial_invoices(
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.view_finances"))
):
    """Get financial invoices for a specific child"""
    from app.infrastructure.models.models import StudentParent, Debt
    
    # Verify parent has access to this child
    parent_result = await db.execute(
        select(StudentParent).where(
            and_(
                StudentParent.parent_id == current_user.id,
                StudentParent.student_id == student_id
            )
        )
    )
    if not parent_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Bu öğrenciye erişiminiz yok")
    
    # Get debts for this student
    debt_result = await db.execute(
        select(Debt).where(Debt.student_id == student_id)
    )
    debts = debt_result.scalars().all()
    
    invoices_data = []
    for debt in debts:
        invoices_data.append({
            "debt_id": str(debt.id),
            "debt_type": debt.debt_type,
            "description": debt.description,
            "amount": float(debt.amount),
            "paid_amount": float(debt.paid_amount),
            "remaining_amount": float(debt.remaining_amount),
            "status": debt.status,
            "due_date": debt.due_date.isoformat() if debt.due_date else None
        })
    
    total_remaining = sum(d["remaining_amount"] for d in invoices_data)
    
    return success_response({
        "student_id": str(student_id),
        "total_remaining": total_remaining,
        "invoices": invoices_data
    })


@router.post("/payments/checkout-session")
async def create_payment_checkout_session(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.make_payment"))
):
    """Create a payment checkout session for online payment"""
    from app.infrastructure.models.models import Debt
    
    # Get debt details
    debt_result = await db.execute(
        select(Debt).where(Debt.id == invoice_id)
    )
    debt = debt_result.scalar_one_or_none()
    
    if not debt:
        raise HTTPException(status_code=404, detail="Fatura bulunamadı")
    
    # This would integrate with a payment gateway (Stripe, etc.)
    # For now, returning a mock response
    return success_response({
        "checkout_url": f"https://payment-gateway.example.com/checkout/{invoice_id}",
        "session_id": f"session_{invoice_id}",
        "amount": float(debt.remaining_amount),
        "currency": "TRY",
        "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat()
    }, "Ödeme oturumu oluşturuldu")


@router.get("/child/{student_id}/medicine-requests")
async def get_child_medicine_requests(
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.view_children"))
):
    """Get medicine requests for a specific child"""
    from app.infrastructure.models.models import StudentParent
    
    # Verify parent has access to this child
    parent_result = await db.execute(
        select(StudentParent).where(
            and_(
                StudentParent.parent_id == current_user.id,
                StudentParent.student_id == student_id
            )
        )
    )
    if not parent_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Bu öğrenciye erişiminiz yok")
    
    # This would retrieve medicine requests from database
    # For now, returning empty list
    return success_response({
        "student_id": str(student_id),
        "medicine_requests": []
    })


@router.post("/child/{student_id}/medicine-requests")
async def create_medicine_request(
    student_id: UUID,
    medicine_request: MedicineRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.medicine_request"))
):
    """Create a medicine request for a child"""
    from app.infrastructure.models.models import StudentParent

    # Verify parent has access to this child
    parent_result = await db.execute(
        select(StudentParent).where(
            and_(
                StudentParent.parent_id == current_user.id,
                StudentParent.student_id == student_id
            )
        )
    )
    if not parent_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Bu öğrenciye erişiminiz yok")

    # This would create a medicine request record
    # For now, returning success response
    return success_response({
        "student_id": str(student_id),
        "medicine_name": medicine_request.medicine_name,
        "dosage": medicine_request.dosage,
        "time_to_give": medicine_request.time_to_give,
        "instructions": medicine_request.instructions,
        "status": "PENDING",
        "created_at": datetime.utcnow().isoformat()
    }, "İlaç talebi oluşturuldu")


@router.get("/child/{student_id}/attendance")
async def get_child_attendance_calendar(
    student_id: UUID,
    year: int = Query(..., description="Year for attendance calendar"),
    month: int = Query(..., ge=1, le=12, description="Month for attendance calendar"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.view_attendance"))
):
    """Get attendance calendar for a specific child"""
    from app.infrastructure.models.models import StudentParent, AttendanceRecord
    from calendar import monthrange
    from datetime import timedelta

    # Verify parent has access to this child
    parent_result = await db.execute(
        select(StudentParent).where(
            and_(
                StudentParent.parent_id == current_user.id,
                StudentParent.student_id == student_id
            )
        )
    )
    if not parent_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Bu öğrenciye erişiminiz yok")

    # Get the first and last day of the month
    first_day = date(year, month, 1)
    last_day = date(year, month, monthrange(year, month)[1])

    # Get attendance records for the month
    result = await db.execute(
        select(AttendanceRecord).where(
            and_(
                AttendanceRecord.student_id == student_id,
                AttendanceRecord.attendance_date >= first_day,
                AttendanceRecord.attendance_date <= last_day
            )
        ).order_by(AttendanceRecord.attendance_date)
    )
    attendance_records = result.scalars().all()

    # Build calendar data
    calendar_data = {}
    for record in attendance_records:
        day = record.attendance_date.day
        calendar_data[day] = {
            "date": record.attendance_date.isoformat(),
            "status": record.status,  # PRESENT, ABSENT, LATE, EXCUSED
            "check_in_time": record.check_in_time.strftime("%H:%M") if record.check_in_time else None,
            "check_out_time": record.check_out_time.strftime("%H:%M") if record.check_out_time else None,
            "note": record.note
        }

    # Fill missing days with no data
    for day in range(1, monthrange(year, month)[1] + 1):
        if day not in calendar_data:
            calendar_data[day] = {
                "date": date(year, month, day).isoformat(),
                "status": None,
                "check_in_time": None,
                "check_out_time": None,
                "note": None
            }

    # Calculate summary
    summary = {
        "present": len([r for r in attendance_records if r.status == "PRESENT"]),
        "absent": len([r for r in attendance_records if r.status == "ABSENT"]),
        "late": len([r for r in attendance_records if r.status == "LATE"]),
        "excused": len([r for r in attendance_records if r.status == "EXCUSED"]),
        "total": len(attendance_records)
    }

    return success_response({
        "student_id": str(student_id),
        "year": year,
        "month": month,
        "calendar": calendar_data,
        "summary": summary
    })


@router.get("/child/{student_id}/grades")
async def get_child_grades(
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.view_children"))
):
    """Get academic grades for a specific child"""
    from app.infrastructure.models.models import StudentParent, Student
    
    # Verify parent has access to this child
    parent_result = await db.execute(
        select(StudentParent).where(
            and_(
                StudentParent.parent_id == current_user.id,
                StudentParent.student_id == student_id
            )
        )
    )
    if not parent_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Bu öğrenciye erişiminiz yok")
    
    # Get student info
    student_result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = student_result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Öğrenci bulunamadı")
    
    # Sample grades data (would be retrieved from database in production)
    grades_data = [
        {
            "subject": "Matematik",
            "exam_type": "Yazılı Sınav",
            "score": 85,
            "exam_date": "2024-09-01",
            "status": "COMPLETED"
        },
        {
            "subject": "Türkçe",
            "exam_type": "Yazılı Sınav",
            "score": 92,
            "exam_date": "2024-09-05",
            "status": "COMPLETED"
        },
        {
            "subject": "Fen Bilimleri",
            "exam_type": "Proje",
            "score": 78,
            "exam_date": "2024-09-10",
            "status": "COMPLETED"
        },
        {
            "subject": "Sosyal Bilgiler",
            "exam_type": "Yazılı Sınav",
            "score": 88,
            "exam_date": "2024-09-12",
            "status": "COMPLETED"
        },
        {
            "subject": "İngilizce",
            "exam_type": "Sözlü Sınav",
            "score": 95,
            "exam_date": "2024-09-15",
            "status": "COMPLETED"
        }
    ]
    
    return success_response(grades_data)


@router.get("/child/{student_id}/schedule")
async def get_child_schedule(
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.view_children"))
):
    """Get weekly schedule for a specific child"""
    from app.infrastructure.models.models import StudentParent, Student
    
    # Verify parent has access to this child
    parent_result = await db.execute(
        select(StudentParent).where(
            and_(
                StudentParent.parent_id == current_user.id,
                StudentParent.student_id == student_id
            )
        )
    )
    if not parent_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Bu öğrenciye erişiminiz yok")
    
    # Get student info
    student_result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = student_result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Öğrenci bulunamadı")
    
    # Sample schedule data
    schedule_data = [
        {
            "day_of_week": "Pazartesi",
            "lessons": [
                {"subject": "Matematik", "start_time": "08:30", "end_time": "09:15", "teacher": "Ahmet Yılmaz"},
                {"subject": "Türkçe", "start_time": "09:30", "end_time": "10:15", "teacher": "Ayşe Demir"},
                {"subject": "Fen Bilimleri", "start_time": "10:30", "end_time": "11:15", "teacher": "Mehmet Kaya"},
                {"subject": "Sosyal Bilgiler", "start_time": "11:30", "end_time": "12:15", "teacher": "Fatma Çelik"},
                {"subject": "İngilizce", "start_time": "13:30", "end_time": "14:15", "teacher": "John Smith"}
            ]
        },
        {
            "day_of_week": "Salı",
            "lessons": [
                {"subject": "Türkçe", "start_time": "08:30", "end_time": "09:15", "teacher": "Ayşe Demir"},
                {"subject": "Matematik", "start_time": "09:30", "end_time": "10:15", "teacher": "Ahmet Yılmaz"},
                {"subject": "İngilizce", "start_time": "10:30", "end_time": "11:15", "teacher": "John Smith"},
                {"subject": "Beden Eğitimi", "start_time": "11:30", "end_time": "12:15", "teacher": "Ali Öz"},
                {"subject": "Müzik", "start_time": "13:30", "end_time": "14:15", "teacher": "Zeynep Ak"}
            ]
        },
        {
            "day_of_week": "Çarşamba",
            "lessons": [
                {"subject": "Fen Bilimleri", "start_time": "08:30", "end_time": "09:15", "teacher": "Mehmet Kaya"},
                {"subject": "Sosyal Bilgiler", "start_time": "09:30", "end_time": "10:15", "teacher": "Fatma Çelik"},
                {"subject": "Matematik", "start_time": "10:30", "end_time": "11:15", "teacher": "Ahmet Yılmaz"},
                {"subject": "Türkçe", "start_time": "11:30", "end_time": "12:15", "teacher": "Ayşe Demir"},
                {"subject": "Görsel Sanatlar", "start_time": "13:30", "end_time": "14:15", "teacher": "Emre Yıldız"}
            ]
        },
        {
            "day_of_week": "Perşembe",
            "lessons": [
                {"subject": "İngilizce", "start_time": "08:30", "end_time": "09:15", "teacher": "John Smith"},
                {"subject": "Fen Bilimleri", "start_time": "09:30", "end_time": "10:15", "teacher": "Mehmet Kaya"},
                {"subject": "Türkçe", "start_time": "10:30", "end_time": "11:15", "teacher": "Ayşe Demir"},
                {"subject": "Matematik", "start_time": "11:30", "end_time": "12:15", "teacher": "Ahmet Yılmaz"},
                {"subject": "Bilişim Teknolojileri", "start_time": "13:30", "end_time": "14:15", "teacher": "Caner Erkin"}
            ]
        },
        {
            "day_of_week": "Cuma",
            "lessons": [
                {"subject": "Sosyal Bilgiler", "start_time": "08:30", "end_time": "09:15", "teacher": "Fatma Çelik"},
                {"subject": "İngilizce", "start_time": "09:30", "end_time": "10:15", "teacher": "John Smith"},
                {"subject": "Fen Bilimleri", "start_time": "10:30", "end_time": "11:15", "teacher": "Mehmet Kaya"},
                {"subject": "Matematik", "start_time": "11:30", "end_time": "12:15", "teacher": "Ahmet Yılmaz"},
                {"subject": "Rehberlik", "start_time": "13:30", "end_time": "14:15", "teacher": "Selin Arslan"}
            ]
        }
    ]
    
    return success_response(schedule_data)


@router.get("/child/{student_id}/homework")
async def get_child_homework(
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.view_children"))
):
    """Get homework assignments for a specific child"""
    from app.infrastructure.models.models import StudentParent, Student
    
    # Verify parent has access to this child
    parent_result = await db.execute(
        select(StudentParent).where(
            and_(
                StudentParent.parent_id == current_user.id,
                StudentParent.student_id == student_id
            )
        )
    )
    if not parent_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Bu öğrenciye erişiminiz yok")
    
    # Get student info
    student_result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = student_result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Öğrenci bulunamadı")
    
    # Sample homework data
    homework_data = [
        {
            "subject": "Matematik",
            "title": "Cebirsel İfadeler Ödevi",
            "description": "Sayfa 45-48 arası problemleri çözün ve sonuçları tabloya işleyin",
            "due_date": "2024-09-20",
            "status": "PENDING"
        },
        {
            "subject": "Türkçe",
            "title": "Kompozisyon Yazma",
            "description": "Okul tatili hakkında 200 kelimelik kompozisyon yazın",
            "due_date": "2024-09-22",
            "status": "PENDING"
        },
        {
            "subject": "Fen Bilimleri",
            "title": "Elektrik Devresi Projesi",
            "description": "Basit bir elektrik devresi yapın ve çalışma prensibini açıklayan rapor hazırlayın",
            "due_date": "2024-09-25",
            "status": "PENDING"
        },
        {
            "subject": "Sosyal Bilgiler",
            "title": "Tarih Araştırması",
            "description": "Türkiye Cumhuriyeti'nin kuruluşu hakkında araştırma yapın",
            "due_date": "2024-09-18",
            "status": "COMPLETED"
        },
        {
            "subject": "İngilizce",
            "title": "Vocabulary Quiz",
            "description": "Haftalık kelime listesini öğrenin ve quiz'e hazırlanın",
            "due_date": "2024-09-19",
            "status": "PENDING"
        }
    ]
    
    return success_response(homework_data)


@router.get("/child/{student_id}/materials")
async def get_child_materials(
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.view_children"))
):
    """Get educational materials for a specific child"""
    from app.infrastructure.models.models import StudentParent, Student
    
    # Verify parent has access to this child
    parent_result = await db.execute(
        select(StudentParent).where(
            and_(
                StudentParent.parent_id == current_user.id,
                StudentParent.student_id == student_id
            )
        )
    )
    if not parent_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Bu öğrenciye erişiminiz yok")
    
    # Get student info
    student_result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = student_result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Öğrenci bulunamadı")
    
    # Sample materials data
    materials_data = [
        {
            "title": "Matematik Ders Notları - 1. Ünite",
            "subject": "Matematik",
            "type": "PDF",
            "file_url": "/uploads/math_notes_unit1.pdf"
        },
        {
            "title": "Türkçe Gramer Kitapçığı",
            "subject": "Türkçe",
            "type": "PDF",
            "file_url": "/uploads/turkish_grammar.pdf"
        },
        {
            "title": "Fen Bilimleri Laboratuvar Rehberi",
            "subject": "Fen Bilimleri",
            "type": "PDF",
            "file_url": "/uploads/science_lab_guide.pdf"
        },
        {
            "title": "Sosyal Bilgiler Atlası",
            "subject": "Sosyal Bilgiler",
            "type": "PDF",
            "file_url": "/uploads/social_studies_atlas.pdf"
        },
        {
            "title": "İngilizce Kelime Kartları",
            "subject": "İngilizce",
            "type": "PDF",
            "file_url": "/uploads/english_flashcards.pdf"
        },
        {
            "title": "Matematik Alıştırma Soruları",
            "subject": "Matematik",
            "type": "DOCX",
            "file_url": "/uploads/math_exercises.docx"
        }
    ]
    
    return success_response(materials_data)


@router.get("/child/{student_id}/communications")
async def get_child_communications(
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.view_children"))
):
    """Get communication history for a specific child"""
    from app.infrastructure.models.models import StudentParent, Student
    
    # Verify parent has access to this child
    parent_result = await db.execute(
        select(StudentParent).where(
            and_(
                StudentParent.parent_id == current_user.id,
                StudentParent.student_id == student_id
            )
        )
    )
    if not parent_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Bu öğrenciye erişiminiz yok")
    
    # Get student info
    student_result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = student_result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Öğrenci bulunamadı")
    
    # Sample communications data
    communications_data = [
        {
            "teacher_name": "Ayşe Demir",
            "date": "2024-09-15",
            "subject": "Türkçe Dersi Performansı",
            "message": "Çocuğunuz Türkçe derslerinde çok başarılı. Okuma ve yazma becerileri gelişim gösteriyor. Evde de bol bol kitap okumasını teşvik edebiliriz."
        },
        {
            "teacher_name": "Ahmet Yılmaz",
            "date": "2024-09-12",
            "subject": "Matematik Ödev Hakkında",
            "message": "Son matematik ödevini zamanında ve eksiksiz tamamladı. Problem çözme yeteneği gelişiyor. Ders aktif katılımı çok iyi."
        },
        {
            "teacher_name": "Mehmet Kaya",
            "date": "2024-09-10",
            "subject": "Fen Bilimleri Projesi",
            "message": "Fen bilimleri projesinde gösterdiği çaba için tebrik ederim. Grup çalışmasında liderlik rolü üstlendi ve başarılı oldu."
        },
        {
            "teacher_name": "Fatma Çelik",
            "date": "2024-09-08",
            "subject": "Sosyal Gelişim",
            "message": "Sınıf içindeki arkadaşlarıyla ilişkileri çok iyi. Grup çalışmalarında işbirliği yapmayı seviyor ve arkadaşlarına yardım ediyor."
        },
        {
            "teacher_name": "John Smith",
            "date": "2024-09-05",
            "subject": "İngilizce Konuşma Pratiği",
            "message": "İngilizce konuşma pratiğinde büyük ilerleme kaydetti. Kelime dağarcığı genişledi ve daha rahat konuşmaya başladı."
        }
    ]
    
    return success_response(communications_data)


@router.get("/child/{student_id}/announcements")
async def get_child_announcements(
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.view_children"))
):
    """Get school announcements for a specific child"""
    from app.infrastructure.models.models import StudentParent, Student
    
    # Verify parent has access to this child
    parent_result = await db.execute(
        select(StudentParent).where(
            and_(
                StudentParent.parent_id == current_user.id,
                StudentParent.student_id == student_id
            )
        )
    )
    if not parent_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Bu öğrenciye erişiminiz yok")
    
    # Get student info
    student_result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = student_result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Öğrenci bulunamadı")
    
    # Sample announcements data
    announcements_data = [
        {
            "title": "Okul Açılış Töreni Duyurusu",
            "category": "Okul Duyurusu",
            "date": "2024-09-01",
            "content": "2024-2025 eğitim öğretim yılı açılış töreni 15 Eylül Pazar günü saat 10:00'da okul bahçesinde yapılacaktır. Tüm velilerimiz ve öğrencilerimiz davetlidir."
        },
        {
            "title": "Veli Toplantısı",
            "category": "Sınıf Duyurusu",
            "date": "2024-09-10",
            "content": "Sınıf veli toplantısı 20 Eylül Cuma günü saat 18:00'da sınıf odasında yapılacaktır. Katılımınız önemlidir."
        },
        {
            "title": "Kuş Gribi Aşısı Duyurusu",
            "category": "Sağlık Duyurusu",
            "date": "2024-09-12",
            "content": "Okul sağlık birimi tarafından kuş gribi aşısı uygulaması 25 Eylül Salı günü yapılacaktır. Aşı olmak isteyen velilerimiz formu doldurup göndermelidir."
        },
        {
            "title": "Kırtasiye Listesi Güncellemesi",
            "category": "Akademik Duyuru",
            "date": "2024-09-08",
            "content": "2024-2025 eğitim yılı kırtasiye listesi güncellenmiştir. Lütfen web sitemizden güncel listeyi kontrol ediniz."
        },
        {
            "title": "Okul Servisi Ücret Duyurusu",
            "category": "Finans Duyurusu",
            "date": "2024-09-05",
            "content": "2024-2025 eğitim yılı okul servisi ücretleri belirlenmiştir. Ödemeler Eylül sonuna kadar yapılmalıdır."
        }
    ]
    
    return success_response(announcements_data)


@router.get("/child/{student_id}/activities")
async def get_child_activities(
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.view_children"))
):
    """Get club activities for a specific child"""
    from app.infrastructure.models.models import StudentParent, Student
    
    # Verify parent has access to this child
    parent_result = await db.execute(
        select(StudentParent).where(
            and_(
                StudentParent.parent_id == current_user.id,
                StudentParent.student_id == student_id
            )
        )
    )
    if not parent_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Bu öğrenciye erişiminiz yok")
    
    # Get student info
    student_result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = student_result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Öğrenci bulunamadı")
    
    # Sample activities data
    activities_data = [
        {
            "name": "Satranç Kulübü",
            "type": "Akademik Kulüp",
            "day": "Salı",
            "time": "15:30-16:30"
        },
        {
            "name": "Futbol Takımı",
            "type": "Spor Kulübü",
            "day": "Çarşamba",
            "time": "15:30-17:00"
        },
        {
            "name": "Resim Atölyesi",
            "type": "Sanat Kulübü",
            "day": "Perşembe",
            "time": "15:30-16:30"
        },
        {
            "name": "Müzik Korosu",
            "type": "Sanat Kulübü",
            "day": "Cuma",
            "time": "15:30-16:30"
        },
        {
            "name": "Robotik Kulübü",
            "type": "STEM Kulübü",
            "day": "Pazartesi",
            "time": "15:30-16:30"
        },
        {
            "name": "Drama Kulübü",
            "type": "Sanat Kulübü",
            "day": "Cuma",
            "time": "14:30-15:30"
        }
    ]
    
    return success_response(activities_data)


@router.get("/child/{student_id}/weekly-reports")
async def get_child_weekly_reports(
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.view_children"))
):
    """Get weekly reports for a specific child"""
    from app.infrastructure.models.models import StudentParent, Student
    
    # Verify parent has access to this child
    parent_result = await db.execute(
        select(StudentParent).where(
            and_(
                StudentParent.parent_id == current_user.id,
                StudentParent.student_id == student_id
            )
        )
    )
    if not parent_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Bu öğrenciye erişiminiz yok")
    
    # Get student info
    student_result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = student_result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Öğrenci bulunamadı")
    
    # Sample weekly reports data
    weekly_reports_data = [
        {
            "week_title": "Eylül - 2. Hafta",
            "report_date": "2024-09-15",
            "teacher_name": "Ayşe Demir",
            "summary": "Bu hafta öğrencimiz tüm derslerde başarılı bir performans gösterdi. Özellikle matematik ve fen bilimleri derslerinde büyük ilerleme kaydetti. Ödevlerini zamanında ve eksiksiz tamamladı.",
            "behavior": "Sınıf kurallarına uyuyor, arkadaşlarıyla iyi ilişkiler kuruyor, derslere aktif katılım sağlıyor.",
            "social": "Grup çalışmalarında işbirliği yapıyor, arkadaşlarına yardım ediyor, liderlik özellikleri gösteriyor."
        },
        {
            "week_title": "Eylül - 1. Hafta",
            "report_date": "2024-09-08",
            "teacher_name": "Ayşe Demir",
            "summary": "Okula adaptasyon süreci başarıyla tamamlandı. Derslere katılım yüksek, ödevlerinizi düzenli yapıyor. Okuma alışkanlığı gelişmekte.",
            "behavior": "Disiplinli ve düzenli, öğretmenlerini dinliyor, sınıf kurallarına uyuyor.",
            "social": "Arkadaşlarıyla tanışma süreci olumlu, yeni ortamlara hızlı uyum sağlıyor."
        },
        {
            "week_title": "Ağustos - 4. Hafta",
            "report_date": "2024-09-01",
            "teacher_name": "Mehmet Kaya",
            "summary": "Yeni eğitim öğretim yılına hazır bir şekilde başladı. Yaz tatili boyunca okuma alışkanlığını korumuş, matematik temellerini güçlendirmiş.",
            "behavior": "Motivasyonu yüksek, hedeflerine odaklı, düzenli ve çalışkan.",
            "social": "Aile ilişkileri güçlü, kardeşleriyle iyi geçiniyor, sorumluluk bilinci gelişmiş."
        }
    ]
    
    return success_response(weekly_reports_data)


@router.get("/child/{student_id}/teachers")
async def get_child_teachers(
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.view_children"))
):
    """Get teachers for a specific child"""
    from app.infrastructure.models.models import StudentParent, Student, ClassTeacher, User
    
    # Verify parent has access to this child
    parent_result = await db.execute(
        select(StudentParent).where(
            and_(
                StudentParent.parent_id == current_user.id,
                StudentParent.student_id == student_id
            )
        )
    )
    if not parent_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Bu öğrenciye erişiminiz yok")
    
    # Get student info
    student_result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = student_result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Öğrenci bulunamadı")
    
    # Get class teachers
    if student.class_id:
        class_teachers_result = await db.execute(
            select(ClassTeacher, User).join(User, ClassTeacher.user_id == User.id)
            .where(ClassTeacher.class_id == student.class_id)
        )
        
        teachers_data = []
        for class_teacher, user in class_teachers_result:
            teachers_data.append({
                "id": str(user.id),
                "first_name": user.first_name,
                "last_name": user.last_name,
                "subject": "Sınıf Öğretmeni" if class_teacher.is_primary else "Ders Öğretmeni"
            })
        
        if teachers_data:
            return success_response(teachers_data)
    
    # Sample teachers data if no class assigned or no teachers found
    return success_response([])


class MessageCreate(BaseModel):
    teacher_id: str
    subject: str
    message: str


@router.post("/child/{student_id}/send-message")
async def send_message_to_teacher(
    student_id: UUID,
    message_data: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.send_message"))
):
    """Send a message to a teacher"""
    from app.infrastructure.models.models import StudentParent, Student, ChatMessage
    
    # Verify parent has access to this child
    parent_result = await db.execute(
        select(StudentParent).where(
            and_(
                StudentParent.parent_id == current_user.id,
                StudentParent.student_id == student_id
            )
        )
    )
    if not parent_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Bu öğrenciye erişiminiz yok")
    
    # Get student info
    student_result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = student_result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Öğrenci bulunamadı")
    
    # Create chat message
    new_message = ChatMessage(
        sender_id=current_user.id,
        receiver_id=UUID(message_data.teacher_id),
        class_id=student.class_id,
        content=f"Konu: {message_data.subject}\n\n{message_data.message}",
        is_read=False
    )
    
    db.add(new_message)
    await db.commit()
    
    return success_response({
        "message_id": str(new_message.id),
        "sender_id": str(current_user.id),
        "receiver_id": message_data.teacher_id,
        "subject": message_data.subject,
        "message": message_data.message,
        "sent_at": new_message.sent_at.isoformat()
    }, "Mesaj başarıyla gönderildi")


@router.get("/child/{student_id}/chat/{teacher_id}")
async def get_chat_messages(
    student_id: UUID,
    teacher_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get chat messages between parent and teacher"""
    from app.infrastructure.models.models import StudentParent, Student, ChatMessage, User
    
    # Verify parent has access to this child
    parent_result = await db.execute(
        select(StudentParent).where(
            and_(
                StudentParent.parent_id == current_user.id,
                StudentParent.student_id == student_id
            )
        )
    )
    if not parent_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Bu öğrenciye erişiminiz yok")
    
    # Get student info
    student_result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = student_result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Öğrenci bulunamadı")
    
    # Get chat messages
    messages_result = await db.execute(
        select(ChatMessage, User).join(User, ChatMessage.sender_id == User.id)
        .where(
            and_(
                ChatMessage.class_id == student.class_id,
                or_(
                    and_(ChatMessage.sender_id == current_user.id, ChatMessage.receiver_id == UUID(teacher_id)),
                    and_(ChatMessage.sender_id == UUID(teacher_id), ChatMessage.receiver_id == current_user.id)
                )
            )
        )
        .order_by(ChatMessage.sent_at)
    )
    
    messages_data = []
    for message, user in messages_result:
        messages_data.append({
            "id": str(message.id),
            "sender_id": str(message.sender_id),
            "receiver_id": str(message.receiver_id),
            "content": message.content,
            "is_read": message.is_read,
            "sent_at": message.sent_at.isoformat(),
            "sender_name": f"{user.first_name} {user.last_name}",
            "is_current_user": message.sender_id == current_user.id
        })
    
    return success_response(messages_data)


class ChatMessageCreate(BaseModel):
    message: str


@router.post("/child/{student_id}/chat/{teacher_id}")
async def send_chat_message(
    student_id: UUID,
    teacher_id: str,
    message_data: ChatMessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send a chat message to teacher"""
    from app.infrastructure.models.models import StudentParent, Student, ChatMessage
    
    # Verify parent has access to this child
    parent_result = await db.execute(
        select(StudentParent).where(
            and_(
                StudentParent.parent_id == current_user.id,
                StudentParent.student_id == student_id
            )
        )
    )
    if not parent_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Bu öğrenciye erişiminiz yok")
    
    # Get student info
    student_result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = student_result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Öğrenci bulunamadı")
    
    # Create chat message
    new_message = ChatMessage(
        sender_id=current_user.id,
        receiver_id=UUID(teacher_id),
        class_id=student.class_id,
        content=message_data.message,
        is_read=False
    )
    
    db.add(new_message)
    await db.commit()
    
    return success_response({
        "message_id": str(new_message.id),
        "sender_id": str(current_user.id),
        "receiver_id": teacher_id,
        "content": message_data.message,
        "sent_at": new_message.sent_at.isoformat()
    }, "Mesaj gönderildi")
