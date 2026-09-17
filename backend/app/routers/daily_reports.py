from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional, List
from uuid import UUID
from datetime import datetime, date
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_tenant_context
from app.core.permissions import PermissionChecker
from app.core.responses import success_response, paginate
from app.domain.entities.user import User
from app.domain.entities.daily_development_report import DailyDevelopmentReport, DailyDevelopmentReportCreate, DailyDevelopmentReportUpdate
from app.core.tenant import TenantContext

router = APIRouter(prefix="/api/daily-reports", tags=["Daily Reports"])


class BulkDailyReportCreate(BaseModel):
    class_id: UUID
    date: date
    reports: List[DailyDevelopmentReportCreate]


def report_to_dict(report: DailyDevelopmentReport) -> dict:
    return {
        "id": str(report.id),
        "student_id": str(report.student_id),
        "class_id": str(report.class_id),
        "date": report.date.isoformat() if report.date else None,
        "meal_status": report.meal_status,
        "sleep_status": report.sleep_status,
        "mood": report.mood,
        "activities": report.activities,
        "teacher_notes": report.teacher_notes,
        "recorded_by": str(report.recorded_by) if report.recorded_by else None,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "updated_at": report.updated_at.isoformat() if report.updated_at else None
    }


@router.get("/")
async def list_daily_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    class_id: Optional[UUID] = None,
    student_id: Optional[UUID] = None,
    date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("daily_reports.read"))
):
    """List daily reports with pagination and filters"""
    from app.infrastructure.models.models import DailyDevelopmentReport as DailyReportModel
    from app.infrastructure.models.models import Student
    
    query = select(DailyReportModel)
    
    # Apply tenant filters
    if tenant.organization_id:
        query = query.join(Student, DailyReportModel.student_id == Student.id)
        query = query.where(Student.organization_id == tenant.organization_id)
    
    if tenant.branch_ids:
        query = query.where(Student.branch_id.in_(tenant.branch_ids))
    
    # Apply additional filters
    if class_id:
        query = query.where(DailyReportModel.class_id == class_id)
    if student_id:
        query = query.where(DailyReportModel.student_id == student_id)
    if date:
        query = query.where(DailyReportModel.date == date)
    
    query = query.order_by(DailyReportModel.date.desc(), DailyReportModel.created_at.desc())
    
    result = await db.execute(query)
    reports = result.scalars().all()
    
    total = len(reports)
    start = (page - 1) * page_size
    end = start + page_size
    paginated_reports = reports[start:end]
    
    return paginate(
        [report_to_dict(DailyDevelopmentReport.model_validate(r)) for r in paginated_reports],
        total,
        page,
        page_size
    )


@router.get("/{report_id}")
async def get_daily_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("academic.read"))
):
    """Get a specific daily report"""
    from app.infrastructure.models.models import DailyDevelopmentReport as DailyReportModel
    
    result = await db.execute(
        select(DailyReportModel).where(DailyReportModel.id == report_id)
    )
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(status_code=404, detail="Daily report not found")
    
    return success_response(report_to_dict(DailyDevelopmentReport.model_validate(report)))


@router.post("/")
async def create_daily_report(
    report: DailyDevelopmentReportCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("academic.write"))
):
    """Create a new daily report"""
    from app.infrastructure.models.models import DailyDevelopmentReport as DailyReportModel
    
    # Check if report already exists for this student on this date
    existing_result = await db.execute(
        select(DailyReportModel).where(
            and_(
                DailyReportModel.student_id == report.student_id,
                DailyReportModel.date == report.date
            )
        )
    )
    existing = existing_result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(status_code=400, detail="Report already exists for this student on this date")
    
    new_report = DailyReportModel(
        student_id=report.student_id,
        class_id=report.class_id,
        date=report.date,
        meal_status=report.meal_status,
        sleep_status=report.sleep_status,
        mood=report.mood,
        activities=report.activities,
        teacher_notes=report.teacher_notes,
        recorded_by=tenant.id
    )
    
    db.add(new_report)
    await db.commit()
    await db.refresh(new_report)
    
    return success_response(report_to_dict(DailyDevelopmentReport.model_validate(new_report)), "Daily report created")


@router.post("/bulk")
async def create_bulk_daily_reports(
    bulk_data: BulkDailyReportCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("academic.write"))
):
    """Create multiple daily reports at once (for a class)"""
    from app.infrastructure.models.models import DailyDevelopmentReport as DailyReportModel
    
    created_reports = []
    
    for report_data in bulk_data.reports:
        # Check if report already exists
        existing_result = await db.execute(
            select(DailyReportModel).where(
                and_(
                    DailyReportModel.student_id == report_data.student_id,
                    DailyReportModel.date == bulk_data.date
                )
            )
        )
        existing = existing_result.scalar_one_or_none()
        
        if not existing:
            new_report = DailyReportModel(
                student_id=report_data.student_id,
                class_id=bulk_data.class_id,
                date=bulk_data.date,
                meal_status=report_data.meal_status,
                sleep_status=report_data.sleep_status,
                mood=report_data.mood,
                activities=report_data.activities,
                teacher_notes=report_data.teacher_notes,
                recorded_by=tenant.id
            )
            db.add(new_report)
            created_reports.append(new_report)
    
    await db.commit()
    
    for report in created_reports:
        await db.refresh(report)
    
    return success_response(
        [report_to_dict(DailyDevelopmentReport.model_validate(r)) for r in created_reports],
        f"{len(created_reports)} daily reports created"
    )


@router.put("/{report_id}")
async def update_daily_report(
    report_id: UUID,
    report_update: DailyDevelopmentReportUpdate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("academic.write"))
):
    """Update a daily report"""
    from app.infrastructure.models.models import DailyDevelopmentReport as DailyReportModel
    
    result = await db.execute(
        select(DailyReportModel).where(DailyReportModel.id == report_id)
    )
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(status_code=404, detail="Daily report not found")
    
    # Update fields
    if report_update.meal_status is not None:
        report.meal_status = report_update.meal_status
    if report_update.sleep_status is not None:
        report.sleep_status = report_update.sleep_status
    if report_update.mood is not None:
        report.mood = report_update.mood
    if report_update.activities is not None:
        report.activities = report_update.activities
    if report_update.teacher_notes is not None:
        report.teacher_notes = report_update.teacher_notes
    
    await db.commit()
    await db.refresh(report)
    
    return success_response(report_to_dict(DailyDevelopmentReport.model_validate(report)), "Daily report updated")


@router.delete("/{report_id}")
async def delete_daily_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("academic.write"))
):
    """Delete a daily report"""
    from app.infrastructure.models.models import DailyDevelopmentReport as DailyReportModel
    
    result = await db.execute(
        select(DailyReportModel).where(DailyReportModel.id == report_id)
    )
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(status_code=404, detail="Daily report not found")
    
    await db.delete(report)
    await db.commit()
    
    return success_response({"message": "Daily report deleted successfully"})
