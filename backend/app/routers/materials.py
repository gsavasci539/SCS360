"""
Course Materials & Digital Library Module API
Handles file uploads, course materials management, and digital library
"""
from __future__ import annotations
from datetime import UTC, datetime, date
from typing import Optional
from uuid import UUID, uuid4
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.infrastructure.models.models import ClassRoom as Class
from app.core.responses import success_response
from app.core.permissions import PermissionChecker
from app.core.tenant import TenantContext
from app.domain.entities import (
    CourseMaterial, User
)
from app.domain.entities.materials import MaterialSubmission
from app.infrastructure.models.models import Student
from sqlalchemy.exc import IntegrityError
from app.application.services import material_file_service
from app.infrastructure.storage.uploads import read_upload
from app.core.exceptions import ValidationException
from app.core.student_access import uses_relationship_scope

router = APIRouter(prefix="/api/materials", tags=["Materials"])

MATERIAL_EXTENSIONS = {
    "PDF": {"pdf"}, "VIDEO": {"mp4", "avi", "mov", "mkv"},
    "AUDIO": {"mp3", "wav", "ogg"}, "DOCUMENT": {"doc", "docx", "txt", "rtf"},
    "PRESENTATION": {"ppt", "pptx"}, "IMAGE": {"jpg", "jpeg", "png", "gif", "bmp"},
    "OTHER": {"zip", "rar"},
}
MaterialType = Literal["PDF", "VIDEO", "AUDIO", "DOCUMENT", "PRESENTATION", "IMAGE", "OTHER"]
MaterialVisibility = Literal["PUBLIC", "CLASS_ONLY", "TEACHER_ONLY"]


async def _validate_scope(db, tenant, class_id, teacher_id, visibility, visible_from, visible_until):
    if visible_from and visible_until and visible_from > visible_until:
        raise ValidationException("Görünürlük bitiş tarihi başlangıçtan önce olamaz")
    if visibility == "CLASS_ONLY" and not class_id:
        raise ValidationException("Sınıfa özel materyal için sınıf seçilmeli")
    if class_id and not (await db.execute(select(Class.id).where(Class.id == class_id))).scalar_one_or_none():
        raise ValidationException("Erişilebilir bir sınıf seçilmeli")
    if not (await db.execute(select(User.id).where(User.id == teacher_id))).scalar_one_or_none():
        raise ValidationException("Erişilebilir bir öğretmen seçilmeli")
    if uses_relationship_scope(tenant) and teacher_id != tenant.user_id:
        raise ValidationException("Öğretmen yalnız kendi adına materyal yükleyebilir")


def _staff_filter(tenant):
    if uses_relationship_scope(tenant):
        from sqlalchemy import or_
        return or_(CourseMaterial.visibility != "TEACHER_ONLY", CourseMaterial.teacher_id == tenant.user_id,
            CourseMaterial.created_by == tenant.user_id)
    return True


def _write_filter(tenant):
    if uses_relationship_scope(tenant):
        from sqlalchemy import or_
        return or_(CourseMaterial.teacher_id == tenant.user_id, CourseMaterial.created_by == tenant.user_id)
    return True


# ==================== Schemas ====================

class CourseMaterialCreate(BaseModel):
    class_id: Optional[UUID] = None
    subject_id: Optional[UUID] = None
    teacher_id: Optional[UUID] = None
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    material_type: MaterialType
    unit_topic: Optional[str] = Field(None, max_length=255)
    visibility: MaterialVisibility = "CLASS_ONLY"
    visible_from: Optional[date] = None
    visible_until: Optional[date] = None

class CourseMaterialResponse(BaseModel):
    id: UUID
    class_id: Optional[UUID]
    class_name: Optional[str]
    subject_id: Optional[UUID]
    teacher_id: Optional[UUID]
    teacher_name: Optional[str]
    title: str
    description: Optional[str]
    material_type: str
    file_url: str
    file_size: Optional[int]
    file_name: Optional[str]
    unit_topic: Optional[str]
    visibility: str
    visible_from: Optional[date]
    visible_until: Optional[date]
    download_count: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID]
    created_by_name: Optional[str]


class MaterialSubmissionCreate(BaseModel):
    material_id: UUID
    student_id: UUID
    submission_text: Optional[str] = Field(None, max_length=10000)
    file_url: Optional[str] = Field(None, max_length=500)


class MaterialGradingCreate(BaseModel):
    grade: float = Field(..., ge=0, le=100)
    feedback: Optional[str] = Field(None, max_length=10000)


# ==================== Course Materials Endpoints ====================

@router.get("")
async def get_course_materials(
    class_id: Optional[UUID] = Query(None),
    teacher_id: Optional[UUID] = Query(None),
    material_type: Optional[str] = Query(None),
    visibility: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(True),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("material.read"))
):
    """Get course materials with filtering"""
    query = select(CourseMaterial).where(_staff_filter(tenant))
    
    conditions = []
    if class_id:
        conditions.append(CourseMaterial.class_id == class_id)
    if teacher_id:
        conditions.append(CourseMaterial.teacher_id == teacher_id)
    if material_type:
        conditions.append(CourseMaterial.material_type == material_type.upper())
    if visibility:
        conditions.append(CourseMaterial.visibility == visibility.upper())
    if is_active is not None:
        conditions.append(CourseMaterial.is_active == is_active)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(CourseMaterial.created_at.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    materials = result.scalars().all()
    
    enriched_materials = []
    for material in materials:
        # Get class name
        class_name = None
        if material.class_id:
            class_result = await db.execute(
                select(Class).where(Class.id == material.class_id)
            )
            cls = class_result.scalar_one_or_none()
            if cls:
                class_name = cls.name
        
        # Get teacher name
        teacher_name = None
        if material.teacher_id:
            teacher_result = await db.execute(
                select(User).where(User.id == material.teacher_id)
            )
            teacher = teacher_result.scalar_one_or_none()
            if teacher:
                teacher_name = f"{teacher.first_name} {teacher.last_name}"
        
        # Get created by name
        created_by_name = None
        if material.created_by:
            user_result = await db.execute(
                select(User).where(User.id == material.created_by)
            )
            user = user_result.scalar_one_or_none()
            if user:
                created_by_name = f"{user.first_name} {user.last_name}"
        
        enriched_materials.append({
            "id": str(material.id),
            "class_id": str(material.class_id) if material.class_id else None,
            "class_name": class_name,
            "subject_id": str(material.subject_id) if material.subject_id else None,
            "teacher_id": str(material.teacher_id) if material.teacher_id else None,
            "teacher_name": teacher_name,
            "title": material.title,
            "description": material.description,
            "material_type": material.material_type,
            "file_url": material_file_service.download_url(material.id),
            "file_size": material.file_size,
            "file_name": material.file_name,
            "unit_topic": material.unit_topic,
            "visibility": material.visibility,
            "visible_from": material.visible_from.isoformat() if material.visible_from else None,
            "visible_until": material.visible_until.isoformat() if material.visible_until else None,
            "download_count": material.download_count,
            "is_active": material.is_active,
            "created_at": material.created_at.isoformat(),
            "updated_at": material.updated_at.isoformat(),
            "created_by": str(material.created_by) if material.created_by else None,
            "created_by_name": created_by_name
        })
    
    return success_response(enriched_materials)


@router.post("/upload")
async def upload_course_material(
    class_id: Optional[UUID] = Query(None),
    subject_id: Optional[UUID] = Query(None),
    teacher_id: Optional[UUID] = Query(None),
    title: str = Query(..., min_length=1, max_length=255),
    description: Optional[str] = Query(None, max_length=1000),
    material_type: MaterialType = Query(...),
    unit_topic: Optional[str] = Query(None, max_length=255),
    visibility: MaterialVisibility = Query("CLASS_ONLY"),
    visible_from: Optional[date] = Query(None),
    visible_until: Optional[date] = Query(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("material.write"))
):
    """Upload a course material file"""
    title = title.strip()
    if not title:
        raise ValidationException("Materyal başlığı gerekli")
    teacher_id = teacher_id or tenant.user_id
    await _validate_scope(db, tenant, class_id, teacher_id, visibility, visible_from, visible_until)
    name, content = await read_upload(file, MATERIAL_EXTENSIONS[material_type])
    material_id = uuid4()
    
    # Create database record
    new_material = CourseMaterial(
        id=material_id,
        class_id=class_id,
        subject_id=subject_id,
        teacher_id=teacher_id,
        title=title,
        description=description,
        material_type=material_type,
        file_url=material_file_service.download_url(material_id),
        file_size=len(content),
        file_name=name,
        unit_topic=unit_topic,
        visibility=visibility.upper(),
        visible_from=visible_from,
        visible_until=visible_until,
        download_count=0,
        is_active=True,
        created_by=tenant.user_id,
    )
    db.add(new_material)
    await db.flush()
    await material_file_service.save_content(material_id, content)
    await db.refresh(new_material)
    
    return success_response({
        "id": str(new_material.id),
        "title": new_material.title,
        "material_type": new_material.material_type,
        "file_url": new_material.file_url,
        "file_size": new_material.file_size,
        "file_name": new_material.file_name,
        "created_at": new_material.created_at.isoformat()
    })


@router.put("/{material_id}")
async def update_course_material(
    material_id: UUID,
    material: CourseMaterialCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("material.write"))
):
    """Update a course material"""
    result = await db.execute(
        select(CourseMaterial).where(CourseMaterial.id == material_id, _write_filter(tenant))
    )
    existing_material = result.scalar_one_or_none()
    
    if not existing_material:
        raise HTTPException(status_code=404, detail="Material not found")

    await _validate_scope(db, tenant, material.class_id, material.teacher_id or tenant.user_id,
        material.visibility, material.visible_from, material.visible_until)
    if existing_material.material_type != material.material_type:
        raise ValidationException("Dosya türü yüklenen dosyadan bağımsız değiştirilemez")
    
    existing_material.class_id = material.class_id
    existing_material.subject_id = material.subject_id
    existing_material.teacher_id = material.teacher_id or tenant.user_id
    existing_material.updated_by = tenant.user_id
    existing_material.title = material.title
    existing_material.description = material.description
    existing_material.material_type = material.material_type.upper()
    existing_material.unit_topic = material.unit_topic
    existing_material.visibility = material.visibility.upper()
    existing_material.visible_from = material.visible_from
    existing_material.visible_until = material.visible_until
    
    await db.commit()
    await db.refresh(existing_material)
    
    return success_response({
        "id": str(existing_material.id),
        "title": existing_material.title,
        "updated_at": existing_material.updated_at.isoformat()
    })


@router.delete("/{material_id}")
async def delete_course_material(
    material_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("material.write"))
):
    """Delete a course material"""
    result = await db.execute(
        select(CourseMaterial).where(CourseMaterial.id == material_id, _write_filter(tenant))
    )
    material = result.scalar_one_or_none()
    
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    # Preserve submission references and audit history when removing a material.
    material.is_active = False
    material.updated_by = tenant.user_id
    await db.commit()
    
    return success_response({"message": "Material deleted successfully"})


@router.post("/{material_id}/download")
async def download_course_material(
    material_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("material.read"))
):
    """Return the authenticated download URL; actual downloads update the counter."""
    result = await db.execute(
        select(CourseMaterial).where(CourseMaterial.id == material_id,
            CourseMaterial.is_active.is_(True), _staff_filter(tenant))
    )
    material = result.scalar_one_or_none()
    
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    return success_response({
        "id": str(material.id),
        "file_url": material_file_service.download_url(material.id),
        "download_count": material.download_count
    })


@router.get("/{material_id}/file")
async def get_material_file(
    material_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("material.read")),
):
    material = (await db.execute(select(CourseMaterial).where(CourseMaterial.id == material_id,
        CourseMaterial.is_active.is_(True), _staff_filter(tenant)))).scalar_one_or_none()
    if material is None:
        raise HTTPException(status_code=404, detail="Materyal bulunamadı")
    return await material_file_service.file_response(db, material)


@router.get("/stats/summary")
async def get_materials_stats(
    class_id: Optional[UUID] = Query(None),
    teacher_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("material.read"))
):
    """Get materials statistics"""
    query = select(CourseMaterial)
    
    conditions = []
    if class_id:
        conditions.append(CourseMaterial.class_id == class_id)
    if teacher_id:
        conditions.append(CourseMaterial.teacher_id == teacher_id)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    result = await db.execute(query)
    materials = result.scalars().all()
    
    # Calculate statistics
    total_materials = len(materials)
    total_downloads = sum(m.download_count or 0 for m in materials)
    
    # Group by type
    by_type = {}
    for material in materials:
        by_type[material.material_type] = by_type.get(material.material_type, 0) + 1
    
    # Group by visibility
    by_visibility = {}
    for material in materials:
        by_visibility[material.visibility] = by_visibility.get(material.visibility, 0) + 1
    
    return success_response({
        "total_materials": total_materials,
        "total_downloads": total_downloads,
        "by_type": by_type,
        "by_visibility": by_visibility
    })


# ==================== Material Submissions Endpoints ====================

@router.post("/{material_id}/submissions")
async def submit_material(
    material_id: UUID,
    submission: MaterialSubmissionCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("material.write"))
):
    """Submit a material assignment"""
    if submission.material_id != material_id:
        raise ValidationException("Materyal kimliği istek yoluyla eşleşmiyor")
    if not (submission.submission_text or "").strip():
        raise ValidationException("Teslim açıklaması gerekli")
    if submission.file_url:
        raise ValidationException("Dosya bağlantısı yerine metin teslimi kullanın")
    
    # Verify material exists
    material_result = await db.execute(
        select(CourseMaterial).where(CourseMaterial.id == material_id,
            CourseMaterial.is_active.is_(True), _write_filter(tenant))
    )
    material = material_result.scalar_one_or_none()
    
    if not material:
        raise HTTPException(status_code=404, detail="Materyal bulunamadı")
    
    # Verify student exists
    student_result = await db.execute(
        select(Student).where(Student.id == submission.student_id)
    )
    student = student_result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Öğrenci bulunamadı")
    if material.visibility == "TEACHER_ONLY" or (material.class_id and material.visibility != "PUBLIC" and student.class_id != material.class_id):
        raise ValidationException("Materyal bu öğrenciye açık değil")
    
    # Check if student already submitted
    existing_result = await db.execute(
        select(MaterialSubmission).where(
            and_(
                MaterialSubmission.material_id == material_id,
                MaterialSubmission.student_id == submission.student_id
            )
        )
    )
    existing = existing_result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(status_code=409, detail="Bu materyal zaten teslim edildi")
    
    # Create submission
    new_submission = MaterialSubmission(
        organization_id=student.organization_id,
        branch_id=student.branch_id,
        material_id=material_id,
        student_id=submission.student_id,
        submission_text=submission.submission_text,
        file_url=submission.file_url,
        status="SUBMITTED",
        submitted_at=datetime.now(UTC)
    )
    
    try:
        async with db.begin_nested():
            db.add(new_submission)
            await db.flush()
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Bu materyal zaten teslim edildi")
    await db.refresh(new_submission)
    
    return success_response({
        "id": str(new_submission.id),
        "material_id": str(new_submission.material_id),
        "student_id": str(new_submission.student_id),
        "status": new_submission.status,
        "submitted_at": new_submission.submitted_at.isoformat()
    }, "Materyal teslim edildi")


@router.get("/{material_id}/submissions")
async def get_material_submissions(
    material_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("material.read"))
):
    """Get all submissions for a material"""
    
    # Verify material exists
    material_result = await db.execute(
        select(CourseMaterial).where(CourseMaterial.id == material_id, _write_filter(tenant))
    )
    material = material_result.scalar_one_or_none()
    
    if not material:
        raise HTTPException(status_code=404, detail="Materyal bulunamadı")
    
    # Get submissions
    result = await db.execute(
        select(MaterialSubmission).where(MaterialSubmission.material_id == material_id)
    )
    submissions = result.scalars().all()
    
    enriched_submissions = []
    for submission in submissions:
        # Get student info
        student_result = await db.execute(
            select(Student).where(Student.id == submission.student_id)
        )
        student = student_result.scalar_one_or_none()
        
        enriched_submissions.append({
            "id": str(submission.id),
            "material_id": str(submission.material_id),
            "student_id": str(submission.student_id),
            "student_name": f"{student.first_name} {student.last_name}" if student else None,
            "student_number": student.student_number if student else None,
            "submission_text": submission.submission_text,
            "file_url": submission.file_url,
            "status": submission.status,
            "grade": submission.grade,
            "feedback": submission.feedback,
            "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
            "graded_at": submission.graded_at.isoformat() if submission.graded_at else None
        })
    
    return success_response(enriched_submissions)


@router.put("/submissions/{submission_id}/grade")
async def grade_material_submission(
    submission_id: UUID,
    grading: MaterialGradingCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("material.write"))
):
    """Grade a material submission"""
    
    result = await db.execute(
        select(MaterialSubmission).join(CourseMaterial, CourseMaterial.id == MaterialSubmission.material_id)
        .where(MaterialSubmission.id == submission_id, _write_filter(tenant))
    )
    submission = result.scalar_one_or_none()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Teslim bulunamadı")
    
    submission.grade = grading.grade
    submission.feedback = grading.feedback
    submission.status = "GRADED"
    submission.graded_at = datetime.now(UTC)
    
    await db.commit()
    
    return success_response({
        "id": str(submission.id),
        "grade": submission.grade,
        "feedback": submission.feedback,
        "status": submission.status,
        "graded_at": submission.graded_at.isoformat()
    }, "Teslim notlandırıldı")
