"""Document management and auditable manual guardian decisions."""
from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services import consent_service as service
from app.core.database import get_db
from app.core.dates import school_today
from app.core.permissions import PermissionChecker
from app.core.responses import success_response
from app.core.tenant import TenantContext
from app.domain.entities.consents import ConsentDocument
from app.infrastructure.models.models import User

router = APIRouter(prefix="/api/consents", tags=["Consents"])


class ConsentDocumentCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    organization_id: UUID | None = None
    title: str = Field(min_length=1, max_length=255)
    document_type: str = Field(min_length=1, max_length=50)
    content: str = Field(min_length=1, max_length=100000)
    version: str = Field(default="1.0", min_length=1, max_length=20)
    effective_date: date = Field(default_factory=school_today)


class StudentConsentCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    student_id: UUID
    consent_document_id: UUID
    parent_id: UUID
    consent_status: Literal["APPROVED", "REJECTED"] = "APPROVED"
    consent_method: Literal["MANUAL", "PAPER"] = "MANUAL"
    signature_data: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=2000)


@router.get("/options")
async def options(organization_id: UUID | None = None, student_id: UUID | None = None,
                  search: str = Query("", max_length=100), db: AsyncSession = Depends(get_db, scope="function"),
                  tenant: TenantContext = Depends(PermissionChecker("consents.write"))):
    return success_response(await service.options(db, tenant, organization_id, search, student_id))


@router.get("/documents")
async def documents(document_type: str | None = None, is_active: bool | None = True,
                    limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0),
                    db: AsyncSession = Depends(get_db, scope="function"), tenant: TenantContext = Depends(PermissionChecker("consents.read"))):
    query = select(ConsentDocument)
    if document_type:
        query = query.where(ConsentDocument.document_type == document_type)
    if is_active is not None:
        query = query.where(ConsentDocument.is_active == is_active)
    docs = (await db.execute(query.order_by(ConsentDocument.effective_date.desc(), ConsentDocument.id).limit(limit).offset(offset))).scalars().all()
    names = {user.id: f"{user.first_name} {user.last_name}" for user in (await db.execute(select(User).where(User.id.in_([doc.created_by for doc in docs])))).scalars()} if docs else {}
    return success_response([{**service.document_data(doc), "created_by_name": names.get(doc.created_by)} for doc in docs])


@router.post("/documents")
async def create_document(document: ConsentDocumentCreate, db: AsyncSession = Depends(get_db, scope="function"),
                          tenant: TenantContext = Depends(PermissionChecker("consents.write"))):
    organization_id = await service.form_organization(db, tenant, document.organization_id)
    doc = ConsentDocument(**document.model_dump(exclude={"organization_id"}), organization_id=organization_id, created_by=tenant.user_id, is_active=True)
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return success_response(service.document_data(doc))


@router.put("/documents/{document_id}")
async def edit_document(document_id: UUID, document: ConsentDocumentCreate, db: AsyncSession = Depends(get_db, scope="function"),
                        tenant: TenantContext = Depends(PermissionChecker("consents.write"))):
    result = await service.edit_document(db, document_id, document)
    await db.commit()
    return success_response(result)


class ActiveUpdate(BaseModel):
    is_active: bool


@router.patch("/documents/{document_id}/status")
async def change_status(document_id: UUID, status: ActiveUpdate, db: AsyncSession = Depends(get_db, scope="function"),
                        tenant: TenantContext = Depends(PermissionChecker("consents.write"))):
    doc = await service.lock_document(db, document_id)
    doc.is_active = status.is_active
    await db.commit()
    return success_response(service.document_data(doc))


@router.get("/student-consents")
async def decisions(student_id: UUID | None = None, consent_document_id: UUID | None = None, consent_status: str | None = None,
                    limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0),
                    db: AsyncSession = Depends(get_db, scope="function"), tenant: TenantContext = Depends(PermissionChecker("consents.read"))):
    return success_response(await service.list_decisions(db, student_id, consent_document_id, consent_status, limit, offset))


@router.post("/student-consents")
async def create_decision(consent: StudentConsentCreate, request: Request, db: AsyncSession = Depends(get_db, scope="function"),
                          tenant: TenantContext = Depends(PermissionChecker("consents.write"))):
    record = await service.decide(db, actor_id=tenant.user_id, student_id=consent.student_id,
        document_id=consent.consent_document_id, parent_id=consent.parent_id, status=consent.consent_status,
        method=consent.consent_method, signature=consent.signature_data, notes=consent.notes,
        ip=request.client.host if request.client else None, user_agent=request.headers.get("user-agent", "")[:500])
    await db.commit()
    return success_response({"id": str(record.id), "student_id": str(record.student_id),
        "consent_document_id": str(record.consent_document_id), "consent_status": record.consent_status})


@router.get("/consent-summary")
async def summary(document_id: UUID | None = None, db: AsyncSession = Depends(get_db, scope="function"),
                  tenant: TenantContext = Depends(PermissionChecker("consents.read"))):
    return success_response(await service.summary(db, document_id))
