"""
Multi-Branch HQ Analytics Module API
Handles financial and academic consolidation across branches
"""
from datetime import datetime, date
from typing import Optional, List
from uuid import UUID
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.responses import success_response
from app.core.security import PermissionChecker, TenantContext
from app.domain.entities import Branch

router = APIRouter(prefix="/api/hq", tags=["HQ"])


# ==================== Schemas ====================

class BranchFinancialSummaryCreate(BaseModel):
    branch_id: UUID
    period: str = Field(..., description="MONTHLY, QUARTERLY, YEARLY")
    year: int = Field(..., ge=2020, le=2100)
    month: Optional[int] = Field(None, ge=1, le=12)
    total_revenue: Decimal = Field(default=0, ge=0)
    total_expenses: Decimal = Field(default=0, ge=0)
    net_profit: Decimal = Field(default=0)
    collection_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    overdue_debt: Decimal = Field(default=0, ge=0)
    student_count: int = Field(default=0, ge=0)

class BranchAcademicSummaryCreate(BaseModel):
    branch_id: UUID
    period: str = Field(..., description="MONTHLY, QUARTERLY, YEARLY")
    year: int = Field(..., ge=2020, le=2100)
    semester: Optional[str] = Field(None, description="FALL, SPRING, SUMMER")
    average_attendance_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    average_exam_score: Optional[Decimal] = Field(None, ge=0, le=100)
    total_students: int = Field(default=0, ge=0)
    total_teachers: int = Field(default=0, ge=0)
    student_retention_rate: Optional[Decimal] = Field(None, ge=0, le=100)


# ==================== Financial Consolidation Endpoints ====================

@router.get("/financial-consolidation")
async def get_financial_consolidation(
    period: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    branch_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("hq.read"))
):
    """Get financial consolidation across branches"""
    from app.domain.entities.hq import BranchFinancialSummary
    
    query = select(BranchFinancialSummary)
    
    conditions = []
    if period:
        conditions.append(BranchFinancialSummary.period == period.upper())
    if year:
        conditions.append(BranchFinancialSummary.year == year)
    if month:
        conditions.append(BranchFinancialSummary.month == month)
    if branch_id:
        conditions.append(BranchFinancialSummary.branch_id == branch_id)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(BranchFinancialSummary.year.desc(), BranchFinancialSummary.month.desc())
    
    result = await db.execute(query)
    summaries = result.scalars().all()
    
    enriched_summaries = []
    total_revenue = Decimal(0)
    total_expenses = Decimal(0)
    total_net_profit = Decimal(0)
    total_students = 0
    
    for summary in summaries:
        # Get branch name
        branch_name = None
        if summary.branch_id:
            branch_result = await db.execute(
                select(Branch).where(Branch.id == summary.branch_id)
            )
            branch = branch_result.scalar_one_or_none()
            if branch:
                branch_name = branch.name
        
        total_revenue += summary.total_revenue
        total_expenses += summary.total_expenses
        total_net_profit += summary.net_profit
        total_students += summary.student_count
        
        enriched_summaries.append({
            "id": str(summary.id),
            "branch_id": str(summary.branch_id),
            "branch_name": branch_name,
            "period": summary.period,
            "year": summary.year,
            "month": summary.month,
            "total_revenue": float(summary.total_revenue),
            "total_expenses": float(summary.total_expenses),
            "net_profit": float(summary.net_profit),
            "collection_rate": float(summary.collection_rate) if summary.collection_rate else None,
            "overdue_debt": float(summary.overdue_debt),
            "student_count": summary.student_count,
            "created_at": summary.created_at.isoformat(),
            "updated_at": summary.updated_at.isoformat()
        })
    
    # Calculate averages
    avg_collection_rate = sum(s.collection_rate or 0 for s in summaries) / len(summaries) if summaries else 0
    
    return success_response({
        "summaries": enriched_summaries,
        "totals": {
            "total_revenue": float(total_revenue),
            "total_expenses": float(total_expenses),
            "total_net_profit": float(total_net_profit),
            "total_students": total_students,
            "avg_collection_rate": float(avg_collection_rate)
        }
    })


@router.post("/financial-summaries")
async def create_financial_summary(
    summary: BranchFinancialSummaryCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("hq.write"))
):
    """Create or update a branch financial summary"""
    from app.domain.entities.hq import BranchFinancialSummary
    
    # Check if summary already exists
    existing_result = await db.execute(
        select(BranchFinancialSummary).where(
            and_(
                BranchFinancialSummary.branch_id == summary.branch_id,
                BranchFinancialSummary.period == summary.period.upper(),
                BranchFinancialSummary.year == summary.year,
                BranchFinancialSummary.month == summary.month
            )
        )
    )
    existing = existing_result.scalar_one_or_none()
    
    if existing:
        existing.total_revenue = summary.total_revenue
        existing.total_expenses = summary.total_expenses
        existing.net_profit = summary.net_profit
        existing.collection_rate = summary.collection_rate
        existing.overdue_debt = summary.overdue_debt
        existing.student_count = summary.student_count
    else:
        new_summary = BranchFinancialSummary(
            branch_id=summary.branch_id,
            period=summary.period.upper(),
            year=summary.year,
            month=summary.month,
            total_revenue=summary.total_revenue,
            total_expenses=summary.total_expenses,
            net_profit=summary.net_profit,
            collection_rate=summary.collection_rate,
            overdue_debt=summary.overdue_debt,
            student_count=summary.student_count
        )
        db.add(new_summary)
    
    await db.commit()
    
    return success_response({
        "message": "Financial summary saved successfully",
        "branch_id": str(summary.branch_id),
        "period": summary.period.upper(),
        "year": summary.year,
        "month": summary.month
    })


@router.get("/financial-comparison")
async def get_financial_comparison(
    year: int = Query(..., description="Year to compare"),
    period: str = Query("MONTHLY", description="Period type"),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("hq.read"))
):
    """Get financial comparison across branches"""
    from app.domain.entities.hq import BranchFinancialSummary
    
    result = await db.execute(
        select(BranchFinancialSummary).where(
            and_(
                BranchFinancialSummary.year == year,
                BranchFinancialSummary.period == period.upper()
            )
        )
    )
    summaries = result.scalars().all()
    
    comparison = []
    for summary in summaries:
        branch_result = await db.execute(
            select(Branch).where(Branch.id == summary.branch_id)
        )
        branch = branch_result.scalar_one_or_none()
        
        comparison.append({
            "branch_id": str(summary.branch_id),
            "branch_name": branch.name if branch else None,
            "total_revenue": float(summary.total_revenue),
            "total_expenses": float(summary.total_expenses),
            "net_profit": float(summary.net_profit),
            "profit_margin": float(summary.net_profit / summary.total_revenue * 100) if summary.total_revenue > 0 else 0,
            "collection_rate": float(summary.collection_rate) if summary.collection_rate else 0,
            "overdue_debt": float(summary.overdue_debt),
            "student_count": summary.student_count
        })
    
    # Sort by net profit
    comparison.sort(key=lambda x: x["net_profit"], reverse=True)
    
    return success_response(comparison)


# ==================== Academic Comparison Endpoints ====================

@router.get("/academic-comparison")
async def get_academic_comparison(
    year: int = Query(..., description="Year to compare"),
    semester: Optional[str] = Query(None, description="Semester to filter"),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("hq.read"))
):
    """Get academic comparison across branches"""
    from app.domain.entities.hq import BranchAcademicSummary
    
    query = select(BranchAcademicSummary).where(BranchAcademicSummary.year == year)
    
    if semester:
        query = query.where(BranchAcademicSummary.semester == semester.upper())
    
    result = await db.execute(query)
    summaries = result.scalars().all()
    
    comparison = []
    for summary in summaries:
        branch_result = await db.execute(
            select(Branch).where(Branch.id == summary.branch_id)
        )
        branch = branch_result.scalar_one_or_none()
        
        comparison.append({
            "branch_id": str(summary.branch_id),
            "branch_name": branch.name if branch else None,
            "period": summary.period,
            "semester": summary.semester,
            "average_attendance_rate": float(summary.average_attendance_rate) if summary.average_attendance_rate else 0,
            "average_exam_score": float(summary.average_exam_score) if summary.average_exam_score else 0,
            "total_students": summary.total_students,
            "total_teachers": summary.total_teachers,
            "student_teacher_ratio": float(summary.total_students / summary.total_teachers) if summary.total_teachers > 0 else 0,
            "student_retention_rate": float(summary.student_retention_rate) if summary.student_retention_rate else 0
        })
    
    # Sort by average exam score
    comparison.sort(key=lambda x: x["average_exam_score"], reverse=True)
    
    return success_response(comparison)


@router.post("/academic-summaries")
async def create_academic_summary(
    summary: BranchAcademicSummaryCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("hq.write"))
):
    """Create or update a branch academic summary"""
    from app.domain.entities.hq import BranchAcademicSummary
    
    # Check if summary already exists
    existing_result = await db.execute(
        select(BranchAcademicSummary).where(
            and_(
                BranchAcademicSummary.branch_id == summary.branch_id,
                BranchAcademicSummary.period == summary.period.upper(),
                BranchAcademicSummary.year == summary.year,
                BranchAcademicSummary.semester == summary.semester
            )
        )
    )
    existing = existing_result.scalar_one_or_none()
    
    if existing:
        existing.average_attendance_rate = summary.average_attendance_rate
        existing.average_exam_score = summary.average_exam_score
        existing.total_students = summary.total_students
        existing.total_teachers = summary.total_teachers
        existing.student_retention_rate = summary.student_retention_rate
    else:
        new_summary = BranchAcademicSummary(
            branch_id=summary.branch_id,
            period=summary.period.upper(),
            year=summary.year,
            semester=summary.semester,
            average_attendance_rate=summary.average_attendance_rate,
            average_exam_score=summary.average_exam_score,
            total_students=summary.total_students,
            total_teachers=summary.total_teachers,
            student_retention_rate=summary.student_retention_rate
        )
        db.add(new_summary)
    
    await db.commit()
    
    return success_response({
        "message": "Academic summary saved successfully",
        "branch_id": str(summary.branch_id),
        "period": summary.period.upper(),
        "year": summary.year,
        "semester": summary.semester
    })


@router.get("/dashboard")
async def get_hq_dashboard(
    year: int = Query(..., description="Dashboard year"),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("hq.read"))
):
    """Get HQ dashboard summary with key metrics"""
    from app.domain.entities.hq import BranchFinancialSummary, BranchAcademicSummary
    
    # Get financial summaries for the year
    financial_result = await db.execute(
        select(BranchFinancialSummary).where(BranchFinancialSummary.year == year)
    )
    financial_summaries = financial_result.scalars().all()
    
    # Get academic summaries for the year
    academic_result = await db.execute(
        select(BranchAcademicSummary).where(BranchAcademicSummary.year == year)
    )
    academic_summaries = academic_result.scalars().all()
    
    # Calculate totals
    total_revenue = sum(s.total_revenue for s in financial_summaries)
    total_expenses = sum(s.total_expenses for s in financial_summaries)
    total_net_profit = sum(s.net_profit for s in financial_summaries)
    total_students = sum(s.student_count for s in financial_summaries)
    total_teachers = sum(s.total_teachers for s in academic_summaries)
    
    # Calculate averages
    avg_attendance = sum(s.average_attendance_rate or 0 for s in academic_summaries) / len(academic_summaries) if academic_summaries else 0
    avg_exam_score = sum(s.average_exam_score or 0 for s in academic_summaries) / len(academic_summaries) if academic_summaries else 0
    avg_collection_rate = sum(s.collection_rate or 0 for s in financial_summaries) / len(financial_summaries) if financial_summaries else 0
    
    # Get branch count
    branch_count = len(set(s.branch_id for s in financial_summaries))
    
    return success_response({
        "year": year,
        "financial_metrics": {
            "total_revenue": float(total_revenue),
            "total_expenses": float(total_expenses),
            "total_net_profit": float(total_net_profit),
            "avg_collection_rate": float(avg_collection_rate),
            "branch_count": branch_count
        },
        "academic_metrics": {
            "total_students": total_students,
            "total_teachers": total_teachers,
            "avg_attendance_rate": float(avg_attendance),
            "avg_exam_score": float(avg_exam_score),
            "student_teacher_ratio": float(total_students / total_teachers) if total_teachers > 0 else 0
        },
        "branch_count": branch_count
    })
