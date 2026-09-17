"""
KVKK & Veli Onay Masası Module API
Handles consent documents and student consents
"""
from datetime import datetime, date
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.responses import success_response
from app.core.security import PermissionChecker, TenantContext
from app.domain.entities import Student, User, Parent

router = APIRouter(prefix="/api/consents", tags=["Consents"])


# ==================== Schemas ====================

class ConsentDocumentCreate(BaseModel):
    title: str = Field(..., max_length=255)
    document_type: str = Field(..., max_length=50, description="PHOTO_CONSENT, TRIP_CONSENT, KVKK, etc.")
    content: str = Field(..., description="Document content")
    version: str = Field(default="1.0", max_length=20)
    effective_date: date = Field(default_factory=date.today)

class StudentConsentCreate(BaseModel):
    student_id: UUID
    consent_document_id: UUID
    parent_id: Optional[UUID] = None
    consent_method: Optional[str] = None
    signature_data: Optional[str] = None
    notes: Optional[str] = None


# ==================== Consent Documents Endpoints ====================

@router.get("/documents")
async def get_consent_documents(
    document_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(True),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("consents.read"))
):
    """Get consent documents with filtering"""
    from app.domain.entities.consents import ConsentDocument
    
    query = select(ConsentDocument)
    
    conditions = []
    if document_type:
        conditions.append(ConsentDocument.document_type == document_type)
    if is_active is not None:
        conditions.append(ConsentDocument.is_active == is_active)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(ConsentDocument.effective_date.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    documents = result.scalars().all()
    
    enriched_documents = []
    for doc in documents:
        # Get created by name
        created_by_name = None
        if doc.created_by:
            user_result = await db.execute(
                select(User).where(User.id == doc.created_by)
            )
            user = user_result.scalar_one_or_none()
            if user:
                created_by_name = f"{user.first_name} {user.last_name}"
        
        enriched_documents.append({
            "id": str(doc.id),
            "title": doc.title,
            "document_type": doc.document_type,
            "content": doc.content,
            "version": doc.version,
            "effective_date": doc.effective_date.isoformat(),
            "is_active": doc.is_active,
            "created_by": str(doc.created_by),
            "created_by_name": created_by_name,
            "created_at": doc.created_at.isoformat()
        })
    
    return success_response(enriched_documents)


@router.post("/documents")
async def create_consent_document(
    document: ConsentDocumentCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("consents.write"))
):
    """Create a new consent document"""
    from app.domain.entities.consents import ConsentDocument
    
    new_document = ConsentDocument(
        title=document.title,
        document_type=document.document_type,
        content=document.content,
        version=document.version,
        effective_date=document.effective_date,
        is_active=True,
        created_by=None  # Will be set from current user context
    )
    db.add(new_document)
    await db.commit()
    await db.refresh(new_document)
    
    return success_response({
        "id": str(new_document.id),
        "title": new_document.title,
        "document_type": new_document.document_type,
        "version": new_document.version,
        "effective_date": new_document.effective_date.isoformat(),
        "created_at": new_document.created_at.isoformat()
    })


@router.put("/documents/{document_id}")
async def update_consent_document(
    document_id: UUID,
    document: ConsentDocumentCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("consents.write"))
):
    """Update a consent document"""
    from app.domain.entities.consents import ConsentDocument
    
    result = await db.execute(
        select(ConsentDocument).where(ConsentDocument.id == document_id)
    )
    existing_document = result.scalar_one_or_none()
    
    if not existing_document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    existing_document.title = document.title
    existing_document.document_type = document.document_type
    existing_document.content = document.content
    existing_document.version = document.version
    existing_document.effective_date = document.effective_date
    
    await db.commit()
    
    return success_response({
        "id": str(existing_document.id),
        "updated_at": existing_document.updated_at.isoformat()
    })


# ==================== Student Consents Endpoints ====================

@router.get("/student-consents")
async def get_student_consents(
    student_id: Optional[UUID] = Query(None),
    consent_document_id: Optional[UUID] = Query(None),
    consent_status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("consents.read"))
):
    """Get student consents with filtering"""
    from app.domain.entities.consents import StudentConsent
    
    query = select(StudentConsent)
    
    conditions = []
    if student_id:
        conditions.append(StudentConsent.student_id == student_id)
    if consent_document_id:
        conditions.append(StudentConsent.consent_document_id == consent_document_id)
    if consent_status:
        conditions.append(StudentConsent.consent_status == consent_status.upper())
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(StudentConsent.created_at.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    consents = result.scalars().all()
    
    enriched_consents = []
    for consent in consents:
        # Get student name
        student_name = None
        if consent.student_id:
            student_result = await db.execute(
                select(Student).where(Student.id == consent.student_id)
            )
            student = student_result.scalar_one_or_none()
            if student:
                student_name = f"{student.first_name} {student.last_name}"
        
        # Get document title
        document_title = None
        if consent.consent_document_id:
            from app.domain.entities.consents import ConsentDocument
            doc_result = await db.execute(
                select(ConsentDocument).where(ConsentDocument.id == consent.consent_document_id)
            )
            doc = doc_result.scalar_one_or_none()
            if doc:
                document_title = doc.title
        
        # Get parent name
        parent_name = None
        if consent.parent_id:
            parent_result = await db.execute(
                select(Parent).where(Parent.id == consent.parent_id)
            )
            parent = parent_result.scalar_one_or_none()
            if parent:
                parent_name = f"{parent.first_name} {parent.last_name}"
        
        enriched_consents.append({
            "id": str(consent.id),
            "student_id": str(consent.student_id),
            "student_name": student_name,
            "consent_document_id": str(consent.consent_document_id),
            "document_title": document_title,
            "parent_id": str(consent.parent_id) if consent.parent_id else None,
            "parent_name": parent_name,
            "consent_status": consent.consent_status,
            "consent_method": consent.consent_method,
            "consented_at": consent.consented_at.isoformat() if consent.consented_at else None,
            "ip_address": str(consent.ip_address) if consent.ip_address else None,
            "signature_data": consent.signature_data,
            "notes": consent.notes,
            "created_at": consent.created_at.isoformat()
        })
    
    return success_response(enriched_consents)


@router.post("/student-consents")
async def create_student_consent(
    consent: StudentConsentCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("consents.write"))
):
    """Create or update a student consent"""
    from app.domain.entities.consents import StudentConsent
    
    # Check if consent already exists
    existing_result = await db.execute(
        select(StudentConsent).where(
            and_(
                StudentConsent.student_id == consent.student_id,
                StudentConsent.consent_document_id == consent.consent_document_id
            )
        )
    )
    existing = existing_result.scalar_one_or_none()
    
    if existing:
        existing.parent_id = consent.parent_id
        existing.consent_status = "APPROVED"
        existing.consent_method = consent.consent_method
        existing.signature_data = consent.signature_data
        existing.consented_at = datetime.utcnow()
        existing.notes = consent.notes
    else:
        new_consent = StudentConsent(
            student_id=consent.student_id,
            consent_document_id=consent.consent_document_id,
            parent_id=consent.parent_id,
            consent_status="APPROVED",
            consent_method=consent.consent_method,
            signature_data=consent.signature_data,
            consented_at=datetime.utcnow(),
            notes=consent.notes
        )
        db.add(new_consent)
    
    await db.commit()
    
    return success_response({
        "message": "Consent saved successfully",
        "student_id": str(consent.student_id),
        "consent_document_id": str(consent.consent_document_id),
        "consent_status": "APPROVED"
    })


@router.get("/consent-summary")
async def get_consent_summary(
    document_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("consents.read"))
):
    """Get consent summary statistics"""
    from app.domain.entities.consents import StudentConsent
    
    query = select(StudentConsent)
    
    if document_id:
        query = query.where(StudentConsent.consent_document_id == document_id)
    
    result = await db.execute(query)
    consents = result.scalars().all()
    
    total = len(consents)
    approved = sum(1 for c in consents if c.consent_status == "APPROVED")
    pending = sum(1 for c in consents if c.consent_status == "PENDING")
    rejected = sum(1 for c in consents if c.consent_status == "REJECTED")
    
    return success_response({
        "total": total,
        "approved": approved,
        "pending": pending,
        "rejected": rejected,
        "approval_rate": (approved / total * 100) if total > 0 else 0
    })
