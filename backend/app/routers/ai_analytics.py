"""
AI Analytics Router
Provides endpoints for AI-powered analytics and predictions
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.ai_service import ai_service
from app.core.database import get_db
from app.core.security import PermissionChecker, TenantContext
from app.core.responses import success_response, NotFoundException
from app.infrastructure.models.models import (
    Student, AttendanceRecord, Payment, Debt, 
    Parent, User, Receipt, Grade, DebtStatus
)


router = APIRouter(prefix="/api/ai", tags=["AI Analytics"])


def _status_value(value) -> str:
    if value is None:
        return ""
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


@router.get("/student-performance/{student_id}")
async def get_student_performance_prediction(
    student_id: str,
    tenant: TenantContext = Depends(PermissionChecker("students.read")),
    db: AsyncSession = Depends(get_db),
):
    """
    Get AI-powered student performance prediction
    """
    # Fetch student data
    student_result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = student_result.scalar_one_or_none()
    
    if not student:
        raise NotFoundException("Student not found")
    
    # Fetch attendance data
    attendance_result = await db.execute(
        select(AttendanceRecord)
        .where(AttendanceRecord.student_id == student_id)
        .order_by(AttendanceRecord.attendance_date.desc())
        .limit(30)
    )
    attendance_records = attendance_result.scalars().all()
    
    # Calculate attendance rate
    present_count = sum(1 for r in attendance_records if r.status == "PRESENT")
    attendance_rate = (present_count / len(attendance_records) * 100) if attendance_records else 0
    
    # Fetch real grade data from database
    grades_result = await db.execute(
        select(Grade)
        .where(Grade.student_id == student_id)
        .order_by(Grade.exam_date.desc())
        .limit(20)
    )
    grade_records = grades_result.scalars().all()
    
    # Extract historical grades from real data
    historical_grades = [float(g.score) for g in grade_records] if grade_records else []
    
    # If no grades found, use default values
    if not historical_grades:
        historical_grades = [70.0]
    
    # Calculate study hours based on grade types (mock estimation)
    # More homework/projects = more study hours
    study_hours = 5 + len([g for g in grade_records if g.grade_type in ["HOMEWORK", "PROJECT"]]) if grade_records else 5
    
    # Get prediction
    prediction = await ai_service.predict_student_performance(
        student_id=student_id,
        historical_grades=historical_grades,
        attendance_rate=attendance_rate,
        study_hours=study_hours
    )
    
    return success_response(prediction)


@router.get("/attendance-analysis")
async def get_attendance_analysis(
    days: int = 30,
    tenant: TenantContext = Depends(PermissionChecker("attendance.read")),
    db: AsyncSession = Depends(get_db),
):
    """
    Get AI-powered attendance pattern analysis
    """
    start_date = datetime.now() - timedelta(days=days)
    
    # Fetch attendance data
    attendance_result = await db.execute(
        select(AttendanceRecord)
        .where(AttendanceRecord.attendance_date >= start_date)
        .where(AttendanceRecord.organization_id == tenant.organization_id)
    )
    attendance_records = attendance_result.scalars().all()
    
    # Format for AI service
    attendance_data = [
        {
            "student_id": str(r.student_id),
            "date": r.attendance_date.isoformat() if r.attendance_date else None,
            "status": _status_value(r.status) or "unknown"
        }
        for r in attendance_records
    ]
    
    # Get analysis
    analysis = await ai_service.analyze_attendance_patterns(
        attendance_data=attendance_data,
        period_days=days
    )
    
    return success_response(analysis)


@router.get("/payment-forecast")
async def get_payment_forecast(
    months: int = 6,
    tenant: TenantContext = Depends(PermissionChecker("finance.read")),
    db: AsyncSession = Depends(get_db),
):
    """
    Get AI-powered payment collection forecast with detailed analysis
    """
    # Fetch payment history
    payment_result = await db.execute(
        select(Payment)
        .where(Payment.organization_id == tenant.organization_id)
        .where(Payment.created_at >= datetime.now() - timedelta(days=180))
        .order_by(Payment.created_at.desc())
    )
    payments = payment_result.scalars().all()
    
    # Calculate outstanding debt
    debt_result = await db.execute(
        select(Debt)
        .where(Debt.organization_id == tenant.organization_id)
        .where(Debt.status == DebtStatus.UNPAID)
    )
    debts = debt_result.scalars().all()
    outstanding_debt = sum((d.remaining_amount for d in debts), Decimal("0")) if debts else Decimal("0")
    
    # Format for AI service
    payment_history = [
        {
            "date": p.created_at.isoformat() if p.created_at else None,
            "amount": float(p.amount)
        }
        for p in payments
    ]
    
    # Get detailed forecast with risk assessment
    forecast = await ai_service.forecast_payment_collection(
        payment_history=payment_history,
        outstanding_debt=outstanding_debt,
        forecast_months=months
    )
    
    return success_response(forecast)


@router.get("/canteen-analysis")
async def get_canteen_analysis(
    days: int = 30,
    tenant: TenantContext = Depends(PermissionChecker("students.read")),
    db: AsyncSession = Depends(get_db),
):
    """
    Get AI-powered canteen operations analysis
    """
    # Mock sales data (would come from actual sales records)
    sales_data = [
        {"product": "Sandviç", "amount": 15.0, "date": (datetime.now() - timedelta(days=i)).isoformat()}
        for i in range(days)
    ]
    
    # Mock inventory data (would come from actual inventory records)
    inventory_data = [
        {"product": "Sandviç", "stock": 5, "threshold": 10},
        {"product": "Su", "stock": 20, "threshold": 15},
        {"product": "Meyve Suyu", "stock": 8, "threshold": 10},
        {"product": "Bisküvi", "stock": 25, "threshold": 20},
        {"product": "Çikolata", "stock": 3, "threshold": 10}
    ]
    
    # Get analysis
    analysis = await ai_service.analyze_canteen_operations(
        sales_data=sales_data,
        inventory_data=inventory_data,
        period_days=days
    )
    
    return success_response(analysis)


@router.get("/students-overview")
async def get_students_overview_analysis(
    tenant: TenantContext = Depends(PermissionChecker("students.read")),
    db: AsyncSession = Depends(get_db),
):
    """
    Get AI-powered students overview analysis
    """
    # Fetch students
    students_result = await db.execute(
        select(Student)
        .where(Student.organization_id == tenant.organization_id)
    )
    students = students_result.scalars().all()
    
    # Fetch grades
    grades_result = await db.execute(
        select(Grade)
        .where(Grade.organization_id == tenant.organization_id)
    )
    grades = grades_result.scalars().all()
    
    # Fetch attendance
    attendance_result = await db.execute(
        select(AttendanceRecord)
        .where(AttendanceRecord.organization_id == tenant.organization_id)
        .limit(1000)
    )
    attendance = attendance_result.scalars().all()
    
    # Format data for AI service
    students_data = [
        {"id": str(s.id), "status": _status_value(s.status) or "ACTIVE"}
        for s in students
    ]
    
    grades_data = [
        {"score": float(g.score)}
        for g in grades if g.score is not None
    ]
    
    attendance_data = [
        {"status": _status_value(a.status)}
        for a in attendance
    ]
    
    # Get analysis
    analysis = await ai_service.analyze_students_overview(
        students_data=students_data,
        grades_data=grades_data,
        attendance_data=attendance_data
    )
    
    return success_response(analysis)


@router.get("/parents-overview")
async def get_parents_overview_analysis(
    tenant: TenantContext = Depends(PermissionChecker("students.read")),
    db: AsyncSession = Depends(get_db),
):
    """
    Get AI-powered parents overview analysis
    """
    try:
        # Fetch parents
        parents_result = await db.execute(
            select(Parent)
            .where(Parent.organization_id == tenant.organization_id)
        )
        parents = parents_result.scalars().all()
        
        # Fetch communication data (mock - would come from actual communication records)
        communication_data = []
        
        # Fetch payment data (use empty array since Payment doesn't have parent_id)
        payment_data = []
        
        # Format data for AI service
        parents_data = [
            {
                "id": str(p.id),
                "status": "ACTIVE" if getattr(p, "receive_notifications", True) else "PASSIVE",
            }
            for p in parents
        ]
        
        # Get analysis
        analysis = await ai_service.analyze_parents_overview(
            parents_data=parents_data,
            communication_data=communication_data,
            payment_data=payment_data
        )
        
        return success_response(analysis)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise


@router.get("/parent-satisfaction")
async def get_parent_satisfaction_analysis(
    tenant: TenantContext = Depends(PermissionChecker("parents.read")),
    db: AsyncSession = Depends(get_db),
):
    """
    Get AI-powered parent satisfaction analysis
    """
    # Mock feedback data (would come from actual feedback records)
    feedback_data = [
        {"rating": 4, "comment": "Good communication with teachers"},
        {"rating": 5, "comment": "Very satisfied with the school"},
        {"rating": 3, "comment": "Could improve response times"},
        {"rating": 4, "comment": "Happy with academic progress"},
        {"rating": 5, "comment": "Excellent facilities"}
    ]
    
    # Mock communication data
    communication_data = [
        {
            "sent_at": (datetime.now() - timedelta(hours=2)).isoformat(),
            "responded_at": (datetime.now() - timedelta(hours=1)).isoformat()
        },
        {
            "sent_at": (datetime.now() - timedelta(hours=24)).isoformat(),
            "responded_at": (datetime.now() - timedelta(hours=20)).isoformat()
        }
    ]
    
    # Get analysis
    analysis = await ai_service.analyze_parent_satisfaction(
        feedback_data=feedback_data,
        communication_data=communication_data
    )
    
    return success_response(analysis)


@router.get("/teacher-performance/{teacher_id}")
async def get_teacher_performance_analysis(
    teacher_id: str,
    tenant: TenantContext = Depends(PermissionChecker("user.read")),
    db: AsyncSession = Depends(get_db),
):
    """
    Get AI-powered teacher performance analysis
    """
    # Fetch teacher
    user_result = await db.execute(
        select(User).where(User.id == teacher_id)
    )
    teacher = user_result.scalar_one_or_none()
    
    if not teacher:
        raise NotFoundException("Teacher not found")
    
    # Mock data (would come from actual records)
    student_grades = [78.0, 82.0, 85.0, 79.0, 88.0, 76.0, 84.0, 81.0]
    attendance_rates = [92.0, 95.0, 88.0, 94.0, 91.0, 93.0, 90.0, 96.0]
    parent_feedback = [
        {"rating": 4, "comment": "Great teacher"},
        {"rating": 5, "comment": "Very helpful"},
        {"rating": 4, "comment": "Good communication"}
    ]
    
    # Get analysis
    analysis = await ai_service.analyze_teacher_performance(
        teacher_id=teacher_id,
        student_grades=student_grades,
        attendance_rates=attendance_rates,
        parent_feedback=parent_feedback
    )
    
    return success_response(analysis)


@router.get("/insights-report")
async def get_insights_report(
    days: int = 30,
    tenant: TenantContext = Depends(PermissionChecker("students.read")),
    db: AsyncSession = Depends(get_db),
):
    """
    Get comprehensive AI insights report
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Generate report
    report = await ai_service.generate_insights_report(
        organization_id=str(tenant.organization_id),
        date_range=(start_date, end_date)
    )
    
    return success_response(report)
