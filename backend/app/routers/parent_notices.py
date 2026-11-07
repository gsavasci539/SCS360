from __future__ import annotations
from uuid import UUID
from typing import Optional
from datetime import datetime
from pydantic import BaseModel

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_tenant_context
from app.core.permissions import PermissionChecker
from app.core.responses import success_response, paginate
from app.core.tenant import TenantContext
from app.domain.entities.user import User
from app.infrastructure.repositories.base import BaseRepository

router = APIRouter(prefix="/api/parent-notices", tags=["Parent Notices"])


class ParentNoticeCreate(BaseModel):
    student_id: UUID
    type: str
    description: Optional[str] = None


class ParentNoticeUpdate(BaseModel):
    type: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


from app.infrastructure.models.models import ParentNotice, Student
from app.core.student_access import accessible_student_ids, require_student_access
from app.core.exceptions import NotFoundException


def parent_notice_to_dict(notice, student=None):
    return {"id": str(notice.id), "student_id": str(notice.student_id),
        "student_name": f"{student.first_name} {student.last_name}" if student else None,
        "type": notice.type, "description": notice.description, "status": notice.status,
        "created_at": notice.created_at.isoformat() if notice.created_at else None}


async def notice_query(db, tenant):
    repo = BaseRepository(db, tenant)
    query = repo._branch_filter(repo._org_filter(select(ParentNotice, Student)
        .join(Student, Student.id == ParentNotice.student_id), ParentNotice), Student)
    query = query.where(ParentNotice.deleted_at.is_(None), Student.deleted_at.is_(None))
    ids = await accessible_student_ids(db, tenant)
    return query.where(Student.id.in_(ids)) if ids is not None else query


async def stored_notice(db, tenant, identifier):
    row = (await db.execute((await notice_query(db, tenant)).where(ParentNotice.id == identifier))).one_or_none()
    return row[0] if row else None


def medication_status(schedule) -> str:
    from app.application.services.infirmary_service import medicine_request_status
    return medicine_request_status(schedule)


async def medication_notices(db: AsyncSession, tenant: TenantContext) -> list[dict]:
    if not tenant.has_permission("health.read"):
        return []
    from app.application.services.infirmary_service import instructions
    from app.domain.entities.health import MedicationSchedule
    from app.infrastructure.models.models import Student

    conditions = []
    if not tenant.is_super_admin:
        conditions.append(Student.organization_id == tenant.organization_id)
    if tenant.branch_ids:
        conditions.append(Student.branch_id.in_(tenant.branch_ids))
    ids = await accessible_student_ids(db, tenant)
    if ids is not None:
        conditions.append(Student.id.in_(ids))
    conditions.append(Student.deleted_at.is_(None))

    query = (
        select(MedicationSchedule, Student)
        .join(Student, MedicationSchedule.student_id == Student.id)
        .order_by(MedicationSchedule.created_at.desc())
    )
    if conditions:
        query = query.where(and_(*conditions))

    result = await db.execute(query)
    items = []
    for schedule, student in result:
        items.append({
            "id": str(schedule.id),
            "student_id": str(student.id),
            "student_name": f"{student.first_name} {student.last_name}",
            "type": "MEDICATION",
            "description": f"{schedule.medication_name} - {schedule.dosage} - {schedule.frequency}",
            "status": medication_status(schedule),
            "created_at": schedule.created_at.isoformat() if schedule.created_at else None,
            "source": "medicine_request",
            "medicine_name": schedule.medication_name,
            "dosage": schedule.dosage,
            "time_to_give": schedule.frequency,
            "instructions": instructions(schedule),
        })
    return items


@router.get("")
async def list_parent_notices(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    search: Optional[str] = None,
    tenant: TenantContext = Depends(PermissionChecker("parent_notices.read")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    # Filter by organization
    stored = [parent_notice_to_dict(n, student) for n, student in (await db.execute(await notice_query(db, tenant))).all()]
    filtered = stored + await medication_notices(db, tenant)
    
    if search:
        lowered = search.lower()
        filtered = [
            n for n in filtered
            if lowered in str(n.get("student_name", "")).lower()
            or lowered in str(n.get("description", "")).lower()
        ]

    filtered.sort(key=lambda n: n.get("created_at") or "", reverse=True)
    
    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size
    items = filtered[start:end]
    
    return success_response(paginate(items, total, page, page_size))


@router.post("")
async def create_parent_notice(
    body: ParentNoticeCreate,
    tenant: TenantContext = Depends(PermissionChecker("parent_notices.write")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    from app.infrastructure.models.models import Student

    student = await BaseRepository(db, tenant).get_by_id(body.student_id, Student)
    await require_student_access(db, tenant, student.id)
    student_name = f"{student.first_name} {student.last_name}" if student else "Öğrenci"

    
    notice = ParentNotice(
        student_id=body.student_id,
        type=body.type,
        description=body.description,
        organization_id=student.organization_id,
        created_by=tenant.user_id,
        created_at=datetime.utcnow()
    )
    
    # Generate simple ID
    import uuid
    notice.id = uuid.uuid4()
    
    db.add(notice)
    await db.flush()
    
    return success_response(parent_notice_to_dict(notice, student), "Veli talebi oluşturuldu")


@router.get("/{notice_id}")
async def get_parent_notice(
    notice_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("parent_notices.read")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    notice = await stored_notice(db, tenant, notice_id)
    
    if not notice:
        notice = next((n for n in await medication_notices(db, tenant) if str(n["id"]) == str(notice_id)), None)
        if not notice:
            raise NotFoundException("Veli talebi bulunamadı")
        return success_response(notice)
    
    return success_response(parent_notice_to_dict(notice))


@router.put("/{notice_id}")
async def update_parent_notice(
    notice_id: UUID,
    body: ParentNoticeUpdate,
    tenant: TenantContext = Depends(PermissionChecker("parent_notices.write")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    notice = await stored_notice(db, tenant, notice_id)
    
    if not notice:
        from app.domain.entities.health import MedicationSchedule
        if not any(n["id"] == str(notice_id) for n in await medication_notices(db, tenant)):
            raise NotFoundException("Veli talebi bulunamadı")
        result = await db.execute(select(MedicationSchedule).where(MedicationSchedule.id == notice_id))
        schedule = result.scalar_one_or_none()
        if not schedule:
            return success_response(None, "Veli talebi bulunamadı", success=False)
        from app.application.services.infirmary_service import decide_request, medicine_request_status
        await decide_request(db, tenant, notice_id, body.status or medicine_request_status(schedule))
        items = await medication_notices(db, tenant)
        updated = next((n for n in items if str(n["id"]) == str(notice_id)), None)
        return success_response(updated, "Veli talebi güncellendi")
    
    if body.type:
        notice.type = body.type
    if body.description is not None:
        notice.description = body.description
    if body.status:
        notice.status = body.status
    
    return success_response(parent_notice_to_dict(notice), "Veli talebi güncellendi")


@router.delete("/{notice_id}")
async def delete_parent_notice(
    notice_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("parent_notices.write")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    from app.domain.entities.health import MedicationSchedule

    scoped_medication = any(n["id"] == str(notice_id) for n in await medication_notices(db, tenant))
    result = await db.execute(select(MedicationSchedule).where(MedicationSchedule.id == notice_id)) if scoped_medication else None
    schedule = result.scalar_one_or_none() if result else None
    if schedule:
        from app.application.services.infirmary_service import decide_request, medicine_request_status
        status = medicine_request_status(schedule)
        await decide_request(db, tenant, notice_id, "REJECTED" if status == "PENDING" else "COMPLETED" if status == "APPROVED" else status)
        return success_response(message="Veli talebi kapatıldı")

    notice = await stored_notice(db, tenant, notice_id)
    if notice is None:
        raise NotFoundException("Veli talebi bulunamadı")
    from datetime import UTC
    notice.deleted_at = datetime.now(UTC)
    
    return success_response(message="Veli talebi silindi")
