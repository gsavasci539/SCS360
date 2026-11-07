from app.core.dates import school_today
from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File, Request, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from typing import Optional, List, Literal
from uuid import UUID
from datetime import datetime, date, timedelta
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_tenant_context
from app.core.permissions import PermissionChecker
from app.core.responses import success_response
from app.domain.entities.user import User
from app.core.tenant import TenantContext
from app.core.student_access import require_parent_child_access, require_teacher_for_student
from app.core.parent_purpose import activate_parent_scope
from app.routers.payments import IyzicoPaymentRequest

router = APIRouter(prefix="/api/parent", tags=["Parent Portal"], dependencies=[Depends(activate_parent_scope)])


from app.domain.entities.student_teacher import ChatbotQueryRequest


@router.post("/chatbot")
async def parent_chatbot(
    body: ChatbotQueryRequest, db: AsyncSession = Depends(get_db, scope="function"), current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_tenant_context),
):
    if not tenant.parent_portal:
        raise HTTPException(403, "Bu alan bağlı veliler içindir")
    from app.routers.chatbot import _process_chatbot_query
    return success_response(await _process_chatbot_query(body, db, current_user))


@router.get("/child/{student_id}/insights")
async def parent_student_insights(
    student_id: UUID, context: str = Query("dashboard", max_length=30),
    db: AsyncSession = Depends(get_db, scope="function"), current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.view_children")),
):
    from app.application.services.student_insights import for_student
    await require_parent_child_access(db, current_user.id, student_id)
    return success_response(await for_student(db, tenant, student_id, context))


class ExcuseRequestCreate(BaseModel):
    start_date: date
    end_date: date
    reason_type: Literal["ILLNESS", "FAMILY", "TRAVEL", "OTHER"]
    description: str = Field(..., min_length=1, max_length=2000)


class MedicineRequestCreate(BaseModel):
    model_config = {"str_strip_whitespace": True}
    medicine_name: str = Field(min_length=1, max_length=255)
    dosage: str = Field(min_length=1, max_length=100)
    time_to_give: str = Field(min_length=1, max_length=100)
    instructions: Optional[str] = Field(None, max_length=1000)


class MessageCreate(BaseModel):
    teacher_id: UUID
    subject: str = Field(min_length=1, max_length=150)
    message: str = Field(min_length=1, max_length=10000)


class GuardianDecision(BaseModel):
    model_config = {"extra": "forbid", "str_strip_whitespace": True}
    consent_status: Literal["APPROVED", "REJECTED"]
    acknowledged: Literal[True]
    document_version: str = Field(min_length=1, max_length=20)
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    signed_name: str = Field(min_length=2, max_length=200)


class GuardianSurveyResponse(BaseModel):
    model_config = {"extra": "forbid"}
    response_data: dict = Field(max_length=100)


@router.get("/child/{student_id}/surveys")
async def guardian_surveys(student_id: UUID, limit: int = Query(21, ge=1, le=100), offset: int = Query(0, ge=0),
                           db: AsyncSession = Depends(get_db, scope="function"), current_user: User = Depends(get_current_user),
                           tenant: TenantContext = Depends(PermissionChecker("parent.view_children"))):
    from app.application.services.survey_service import parent_surveys
    return success_response(await parent_surveys(db, current_user, student_id, limit, offset))


@router.post("/child/{student_id}/surveys/{survey_id}/respond")
async def guardian_survey_response(student_id: UUID, survey_id: UUID, response: GuardianSurveyResponse,
                                   db: AsyncSession = Depends(get_db, scope="function"), current_user: User = Depends(get_current_user),
                                   tenant: TenantContext = Depends(PermissionChecker("parent.respond_survey"))):
    from app.application.services.survey_service import respond
    result = await respond(db, survey_id, current_user.id, response.response_data, parent_user=current_user, student_id=student_id)
    await db.commit()
    return success_response(result)


@router.get("/child/{student_id}/consents")
async def guardian_documents(student_id: UUID, limit: int = Query(21, ge=1, le=100), offset: int = Query(0, ge=0),
                             db: AsyncSession = Depends(get_db, scope="function"), current_user: User = Depends(get_current_user),
                             tenant: TenantContext = Depends(PermissionChecker("parent.view_children"))):
    from app.application.services.consent_service import parent_documents
    return success_response(await parent_documents(db, current_user, student_id, limit, offset))


@router.post("/child/{student_id}/consents/{document_id}")
async def guardian_decision(student_id: UUID, document_id: UUID, decision: GuardianDecision, request: Request,
                            db: AsyncSession = Depends(get_db, scope="function"), current_user: User = Depends(get_current_user),
                            tenant: TenantContext = Depends(PermissionChecker("parent.give_consent"))):
    from app.application.services import consent_service, parent_data_service
    parent, student = await parent_data_service.child(db, current_user, student_id)
    record = await consent_service.decide(db, actor_id=current_user.id, student_id=student.id,
        document_id=document_id, parent_id=parent.id, status=decision.consent_status,
        method="PARENT_PORTAL", signature=decision.signed_name, expected_version=decision.document_version,
        expected_hash=decision.content_sha256, ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:500])
    await db.commit()
    return success_response({"id": str(record.id), "consent_status": record.consent_status,
        "consented_at": consent_service.utc_iso(record.consented_at)})


@router.get("/my-children")
async def get_parent_children(
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.view_children"))
):
    """Get children of the current parent"""
    from app.infrastructure.models.models import StudentParent, Student, ClassRoom, Parent
    
    # Get parent record linked to current user
    parent_result = await db.execute(
        select(Parent).where(Parent.user_id == current_user.id,
            Parent.organization_id == current_user.organization_id, Parent.deleted_at.is_(None))
    )
    parents = parent_result.scalars().all()
    
    if not parents:
        return success_response([])
    
    # Get student-parent relationships
    parent_relations_result = await db.execute(
        select(StudentParent).where(StudentParent.parent_id.in_([parent.id for parent in parents]))
    )
    parent_relations = parent_relations_result.scalars().all()
    
    if not parent_relations:
        return success_response([])
    
    student_ids = [rel.student_id for rel in parent_relations]
    
    # Get student details
    students_result = await db.execute(
        select(Student, ClassRoom)
        .outerjoin(ClassRoom, Student.class_id == ClassRoom.id)
        .where(Student.id.in_(student_ids), Student.organization_id == current_user.organization_id,
            Student.deleted_at.is_(None))
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
            "is_primary": any(rel.is_primary for rel in parent_relations if rel.student_id == student.id)
        })
    
    return success_response(children_data)


@router.get("/child/{student_id}/today-status")
async def get_child_today_status(
    student_id: UUID, db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.view_daily_report")),
):
    from app.application.services import parent_day_service
    return success_response(await parent_day_service.today_status(db, current_user, student_id))


@router.get("/child/{student_id}/timeline")
async def get_child_timeline(
    student_id: UUID, date: Optional[date] = None, db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.view_daily_report")),
):
    from app.application.services import parent_day_service
    return success_response(await parent_day_service.timeline(db, current_user, student_id, date))


@router.post("/child/{student_id}/excuse-request")
async def create_excuse_request(
    student_id: UUID,
    excuse_request: ExcuseRequestCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.send_excuse")),
):
    from app.application.services import excuse_service
    return success_response(await excuse_service.create(db, current_user, student_id, excuse_request),
        "Mazeret talebi oluşturuldu")


@router.get("/child/{student_id}/excuse-requests")
async def list_excuse_requests(
    student_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.view_children")),
):
    from app.application.services import excuse_service
    return success_response(await excuse_service.list_for_child(db, current_user, student_id))


@router.get("/child/{student_id}/financial-invoices")
async def get_child_financial_invoices(
    student_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.view_finances"))
):
    """Get financial invoices for a specific child"""
    from app.infrastructure.models.models import StudentParent, Debt, Parent
    
    # Convert string to UUID
    try:
        student_uuid = UUID(str(student_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="Geçersiz öğrenci ID formatı")
    
    await require_parent_child_access(db, current_user.id, student_uuid)

    # Get debts for this student
    debt_result = await db.execute(
        select(Debt).where(Debt.student_id == student_uuid, Debt.deleted_at.is_(None))
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
    from app.application.services.online_payment_service import available_for
    
    return success_response({
        "student_id": str(student_id),
        "total_remaining": total_remaining,
        "online_payment_available": await available_for(db, current_user.organization_id),
        "invoices": invoices_data
    })


@router.post("/payments/initialize")
async def initialize_parent_payment(
    body: IyzicoPaymentRequest, request: Request,
    db: AsyncSession = Depends(get_db, scope="function"), current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.make_payment")),
):
    from app.application.services import online_payment_service
    from app.infrastructure.models.models import Debt
    from app.infrastructure.repositories.base import BaseRepository
    debt = await BaseRepository(db, tenant).get_by_id(body.debt_id, Debt)
    await require_parent_child_access(db, current_user.id, debt.student_id)
    return success_response(await online_payment_service.initialize(db, tenant, current_user, body,
        request.client.host if request.client else "127.0.0.1"))


@router.get("/payments/checkouts/{checkout_id}")
async def parent_checkout_status(
    checkout_id: UUID, db: AsyncSession = Depends(get_db, scope="function"), current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.make_payment")),
):
    from app.application.services import school_checkout_service
    return success_response(await school_checkout_service.status(db, tenant, checkout_id))


@router.post("/payments/checkouts/{checkout_id}/resume")
async def resume_parent_checkout(checkout_id: UUID, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("parent.make_payment"))):
    from app.application.services import school_checkout_service
    return success_response(await school_checkout_service.resume(db, tenant, checkout_id))


@router.post("/payments/checkouts/{checkout_id}/refresh")
async def refresh_parent_checkout(checkout_id: UUID, db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("parent.make_payment"))):
    from app.application.services import school_checkout_service
    return success_response(await school_checkout_service.refresh(db, tenant, checkout_id))


@router.post("/payments/checkout-session")
async def create_payment_checkout_session(
    invoice_id: UUID,
    request: Request,
    billing: dict | None = Body(None),
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.make_payment"))
):
    from app.application.services import online_payment_service
    from app.infrastructure.models.models import Debt
    from app.infrastructure.repositories.base import BaseRepository
    from app.core.exceptions import ConflictException
    debt = await BaseRepository(db, tenant).get_by_id(invoice_id, Debt)
    await require_parent_child_access(db, current_user.id, debt.student_id)
    if debt.remaining_amount <= 0:
        raise ConflictException("Bu borcun ödenecek bakiyesi yok")
    body = IyzicoPaymentRequest(debt_id=debt.id, amount=debt.remaining_amount, buyer=billing or {})
    return success_response(await online_payment_service.initialize(db, tenant, current_user, body,
        request.client.host if request.client else "127.0.0.1"))


@router.get("/child/{student_id}/medicine-requests")
async def get_child_medicine_requests(student_id: UUID, limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db, scope="function"), current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.view_children"))):
    from app.application.services.infirmary_service import medicine_request_status, instructions
    from app.domain.entities.health import MedicationSchedule
    await require_parent_child_access(db, current_user.id, student_id)
    rows = (await db.execute(select(MedicationSchedule).where(MedicationSchedule.student_id == student_id)
        .order_by(MedicationSchedule.created_at.desc(), MedicationSchedule.id).limit(limit).offset(offset))).scalars().all()
    return success_response({"student_id": str(student_id), "medicine_requests": [{"id": str(row.id),
        "student_id": str(row.student_id), "medicine_name": row.medication_name, "dosage": row.dosage,
        "time_to_give": row.frequency, "instructions": instructions(row), "status": medicine_request_status(row),
        "created_at": row.created_at.isoformat()} for row in rows]})


@router.post("/child/{student_id}/medicine-requests")
async def create_medicine_request(student_id: UUID, medicine_request: MedicineRequestCreate,
    db: AsyncSession = Depends(get_db, scope="function"), current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.medicine_request"))):
    from app.domain.entities.health import MedicationSchedule
    await require_parent_child_access(db, current_user.id, student_id)
    row = MedicationSchedule(student_id=student_id, medication_name=medicine_request.medicine_name,
        dosage=medicine_request.dosage, frequency=medicine_request.time_to_give, instruction="NOT_SPECIFIED",
        parent_notes=medicine_request.instructions, start_date=school_today(), is_active=True, request_status="PENDING",
        created_by=current_user.id)
    db.add(row); await db.commit(); await db.refresh(row)
    return success_response({"id": str(row.id), "student_id": str(row.student_id), "medicine_name": row.medication_name,
        "dosage": row.dosage, "time_to_give": row.frequency, "instructions": medicine_request.instructions,
        "status": "PENDING", "created_at": row.created_at.isoformat()}, "İlaç talebi oluşturuldu")


@router.get("/child/{student_id}/attendance")
async def get_child_attendance_calendar(
    student_id: UUID,
    year: int = Query(..., ge=1, le=9999, description="Year for attendance calendar"),
    month: int = Query(..., ge=1, le=12, description="Month for attendance calendar"),
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.view_attendance"))
):
    """Get attendance calendar for a specific child"""
    from app.infrastructure.models.models import StudentParent, AttendanceRecord, Parent
    from calendar import monthrange
    from datetime import timedelta

    # Convert string to UUID
    try:
        student_uuid = UUID(str(student_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="Geçersiz öğrenci ID formatı")

    await require_parent_child_access(db, current_user.id, student_uuid)

    # Get the first and last day of the month
    first_day = date(year, month, 1)
    last_day = date(year, month, monthrange(year, month)[1])

    # Get attendance records for the month
    result = await db.execute(
        select(AttendanceRecord).where(
            and_(
                AttendanceRecord.student_id == student_uuid, AttendanceRecord.deleted_at.is_(None),
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
            # AttendanceRecord stores the school entry time only.  Keep this
            # key for the frontend contract without reading a nonexistent ORM
            # attribute.
            "check_out_time": None,
            "note": record.notes,
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
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.view_children"))
):
    from app.application.services import parent_data_service
    return success_response(await parent_data_service.grades(db, current_user, student_id))


@router.get("/child/{student_id}/report-cards")
async def get_child_report_cards(
    student_id: UUID, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db, scope="function"), current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.view_children")),
):
    from sqlalchemy import func
    from app.application.services.exam_management import card_data
    from app.core.responses import paginate
    from app.domain.entities.exams import ReportCard
    await require_parent_child_access(db, current_user.id, student_id)
    query = select(ReportCard).where(ReportCard.student_id == student_id, ReportCard.is_published.is_(True))
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    cards = (await db.execute(query.order_by(ReportCard.academic_year.desc(), ReportCard.semester, ReportCard.id)
        .offset((page - 1) * page_size).limit(page_size))).scalars().all()
    rows = []
    for card in cards:
        row = card_data(card)
        for field in ("generated_by", "generated_by_name", "pdf_url"):
            row.pop(field, None)
        if not tenant.has_permission("parent.view_attendance"):
            row["attendance_rate"] = None
        rows.append(row)
    return success_response(paginate(rows, total, page, page_size))


@router.get("/child/{student_id}/schedule")
async def get_child_schedule(
    student_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.view_children"))
):
    from app.application.services import parent_data_service
    return success_response(await parent_data_service.schedule(db, current_user, student_id))


@router.get("/child/{student_id}/homework")
async def get_child_homework(
    student_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.view_children"))
):
    from app.application.services import parent_data_service
    return success_response(await parent_data_service.homework(db, current_user, student_id))


@router.get("/child/{student_id}/materials")
async def get_child_materials(
    student_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.view_children"))
):
    from app.application.services import parent_data_service
    return success_response(await parent_data_service.materials(db, current_user, student_id))


@router.get("/child/{student_id}/materials/{material_id}/download")
async def download_child_material(
    student_id: UUID,
    material_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.view_children")),
):
    from app.application.services import parent_data_service, material_file_service
    from app.domain.entities.materials import CourseMaterial
    from app.core.exceptions import NotFoundException
    _, student = await parent_data_service.child(db, current_user, student_id)
    material = (await db.execute(select(CourseMaterial).where(CourseMaterial.id == material_id,
        material_file_service.visible_to_child(student)))).scalar_one_or_none()
    if material is None:
        raise NotFoundException("Materyal bulunamadı")
    return await material_file_service.file_response(db, material)


@router.get("/child/{student_id}/communications")
async def get_child_communications(
    student_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.view_children"))
):
    from app.application.services import parent_data_service
    return success_response(await parent_data_service.communications(db, current_user, student_id))


@router.get("/child/{student_id}/announcements")
async def get_child_announcements(
    student_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.view_children"))
):
    from app.application.services import parent_data_service
    return success_response(await parent_data_service.announcements(db, current_user, student_id))


@router.get("/child/{student_id}/activities")
async def get_child_activities(
    student_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.view_children"))
):
    from app.application.services import parent_data_service
    return success_response(await parent_data_service.activities(db, current_user, student_id))


@router.get("/child/{student_id}/certificates")
async def list_child_certificates(student_id: UUID, limit: int = Query(100, ge=1, le=200), offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.view_children"))):
    from app.application.services import parent_data_service
    from app.domain.entities.clubs import StudentCertificate
    _, student = await parent_data_service.child(db, current_user, student_id)
    rows = (await db.execute(select(StudentCertificate).where(StudentCertificate.student_id == student.id)
        .order_by(StudentCertificate.issue_date.desc(), StudentCertificate.created_at.desc(), StudentCertificate.id)
        .limit(limit).offset(offset))).scalars()
    return success_response([{"id": str(row.id), "title": row.title, "certificate_type": row.certificate_type,
        "issue_date": row.issue_date.isoformat(), "description": row.description,
        "pdf_url": f"/api/parent/child/{student.id}/certificates/{row.id}/pdf"} for row in rows])


@router.get("/child/{student_id}/certificates/{certificate_id}/pdf")
async def download_child_certificate(student_id: UUID, certificate_id: UUID, db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.view_children"))):
    from app.application.services import parent_data_service
    from app.core.exceptions import NotFoundException
    from app.domain.entities.clubs import StudentCertificate
    from app.routers.clubs import download_certificate
    _, student = await parent_data_service.child(db, current_user, student_id)
    row = (await db.execute(select(StudentCertificate).where(StudentCertificate.id == certificate_id,
        StudentCertificate.student_id == student.id))).scalar_one_or_none()
    if row is None:
        raise NotFoundException("Öğrenci belgesi bulunamadı")
    return await download_certificate(certificate_id, db, tenant)


@router.get("/child/{student_id}/weekly-reports")
async def get_child_weekly_reports(
    student_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.view_children"))
):
    from app.application.services import parent_data_service
    return success_response(await parent_data_service.weekly_reports(db, current_user, student_id))


@router.get("/child/{student_id}/teachers")
async def get_child_teachers(
    student_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.view_children"))
):
    from app.application.services import parent_data_service
    return success_response(await parent_data_service.teachers(db, current_user, student_id))


@router.post("/child/{student_id}/send-message")
async def send_message_to_teacher(
    student_id: UUID,
    message_data: MessageCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.send_message"))
):
    from app.application.services import parent_data_service
    data = await parent_data_service.send_chat(db, current_user, student_id, message_data.teacher_id,
        f"Konu: {message_data.subject}\n\n{message_data.message}")
    return success_response(data, "Mesaj gönderildi")


@router.get("/child/{student_id}/chat/{teacher_id}")
async def get_chat_messages(
    student_id: UUID,
    teacher_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.send_message")),
):
    from app.application.services import parent_data_service
    return success_response(await parent_data_service.chat_history(db, current_user, student_id, teacher_id))


class ChatMessageCreate(BaseModel):
    message: str = Field(min_length=1, max_length=10000)


@router.post("/child/{student_id}/chat/{teacher_id}")
async def send_chat_message(
    student_id: UUID,
    teacher_id: UUID,
    message_data: ChatMessageCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("parent.send_message")),
):
    from app.application.services import parent_data_service
    return success_response(await parent_data_service.send_chat(db, current_user, student_id, teacher_id, message_data.message))
