"""
Exams & Report Card Generator Module API
Handles exam management, grading, and report card generation
"""
from datetime import datetime, date
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.responses import success_response
from app.core.security import PermissionChecker, TenantContext
from app.domain.entities import (
    Exam, ExamResult, ReportCard, Student, User
)

router = APIRouter(prefix="/api/exams", tags=["Exams"])


# ==================== Schemas ====================

class ExamCreate(BaseModel):
    class_id: UUID
    subject_id: Optional[UUID] = None
    teacher_id: Optional[UUID] = None
    title: str = Field(..., min_length=1, max_length=255)
    exam_type: str = Field(..., description="MIDTERM, FINAL, QUIZ, MAKEUP, PROJECT, OTHER")
    exam_date: date = Field(..., description="Exam date")
    start_time: Optional[str] = Field(None, description="HH:MM format")
    duration_minutes: int = Field(default=60, ge=15, le=300)
    max_score: float = Field(default=100.0, ge=0)
    weight: float = Field(default=1.0, ge=0, le=2)
    description: Optional[str] = None

class ExamResponse(BaseModel):
    id: UUID
    class_id: UUID
    class_name: Optional[str]
    subject_id: Optional[UUID]
    teacher_id: Optional[UUID]
    teacher_name: Optional[str]
    title: str
    exam_type: str
    status: str
    exam_date: str
    start_time: Optional[str]
    duration_minutes: int
    max_score: float
    weight: float
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

class ExamResultCreate(BaseModel):
    exam_id: UUID
    student_id: UUID
    score: Optional[float] = Field(None, ge=0)
    grade_scale: Optional[str] = Field(None, description="A, B, C, D, F, PASS, FAIL")
    notes: Optional[str] = None

class ExamResultResponse(BaseModel):
    id: UUID
    exam_id: UUID
    exam_title: Optional[str]
    student_id: UUID
    student_name: Optional[str]
    score: Optional[float]
    grade_scale: Optional[str]
    notes: Optional[str]
    submitted_by: Optional[UUID]
    submitted_by_name: Optional[str]
    submitted_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

class BulkGradeEntry(BaseModel):
    exam_id: UUID
    grades: List[dict] = Field(..., description="List of {student_id, score, grade_scale, notes}")

class ReportCardGenerate(BaseModel):
    student_id: UUID
    academic_year: str = Field(..., description="e.g., 2024-2025")
    semester: str = Field(default="FALL", description="FALL, SPRING, SUMMER")
    teacher_comments: Optional[str] = None
    principal_comments: Optional[str] = None

class ReportCardResponse(BaseModel):
    id: UUID
    student_id: UUID
    student_name: Optional[str]
    academic_year: str
    semester: str
    gpa: Optional[float]
    class_rank: Optional[int]
    total_students: Optional[int]
    attendance_rate: Optional[float]
    teacher_comments: Optional[str]
    principal_comments: Optional[str]
    generated_by: Optional[UUID]
    generated_by_name: Optional[str]
    generated_at: Optional[datetime]
    pdf_url: Optional[str]
    is_published: bool
    created_at: datetime
    updated_at: datetime


# ==================== Exam Endpoints ====================

@router.get("")
async def get_exams(
    class_id: Optional[UUID] = Query(None),
    teacher_id: Optional[UUID] = Query(None),
    exam_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("exam.read"))
):
    """Get exams with filtering"""
    query = select(Exam)
    
    conditions = []
    if class_id:
        conditions.append(Exam.class_id == class_id)
    if teacher_id:
        conditions.append(Exam.teacher_id == teacher_id)
    if exam_type:
        conditions.append(Exam.exam_type == exam_type.upper())
    if status:
        conditions.append(Exam.status == status.upper())
    if start_date:
        conditions.append(Exam.exam_date >= start_date)
    if end_date:
        conditions.append(Exam.exam_date <= end_date)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(Exam.exam_date.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    exams = result.scalars().all()
    
    enriched_exams = []
    for exam in exams:
        # Get class name
        class_name = None
        if exam.class_id:
            class_result = await db.execute(
                select(Class).where(Class.id == exam.class_id)
            )
            cls = class_result.scalar_one_or_none()
            if cls:
                class_name = cls.name
        
        # Get teacher name
        teacher_name = None
        if exam.teacher_id:
            teacher_result = await db.execute(
                select(User).where(User.id == exam.teacher_id)
            )
            teacher = teacher_result.scalar_one_or_none()
            if teacher:
                teacher_name = f"{teacher.first_name} {teacher.last_name}"
        
        enriched_exams.append({
            "id": str(exam.id),
            "class_id": str(exam.class_id),
            "class_name": class_name,
            "subject_id": str(exam.subject_id) if exam.subject_id else None,
            "teacher_id": str(exam.teacher_id) if exam.teacher_id else None,
            "teacher_name": teacher_name,
            "title": exam.title,
            "exam_type": exam.exam_type,
            "status": exam.status,
            "exam_date": exam.exam_date.isoformat(),
            "start_time": exam.start_time,
            "duration_minutes": exam.duration_minutes,
            "max_score": float(exam.max_score),
            "weight": float(exam.weight),
            "description": exam.description,
            "created_at": exam.created_at.isoformat(),
            "updated_at": exam.updated_at.isoformat()
        })
    
    return success_response(enriched_exams)


@router.post("")
async def create_exam(
    exam: ExamCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("exam.write"))
):
    """Create a new exam"""
    new_exam = Exam(
        class_id=exam.class_id,
        subject_id=exam.subject_id,
        teacher_id=exam.teacher_id,
        title=exam.title,
        exam_type=exam.exam_type.upper(),
        status="SCHEDULED",
        exam_date=exam.exam_date,
        start_time=exam.start_time,
        duration_minutes=exam.duration_minutes,
        max_score=exam.max_score,
        weight=exam.weight,
        description=exam.description
    )
    db.add(new_exam)
    await db.commit()
    await db.refresh(new_exam)
    
    return success_response({
        "id": str(new_exam.id),
        "class_id": str(new_exam.class_id),
        "title": new_exam.title,
        "exam_type": new_exam.exam_type,
        "status": new_exam.status,
        "exam_date": new_exam.exam_date.isoformat(),
        "created_at": new_exam.created_at.isoformat()
    })


@router.put("/{exam_id}")
async def update_exam(
    exam_id: UUID,
    exam: ExamCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("exam.write"))
):
    """Update an exam"""
    result = await db.execute(
        select(Exam).where(Exam.id == exam_id)
    )
    existing_exam = result.scalar_one_or_none()
    
    if not existing_exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    existing_exam.class_id = exam.class_id
    existing_exam.subject_id = exam.subject_id
    existing_exam.teacher_id = exam.teacher_id
    existing_exam.title = exam.title
    existing_exam.exam_type = exam.exam_type.upper()
    existing_exam.exam_date = exam.exam_date
    existing_exam.start_time = exam.start_time
    existing_exam.duration_minutes = exam.duration_minutes
    existing_exam.max_score = exam.max_score
    existing_exam.weight = exam.weight
    existing_exam.description = exam.description
    
    await db.commit()
    await db.refresh(existing_exam)
    
    return success_response({
        "id": str(existing_exam.id),
        "title": existing_exam.title,
        "status": existing_exam.status,
        "updated_at": existing_exam.updated_at.isoformat()
    })


@router.delete("/{exam_id}")
async def delete_exam(
    exam_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("exam.write"))
):
    """Delete an exam"""
    result = await db.execute(
        select(Exam).where(Exam.id == exam_id)
    )
    exam = result.scalar_one_or_none()
    
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    await db.delete(exam)
    await db.commit()
    
    return success_response({"message": "Exam deleted successfully"})


# ==================== Exam Results Endpoints ====================

@router.get("/{exam_id}/results")
async def get_exam_results(
    exam_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("exam.read"))
):
    """Get results for a specific exam"""
    result = await db.execute(
        select(ExamResult).where(ExamResult.exam_id == exam_id)
    )
    results = result.scalars().all()
    
    enriched_results = []
    for result_item in results:
        # Get student name
        student_name = None
        if result_item.student_id:
            student_result = await db.execute(
                select(Student).where(Student.id == result_item.student_id)
            )
            student = student_result.scalar_one_or_none()
            if student:
                student_name = f"{student.first_name} {student.last_name}"
        
        # Get submitted by name
        submitted_by_name = None
        if result_item.submitted_by:
            user_result = await db.execute(
                select(User).where(User.id == result_item.submitted_by)
            )
            user = user_result.scalar_one_or_none()
            if user:
                submitted_by_name = f"{user.first_name} {user.last_name}"
        
        # Get exam title
        exam_result = await db.execute(
            select(Exam).where(Exam.id == result_item.exam_id)
        )
        exam = exam_result.scalar_one_or_none()
        exam_title = exam.title if exam else None
        
        enriched_results.append({
            "id": str(result_item.id),
            "exam_id": str(result_item.exam_id),
            "exam_title": exam_title,
            "student_id": str(result_item.student_id),
            "student_name": student_name,
            "score": float(result_item.score) if result_item.score else None,
            "grade_scale": result_item.grade_scale,
            "notes": result_item.notes,
            "submitted_by": str(result_item.submitted_by) if result_item.submitted_by else None,
            "submitted_by_name": submitted_by_name,
            "submitted_at": result_item.submitted_at.isoformat() if result_item.submitted_at else None,
            "created_at": result_item.created_at.isoformat(),
            "updated_at": result_item.updated_at.isoformat()
        })
    
    return success_response(enriched_results)


@router.post("/bulk-grade-entry")
async def bulk_grade_entry(
    request: BulkGradeEntry,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("exam.write"))
):
    """Bulk grade entry for an exam"""
    # Check if exam exists
    exam_result = await db.execute(
        select(Exam).where(Exam.id == request.exam_id)
    )
    exam = exam_result.scalar_one_or_none()
    
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    updated_count = 0
    created_count = 0
    
    for grade_data in request.grades:
        student_id = grade_data.get("student_id")
        score = grade_data.get("score")
        grade_scale = grade_data.get("grade_scale")
        notes = grade_data.get("notes")
        
        # Check if result already exists
        existing_result = await db.execute(
            select(ExamResult).where(
                and_(
                    ExamResult.exam_id == request.exam_id,
                    ExamResult.student_id == student_id
                )
            )
        )
        existing = existing_result.scalar_one_or_none()
        
        if existing:
            existing.score = score
            existing.grade_scale = grade_scale
            existing.notes = notes
            existing.submitted_at = datetime.utcnow()
            updated_count += 1
        else:
            new_result = ExamResult(
                exam_id=request.exam_id,
                student_id=student_id,
                score=score,
                grade_scale=grade_scale,
                notes=notes,
                submitted_at=datetime.utcnow()
            )
            db.add(new_result)
            created_count += 1
    
    await db.commit()
    
    return success_response({
        "message": f"Grades saved: {created_count} created, {updated_count} updated",
        "created": created_count,
        "updated": updated_count
    })


@router.put("/results/{result_id}")
async def update_exam_result(
    result_id: UUID,
    result: ExamResultCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("exam.write"))
):
    """Update an exam result"""
    existing_result = await db.execute(
        select(ExamResult).where(ExamResult.id == result_id)
    )
    existing = existing_result.scalar_one_or_none()
    
    if not existing:
        raise HTTPException(status_code=404, detail="Result not found")
    
    existing.score = result.score
    existing.grade_scale = result.grade_scale
    existing.notes = result.notes
    existing.submitted_at = datetime.utcnow()
    
    await db.commit()
    
    return success_response({
        "id": str(existing.id),
        "score": existing.score,
        "grade_scale": existing.grade_scale,
        "updated_at": existing.updated_at.isoformat()
    })


# ==================== Report Card Endpoints ====================

@router.post("/report-cards/generate")
async def generate_report_card(
    request: ReportCardGenerate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("exam.write"))
):
    """Generate a report card for a student"""
    # Check if student exists
    student_result = await db.execute(
        select(Student).where(Student.id == request.student_id)
    )
    student = student_result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Calculate GPA and class rank
    gpa, class_rank, total_students = await calculate_student_performance(
        db, request.student_id, request.academic_year, request.semester
    )
    
    # Calculate attendance rate (simplified - would integrate with attendance module)
    attendance_rate = 95.0  # Placeholder
    
    # Check if report card already exists
    existing_result = await db.execute(
        select(ReportCard).where(
            and_(
                ReportCard.student_id == request.student_id,
                ReportCard.academic_year == request.academic_year,
                ReportCard.semester == request.semester
            )
        )
    )
    existing = existing_result.scalar_one_or_none()
    
    if existing:
        existing.gpa = gpa
        existing.class_rank = class_rank
        existing.total_students = total_students
        existing.attendance_rate = attendance_rate
        existing.teacher_comments = request.teacher_comments
        existing.principal_comments = request.principal_comments
        existing.generated_at = datetime.utcnow()
    else:
        new_report_card = ReportCard(
            student_id=request.student_id,
            academic_year=request.academic_year,
            semester=request.semester,
            gpa=gpa,
            class_rank=class_rank,
            total_students=total_students,
            attendance_rate=attendance_rate,
            teacher_comments=request.teacher_comments,
            principal_comments=request.principal_comments,
            generated_at=datetime.utcnow()
        )
        db.add(new_report_card)
    
    await db.commit()
    
    # Get the report card
    report_card_result = await db.execute(
        select(ReportCard).where(
            and_(
                ReportCard.student_id == request.student_id,
                ReportCard.academic_year == request.academic_year,
                ReportCard.semester == request.semester
            )
        )
    )
    report_card = report_card_result.scalar_one_or_none()
    
    return success_response({
        "id": str(report_card.id),
        "student_id": str(report_card.student_id),
        "academic_year": report_card.academic_year,
        "semester": report_card.semester,
        "gpa": float(report_card.gpa) if report_card.gpa else None,
        "class_rank": report_card.class_rank,
        "total_students": report_card.total_students,
        "attendance_rate": float(report_card.attendance_rate) if report_card.attendance_rate else None,
        "teacher_comments": report_card.teacher_comments,
        "principal_comments": report_card.principal_comments,
        "generated_at": report_card.generated_at.isoformat() if report_card.generated_at else None,
        "is_published": report_card.is_published
    })


@router.get("/report-cards/{student_id}")
async def get_student_report_cards(
    student_id: UUID,
    academic_year: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("exam.read"))
):
    """Get report cards for a student"""
    query = select(ReportCard).where(ReportCard.student_id == student_id)
    
    if academic_year:
        query = query.where(ReportCard.academic_year == academic_year)
    
    query = query.order_by(ReportCard.academic_year.desc(), ReportCard.semester)
    
    result = await db.execute(query)
    report_cards = result.scalars().all()
    
    enriched_cards = []
    for card in report_cards:
        # Get student name
        student_name = None
        if card.student_id:
            student_result = await db.execute(
                select(Student).where(Student.id == card.student_id)
            )
            student = student_result.scalar_one_or_none()
            if student:
                student_name = f"{student.first_name} {student.last_name}"
        
        # Get generated by name
        generated_by_name = None
        if card.generated_by:
            user_result = await db.execute(
                select(User).where(User.id == card.generated_by)
            )
            user = user_result.scalar_one_or_none()
            if user:
                generated_by_name = f"{user.first_name} {user.last_name}"
        
        enriched_cards.append({
            "id": str(card.id),
            "student_id": str(card.student_id),
            "student_name": student_name,
            "academic_year": card.academic_year,
            "semester": card.semester,
            "gpa": float(card.gpa) if card.gpa else None,
            "class_rank": card.class_rank,
            "total_students": card.total_students,
            "attendance_rate": float(card.attendance_rate) if card.attendance_rate else None,
            "teacher_comments": card.teacher_comments,
            "principal_comments": card.principal_comments,
            "generated_by": str(card.generated_by) if card.generated_by else None,
            "generated_by_name": generated_by_name,
            "generated_at": card.generated_at.isoformat() if card.generated_at else None,
            "pdf_url": card.pdf_url,
            "is_published": card.is_published,
            "created_at": card.created_at.isoformat(),
            "updated_at": card.updated_at.isoformat()
        })
    
    return success_response(enriched_cards)


@router.put("/report-cards/{card_id}/publish")
async def publish_report_card(
    card_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("exam.write"))
):
    """Publish a report card to parent portal"""
    result = await db.execute(
        select(ReportCard).where(ReportCard.id == card_id)
    )
    report_card = result.scalar_one_or_none()
    
    if not report_card:
        raise HTTPException(status_code=404, detail="Report card not found")
    
    report_card.is_published = True
    
    await db.commit()
    
    return success_response({
        "id": str(report_card.id),
        "is_published": True,
        "message": "Report card published successfully"
    })


# ==================== Helper Functions ====================

async def calculate_student_performance(
    db: AsyncSession,
    student_id: UUID,
    academic_year: str,
    semester: str
) -> tuple[Optional[float], Optional[int], Optional[int]]:
    """Calculate GPA, class rank, and total students"""
    # Get all exam results for the student in the academic year/semester
    # This is a simplified calculation - in real app would filter by academic year/semester
    
    result = await db.execute(
        select(ExamResult).where(ExamResult.student_id == student_id)
    )
    results = result.scalars().all()
    
    if not results:
        return None, None, None
    
    # Calculate GPA (simplified)
    total_score = sum(float(r.score) for r in results if r.score is not None)
    avg_score = total_score / len(results) if results else 0
    
    # Convert to GPA scale (4.0 scale)
    gpa = (avg_score / 100) * 4.0 if avg_score else None
    
    # Calculate class rank (simplified - would need proper class grouping)
    class_rank = 1
    total_students = 1
    
    return gpa, class_rank, total_students
