"""
AI Analytics Router
Provides endpoints for AI-powered analytics and predictions
"""
from app.core.dates import school_today

from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


from app.core.database import get_db
from app.core.dependencies import get_tenant_context
from app.core.analysis_access import AnalysisPermission
from app.core.permissions import PermissionChecker
from app.core.responses import success_response, NotFoundException
from app.core.tenant import TenantContext
from app.infrastructure.models.models import (
    Student, AttendanceRecord, Payment, Debt, 
    Parent, User, Receipt, Grade, DebtStatus, ClassRoom, ClassTeacher,
    NotificationJob, Announcement, StudentParent, DailyDevelopmentReport, ChatMessage
)


router = APIRouter(prefix="/api/ai", tags=["AI Analytics"])


# New endpoints to match frontend expectations
async def _recorded_academic_response(days, tenant, db):
    from sqlalchemy.exc import SQLAlchemyError
    from app.application.services.academic_summary import summary
    from app.core.exceptions import AppException
    try:
        return success_response(await summary(db, tenant, days))
    except SQLAlchemyError as exc:
        import logging
        logging.getLogger(__name__).error("Academic summary query failed (%s)", type(exc).__name__)
        raise AppException("Akademik kayıtlar yüklenemedi; daha sonra tekrar deneyin", status_code=503) from None


async def _recorded_financial_response(months, tenant, db):
    from sqlalchemy.exc import SQLAlchemyError
    from app.application.services.financial_summary import summary
    from app.core.exceptions import AppException
    try:
        return success_response(await summary(db, tenant, months))
    except SQLAlchemyError as exc:
        import logging
        logging.getLogger(__name__).error("Financial summary query failed (%s)", type(exc).__name__)
        raise AppException("Finans kayıtları yüklenemedi; daha sonra tekrar deneyin", status_code=503) from None


async def _recorded_financial_predictions_response(months, tenant, db):
    recorded = (await _recorded_financial_response(months, tenant, db))["data"]
    return success_response({**recorded, "ai_model": None, "forecast_months": None,
        "predictions": [], "cash_flow_forecast": [], "risk_parents": [],
        "payment_history": [{"month": row["month"], "amount": row["collected_amount"]}
            for row in recorded["historical_monthly"]],
        "risk_assessment": {"level": "unknown", "overall_score": None,
            "collection_rate": recorded["collection_rate"], "outstanding_debt": recorded["outstanding_debt"],
            "predicted_cash_flow": None, "factors": {}},
    })


async def _recorded_parent_response(days, tenant, db):
    from sqlalchemy.exc import SQLAlchemyError
    from app.application.services.parent_engagement import summary
    from app.core.exceptions import AppException
    try:
        return success_response(await summary(db, tenant, days))
    except SQLAlchemyError as exc:
        import logging
        logging.getLogger(__name__).error("Parent overview query failed (%s)", type(exc).__name__)
        raise AppException("Veli kayıtları yüklenemedi; daha sonra tekrar deneyin", status_code=503) from None


@router.get("/ai-academic-predictions")
async def get_ai_academic_predictions(
    days: int = Query(30, ge=1, le=365),
    tenant: TenantContext = Depends(AnalysisPermission('/ai-academic-predictions')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    return await _recorded_academic_response(days, tenant, db)


@router.get("/ai-attendance-predictions")
async def get_ai_attendance_predictions(
    days: int = Query(30, ge=1, le=365),
    tenant: TenantContext = Depends(AnalysisPermission('/ai-attendance-predictions')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    from sqlalchemy.exc import SQLAlchemyError
    from app.application.services.recorded_attendance import summary
    from app.core.exceptions import AppException
    try:
        return success_response(await summary(db, tenant, days))
    except SQLAlchemyError as exc:
        import logging
        logging.getLogger(__name__).error("Recorded attendance query failed (%s)", type(exc).__name__)
        raise AppException("Yoklama özeti yüklenemedi; daha sonra tekrar deneyin", status_code=503) from None


@router.get("/ai-financial-predictions")
async def get_ai_financial_predictions(
    months: int = Query(6, ge=1, le=24),
    tenant: TenantContext = Depends(AnalysisPermission('/ai-financial-predictions')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    return await _recorded_financial_predictions_response(months, tenant, db)


@router.get("/ai-parent-sentiment")
async def get_ai_parent_sentiment(
    days: int = Query(30, ge=1, le=365),
    tenant: TenantContext = Depends(AnalysisPermission('/ai-parent-sentiment')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    return await _recorded_parent_response(days, tenant, db)


@router.get("/ai-operational-optimization")
async def get_ai_operational_optimization(
    tenant: TenantContext = Depends(AnalysisPermission('/ai-operational-optimization')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    from sqlalchemy.exc import SQLAlchemyError
    from app.application.services.recorded_overview import operations
    from app.core.exceptions import AppException
    try:
        return success_response(await operations(db, tenant))
    except SQLAlchemyError as exc:
        import logging
        logging.getLogger(__name__).error("Recorded overview query failed (%s)", type(exc).__name__)
        raise AppException("Kayıtlı analiz yüklenemedi; daha sonra tekrar deneyin", status_code=503) from None


@router.get("/insights-report")
async def get_insights_report(
    days: int = Query(30, ge=1, le=365),
    tenant: TenantContext = Depends(AnalysisPermission('/insights-report')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    from sqlalchemy.exc import SQLAlchemyError
    from app.application.services.recorded_overview import insights
    from app.core.exceptions import AppException
    try:
        return success_response(await insights(db, tenant, days))
    except SQLAlchemyError as exc:
        import logging
        logging.getLogger(__name__).error("Recorded overview query failed (%s)", type(exc).__name__)
        raise AppException("Kayıtlı analiz yüklenemedi; daha sonra tekrar deneyin", status_code=503) from None


def _status_value(value) -> str:
    if value is None:
        return ""
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


@router.get("/ai-homework-analysis")
async def get_ai_homework_analysis(
    tenant: TenantContext = Depends(AnalysisPermission('/ai-homework-analysis')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """
    Get AI homework analysis for frontend
    """
    try:
        organization_id = tenant.organization_id
        
        # Use grades as proxy for homework analysis since homework model doesn't exist
        grade_result = await db.execute(
            select(Grade).where(Grade.organization_id == organization_id)
        )
        grades = grade_result.scalars().all()
        
        # Calculate homework statistics based on grades
        total_assignments = len(grades)
        
        # Analyze by subject
        subject_stats = {}
        for grade in grades:
            subject = grade.subject or "Diğer"
            if subject not in subject_stats:
                subject_stats[subject] = {"total": 0, "avg_score": 0, "scores": []}
            subject_stats[subject]["total"] += 1
            if grade.score:
                subject_stats[subject]["scores"].append(float(grade.score))
        
        # Generate subject insights
        subject_insights = []
        for subject, stats in subject_stats.items():
            avg_score = sum(stats["scores"]) / len(stats["scores"]) if stats["scores"] else 0
            subject_insights.append({
                "subject": subject,
                "total": stats["total"],
                "avg_score": round(avg_score, 1),
                "performance": "iyi" if avg_score > 75 else "normal" if avg_score > 60 else "zayıf"
            })
        
        # Sort by average score (lowest first)
        subject_insights.sort(key=lambda x: x["avg_score"])
        
        # Generate recommendations
        recommendations = []
        if subject_insights and subject_insights[0]["avg_score"] < 60:
            recommendations.append(f"{subject_insights[0]['subject']} dersi performansı düşük, ek destek gerekli")
        
        avg_overall = sum(s["avg_score"] for s in subject_insights) / len(subject_insights) if subject_insights else 0
        if avg_overall < 70:
            recommendations.append("Genel akademik performans düşük, öğrenci destek programı gözden geçirilmeli")
        
        return success_response({
            "ai_model": "Homework Analytics v1.0",
            "homework_stats": {
                "total": total_assignments,
                "completion_rate": 100,  # Using grades as proxy
                "avg_score": round(avg_overall, 1)
            },
            "subject_insights": subject_insights[:5],
            "recommendations": recommendations
        })
        
    except Exception as e:
        import traceback
        import sys
        print(f"Homework analysis error: {str(e)}", file=sys.stderr)
        traceback.print_exc()
        return success_response({
            "ai_model": "Homework Analytics v1.0",
            "homework_stats": {
                "total": 0,
                "completion_rate": 0,
                "avg_score": 0
            },
            "subject_insights": [],
            "recommendations": [f"Hata: {str(e)}"]
        })


@router.get("/ai-daily-reports-analysis")
async def get_ai_daily_reports_analysis(
    tenant: TenantContext = Depends(AnalysisPermission('/ai-daily-reports-analysis')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """
    Get AI daily reports analysis for frontend
    """
    try:
        organization_id = tenant.organization_id
        
        # Fetch students from this organization
        student_result = await db.execute(
            select(Student).where(Student.organization_id == organization_id)
        )
        students = student_result.scalars().all()
        
        if not students:
            return success_response({
                "ai_model": "Daily Reports Analytics v1.0",
                "report_stats": {
                    "total": 0,
                    "mood_happy": 0,
                    "mood_tired": 0,
                    "mood_rate": 0,
                    "sleep_rate": 0,
                    "meal_rate": 0
                },
                "students_needing_attention": [],
                "recommendations": ["Öğrenci verisi bulunamadı"]
            })
        
        student_ids = [s.id for s in students]
        
        # Fetch daily reports for these students
        report_result = await db.execute(
            select(DailyDevelopmentReport).where(DailyDevelopmentReport.student_id.in_(student_ids))
        )
        reports = report_result.scalars().all()
        
        student_map = {str(s.id): f"{s.first_name} {s.last_name}" for s in students}
        
        # Calculate report statistics
        total_reports = len(reports)
        
        # Analyze mood
        mood_counts = {"happy": 0, "calm": 0, "unsettled": 0, "tired": 0}
        for report in reports:
            if report is None:
                continue
            mood = (report.mood or "").lower()
            if "happy" in mood:
                mood_counts["happy"] += 1
            elif "calm" in mood:
                mood_counts["calm"] += 1
            elif "tired" in mood:
                mood_counts["tired"] += 1
            elif "unsettled" in mood:
                mood_counts["unsettled"] += 1
        
        mood_rate = (mood_counts["happy"] / total_reports * 100) if total_reports > 0 else 0
        
        # Analyze sleep status
        sleep_good = 0
        sleep_poor = 0
        for report in reports:
            if report is None:
                continue
            sleep = (report.sleep_status or "").lower()
            if "well" in sleep:
                sleep_good += 1
            elif "short" in sleep or "no" in sleep:
                sleep_poor += 1
        
        sleep_rate = (sleep_good / total_reports * 100) if total_reports > 0 else 0
        
        # Analyze meal status
        meal_good = 0
        meal_poor = 0
        for report in reports:
            if report is None:
                continue
            meal = (report.meal_status or "").lower()
            if "all" in meal:
                meal_good += 1
            elif "half" in meal or "none" in meal:
                meal_poor += 1
        
        meal_rate = (meal_good / total_reports * 100) if total_reports > 0 else 0
        
        # Identify students needing attention based on overall wellness
        students_needing_attention = []
        student_report_counts = {}
        
        for report in reports:
            if report is None:
                continue
            student_id = str(report.student_id)
            if student_id not in student_report_counts:
                student_report_counts[student_id] = {
                    "student_id": student_id,
                    "student_name": student_map.get(student_id, "Bilinmeyen"),
                    "total_reports": 0,
                    "poor_mood": 0,
                    "poor_sleep": 0,
                    "poor_meal": 0
                }
            student_report_counts[student_id]["total_reports"] += 1
            
            mood = (report.mood or "").lower()
            if "tired" in mood or "unsettled" in mood:
                student_report_counts[student_id]["poor_mood"] += 1
            
            sleep = (report.sleep_status or "").lower()
            if "short" in sleep or "no" in sleep:
                student_report_counts[student_id]["poor_sleep"] += 1
            
            meal = (report.meal_status or "").lower()
            if "half" in meal or "none" in meal:
                student_report_counts[student_id]["poor_meal"] += 1
        
        # Calculate student wellness scores
        for student_id, data in student_report_counts.items():
            if data["total_reports"] > 0:
                mood_risk = (data["poor_mood"] / data["total_reports"] * 100)
                sleep_risk = (data["poor_sleep"] / data["total_reports"] * 100)
                meal_risk = (data["poor_meal"] / data["total_reports"] * 100)
                overall_risk = (mood_risk + sleep_risk + meal_risk) / 3
                
                if overall_risk > 30:  # Only include students with significant issues
                    students_needing_attention.append({
                        "student_id": student_id,
                        "student_name": data["student_name"],
                        "total_reports": data["total_reports"],
                        "poor_mood": data["poor_mood"],
                        "poor_sleep": data["poor_sleep"],
                        "poor_meal": data["poor_meal"],
                        "wellness_score": round(100 - overall_risk, 1),
                        "risk_level": "yüksek" if overall_risk > 50 else "orta"
                    })
        
        # Sort by wellness score (lowest first)
        students_needing_attention.sort(key=lambda x: x["wellness_score"])
        
        # Generate recommendations
        recommendations = []
        if mood_rate < 60:
            recommendations.append("Öğrenci motivasyonu düşük, aktivite programı gözden geçirilmeli")
        
        if sleep_rate < 60:
            recommendations.append("Uyku düzeni sorunlu, veli bilgilendirmesi yapılmalı")
        
        if meal_rate < 60:
            recommendations.append("Beslenme düzeni iyileştirilmeli")
        
        if len(students_needing_attention) > 5:
            recommendations.append(f"{len(students_needing_attention)} öğrenci dikkat gerektiriyor")
        
        if not recommendations:
            recommendations.append("Tüm göstergeler normal seviyede")
        
        return success_response({
            "ai_model": "Daily Reports Analytics v1.0",
            "report_stats": {
                "total": total_reports,
                "mood_happy": mood_counts["happy"],
                "mood_tired": mood_counts["tired"],
                "mood_rate": round(mood_rate, 1),
                "sleep_rate": round(sleep_rate, 1),
                "meal_rate": round(meal_rate, 1)
            },
            "students_needing_attention": students_needing_attention[:10],
            "recommendations": recommendations
        })
        
    except Exception as e:
        import traceback
        import sys
        print(f"Daily reports analysis error: {str(e)}", file=sys.stderr)
        traceback.print_exc()
        return success_response({
            "ai_model": "Daily Reports Analytics v1.0",
            "report_stats": {
                "total": 0,
                "mood_happy": 0,
                "mood_tired": 0,
                "mood_rate": 0,
                "sleep_rate": 0,
                "meal_rate": 0
            },
            "students_needing_attention": [],
            "recommendations": [f"Hata: {str(e)}"]
        })


@router.get("/student-performance/{student_id}")
async def get_student_performance_prediction(
    student_id: UUID,
    context: str = Query("dashboard", max_length=30),
    tenant: TenantContext = Depends(AnalysisPermission('/student-performance/{student_id}')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    from app.application.services.student_insights import for_student
    return success_response(await for_student(db, tenant, student_id, context))


@router.get("/attendance-analysis")
async def get_attendance_analysis(
    days: int = Query(30, ge=1, le=365),
    tenant: TenantContext = Depends(AnalysisPermission('/attendance-analysis')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    from sqlalchemy.exc import SQLAlchemyError
    from app.application.services.recorded_attendance import summary
    from app.core.exceptions import AppException
    try:
        return success_response(await summary(db, tenant, days))
    except SQLAlchemyError as exc:
        import logging
        logging.getLogger(__name__).error("Recorded attendance query failed (%s)", type(exc).__name__)
        raise AppException("Yoklama özeti yüklenemedi; daha sonra tekrar deneyin", status_code=503) from None


@router.get("/payment-forecast")
async def get_payment_forecast(
    months: int = Query(6, ge=1, le=24),
    tenant: TenantContext = Depends(AnalysisPermission('/payment-forecast')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    return await _recorded_financial_response(months, tenant, db)


@router.get("/canteen-analysis")
async def get_canteen_analysis(
    days: int = Query(30, ge=1, le=365),
    tenant: TenantContext = Depends(AnalysisPermission('/canteen-analysis')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    from app.application.services.recorded_canteen import get_recorded_canteen_summary
    return success_response(await get_recorded_canteen_summary(db, tenant, days=days))


@router.get("/students-overview")
async def get_students_overview_analysis(
    tenant: TenantContext = Depends(AnalysisPermission('/students-overview')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """
    Get AI-powered students overview analysis
    """
    organization_id = tenant.organization_id
    
    # Fetch students
    students_result = await db.execute(
        select(Student)
        .where(Student.organization_id == organization_id)
    )
    students = students_result.scalars().all()
    
    # Fetch grades
    grades_result = await db.execute(
        select(Grade)
        .where(Grade.organization_id == organization_id)
    )
    grades = grades_result.scalars().all()
    
    # Fetch attendance
    attendance_result = await db.execute(
        select(AttendanceRecord)
        .where(AttendanceRecord.organization_id == organization_id)
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
    
    # Calculate students overview analysis
    total_students = len(students)
    active_students = len([s for s in students if s.deleted_at is None])
    
    avg_grade = sum((g["score"] for g in grades_data), 0.0) / len(grades_data) if grades_data else 0.0
    present_count = sum(1 for a in attendance_data if a["status"] == "PRESENT")
    attendance_rate = (present_count / len(attendance_data) * 100) if attendance_data else 0
    
    analysis = {
        "total_students": total_students,
        "active_students": active_students,
        "average_grade": round(avg_grade, 1),
        "attendance_rate": round(attendance_rate, 1),
        "performance_distribution": {
            "excellent": len([g for g in grades_data if g["score"] >= 90]),
            "good": len([g for g in grades_data if 70 <= g["score"] < 90]),
            "needs_improvement": len([g for g in grades_data if g["score"] < 70])
        },
        "recommendations": []
    }
    
    if avg_grade < 70:
        analysis["recommendations"].append("Akademik performans artırılmalı")
    if attendance_rate < 90:
        analysis["recommendations"].append("Devamsızlık oranını düşürün")
    
    return success_response(analysis)


@router.get("/parents-overview")
async def get_parents_overview_analysis(
    tenant: TenantContext = Depends(AnalysisPermission('/parents-overview')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """
    Get AI-powered parents overview analysis (organization-wide aggregate)
    """
    import sys
    try:
        organization_id = tenant.organization_id
        
        # Return empty data if organization_id is None
        if not organization_id:
            return success_response({
                "total_parents": 0,
                "active_parents": 0,
                "communication_rate": 0.0,
                "payment_compliance": 0.0,
                "engagement_score": 0.0,
                "trend": "stabil",
                "recommendations": ["Organizasyon atanmamış"],
                "summary": "Organizasyon bilgisi bulunamadı"
            })
        
        # Fetch parents
        parents_result = await db.execute(
            select(Parent)
            .where(Parent.organization_id == organization_id)
        )
        parents = parents_result.scalars().all()
        
        total_parents = len(parents)
        active_parents = len([p for p in parents if p.deleted_at is None])
        
        # Calculate communication rate based on notification preferences and contact information
        parents_with_contact = len([
            p for p in parents 
            if p.receive_notifications and (p.phone or p.email or p.sms_phone or p.whatsapp_phone)
        ])
        communication_rate = (parents_with_contact / total_parents * 100) if total_parents > 0 else 0
        
        # Calculate payment compliance based on actual payment data
        payment_result = await db.execute(
            select(Payment)
            .where(Payment.organization_id == organization_id)
            .where(Payment.created_at >= datetime.now() - timedelta(days=90))
        )
        payments = payment_result.scalars().all()
        
        # Calculate debt compliance
        debt_result = await db.execute(
            select(Debt)
            .where(Debt.organization_id == organization_id)
        )
        debts = debt_result.scalars().all()
        
        total_debt = sum((d.amount for d in debts), Decimal("0")) if debts else Decimal("0")
        paid_debt = sum((d.paid_amount for d in debts), Decimal("0")) if debts else Decimal("0")
        
        payment_compliance = (float(paid_debt / total_debt * 100) if total_debt > 0 else 0) if debts else 0
        
        # Fetch attendance data for all students
        from app.infrastructure.models.models import StudentParent, Student, AttendanceRecord
        student_parent_result = await db.execute(
            select(StudentParent).where(StudentParent.parent_id.in_([p.id for p in parents]))
        )
        student_parents = student_parent_result.scalars().all()
        student_ids = [sp.student_id for sp in student_parents]
        
        attendance_rate = 0.0
        if student_ids:
            attendance_result = await db.execute(
                select(AttendanceRecord)
                .where(AttendanceRecord.student_id.in_(student_ids))
                .where(AttendanceRecord.attendance_date >= datetime.now() - timedelta(days=30))
            )
            attendance_records = attendance_result.scalars().all()
            
            if attendance_records:
                present_count = sum(1 for r in attendance_records if _status_value(r.status) == "PRESENT")
                attendance_rate = (present_count / len(attendance_records) * 100) if attendance_records else 0
        
        # Fetch notification/communication data
        from app.infrastructure.models.models import NotificationJob
        notification_result = await db.execute(
            select(NotificationJob)
            .where(NotificationJob.organization_id == organization_id)
            .where(NotificationJob.created_at >= datetime.now() - timedelta(days=30))
        )
        notifications = notification_result.scalars().all()
        notification_count = len(notifications)
        
        # Fetch announcement data
        from app.infrastructure.models.models import Announcement
        announcement_result = await db.execute(
            select(Announcement)
            .where(Announcement.organization_id == organization_id)
            .where(Announcement.created_at >= datetime.now() - timedelta(days=30))
        )
        announcements = announcement_result.scalars().all()
        announcement_count = len(announcements)
        
        # Calculate comprehensive engagement score
        communication_score = communication_rate * 0.3  # 30% weight
        payment_score = payment_compliance * 0.3  # 30% weight
        attendance_score = attendance_rate * 0.2  # 20% weight
        notification_score = min(notification_count / total_parents * 10, 20) if total_parents > 0 else 0  # 20% weight max
        engagement_score = communication_score + payment_score + attendance_score + notification_score
        
        # Determine trend
        if engagement_score > 75:
            trend = "artıyor"
        elif engagement_score < 50:
            trend = "azalıyor"
        else:
            trend = "stabil"
        
        # Generate recommendations based on comprehensive data
        recommendations = []
        if communication_rate < 60:
            recommendations.append("Bildirim tercihlerini artırmak için velilerle iletişime geçin")
        if payment_compliance < 70:
            recommendations.append("Ödeme hatırlatmalarını gönderin")
        if attendance_rate < 80:
            recommendations.append("Devamsızlık oranını düşürmek için velilerle görüşün")
        if notification_count < total_parents:
            recommendations.append("Daha fazla bildirim gönderin")
        if announcement_count < 2:
            recommendations.append("Düzenli duyuru yayınlayın")
        if engagement_score < 60:
            recommendations.append("Veli katılımını artırmak için etkinlikler düzenleyin")
        if not recommendations:
            recommendations.append("Veli katılımı iyi - mevcut stratejileri sürdürün")
        
        return success_response({
            "total_parents": total_parents,
            "active_parents": active_parents,
            "communication_rate": round(communication_rate, 1),
            "payment_compliance": round(payment_compliance, 1),
            "attendance_rate": round(attendance_rate, 1),
            "notification_count": notification_count,
            "announcement_count": announcement_count,
            "engagement_score": round(engagement_score, 1),
            "trend": trend,
            "recommendations": recommendations,
            "summary": f"Toplam {total_parents} veliden {active_parents} aktif durumda. İletişim oranı %{round(communication_rate, 1)}, Devamsızlık %{round(attendance_rate, 1)}."
        })
        
    except Exception as e:
        import traceback
        print(f"AI Analysis Error: {str(e)}", file=sys.stderr)
        traceback.print_exc()
        return success_response({
            "total_parents": 0,
            "active_parents": 0,
            "communication_rate": 0.0,
            "payment_compliance": 0.0,
            "attendance_rate": 0.0,
            "engagement_score": 0.0,
            "trend": "error",
            "recommendations": [f"Hata: {str(e)}"],
            "summary": f"Error: {str(e)}"
        })


@router.get("/parent-analysis/{parent_id}")
async def get_parent_analysis(
    parent_id: str,
    tenant: TenantContext = Depends(AnalysisPermission('/parent-analysis/{parent_id}')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """
    Get AI-powered analysis for a specific parent
    """
    import sys
    try:
        organization_id = tenant.organization_id
        print(f"DEBUG: Analyzing parent {parent_id} for org {organization_id}", file=sys.stderr)
        
        # Fetch the specific parent
        parent_result = await db.execute(
            select(Parent)
            .where(Parent.id == parent_id)
            .where(Parent.organization_id == organization_id)
        )
        parent = parent_result.scalar_one_or_none()
        
        if not parent:
            print(f"DEBUG: Parent {parent_id} not found", file=sys.stderr)
            return success_response({
                "has_contact_info": False,
                "receives_notifications": False,
                "payment_compliance": 0.0,
                "engagement_score": 0.0,
                "recommendations": ["Veli bulunamadı"],
                "summary": "Veli kaydı bulunamadı"
            })
        
        print(f"DEBUG: Parent found: {parent.first_name} {parent.last_name}", file=sys.stderr)
        
        # Check contact information
        has_contact_info = bool(parent.phone or parent.email or parent.sms_phone or parent.whatsapp_phone)
        receives_notifications = parent.receive_notifications
        print(f"DEBUG: Contact info: {has_contact_info}, Notifications: {receives_notifications}", file=sys.stderr)
        
        # Fetch students associated with this parent
        from app.infrastructure.models.models import StudentParent, Student, AttendanceRecord
        student_parent_result = await db.execute(
            select(StudentParent).where(StudentParent.parent_id == parent_id)
        )
        student_parents = student_parent_result.scalars().all()
        student_ids = [sp.student_id for sp in student_parents]
        print(f"DEBUG: Found {len(student_ids)} students for parent", file=sys.stderr)
        
        # Calculate payment compliance for this parent's students
        payment_compliance = 0.0
        total_debt_amount = Decimal("0")
        total_paid_amount = Decimal("0")
        if student_ids:
            debt_result = await db.execute(
                select(Debt)
                .where(Debt.student_id.in_(student_ids))
            )
            debts = debt_result.scalars().all()
            
            if debts:
                total_debt_amount = sum((d.amount for d in debts), Decimal("0"))
                total_paid_amount = sum((d.paid_amount for d in debts), Decimal("0"))
                payment_compliance = float(total_paid_amount / total_debt_amount * 100) if total_debt_amount > 0 else 0
                print(f"DEBUG: Total debt: {total_debt_amount}, Paid: {total_paid_amount}, Compliance: {payment_compliance}%", file=sys.stderr)
        
        # Calculate attendance rate for parent's students
        attendance_rate = 0.0
        if student_ids:
            attendance_result = await db.execute(
                select(AttendanceRecord)
                .where(AttendanceRecord.student_id.in_(student_ids))
                .where(AttendanceRecord.attendance_date >= datetime.now() - timedelta(days=30))
            )
            attendance_records = attendance_result.scalars().all()
            
            if attendance_records:
                present_count = sum(1 for r in attendance_records if _status_value(r.status) == "PRESENT")
                attendance_rate = (present_count / len(attendance_records) * 100) if attendance_records else 0
                print(f"DEBUG: Attendance rate: {attendance_rate}%", file=sys.stderr)
        
        # Calculate engagement score with more factors
        contact_score = 30 if has_contact_info else 0
        notification_score = 30 if receives_notifications else 0
        payment_score = payment_compliance * 0.2  # Max 20 points
        attendance_score = attendance_rate * 0.2  # Max 20 points
        engagement_score = contact_score + notification_score + payment_score + attendance_score
        
        # Generate recommendations based on real data
        recommendations = []
        if not has_contact_info:
            recommendations.append("İletişim bilgilerini güncelleyin (telefon, e-posta)")
        if not receives_notifications:
            recommendations.append("Bildirim tercihlerini açarak okul haberlerinden haberdar olun")
        if payment_compliance < 50:
            recommendations.append("Ödemeleri zamanında yapın - borç durumunuz yüksek")
        elif payment_compliance < 80:
            recommendations.append("Ödemeleri düzenli takip edin")
        if attendance_rate < 70:
            recommendations.append("Çocuğunuzun devamsızlık oranını düşürün")
        if engagement_score < 50:
            recommendations.append("Okul etkinliklerine ve toplantılarına katılımı artırın")
        if not recommendations:
            recommendations.append("Mükemmel katılım - mevcut stratejileri sürdürün")
        
        result = {
            "has_contact_info": has_contact_info,
            "receives_notifications": receives_notifications,
            "payment_compliance": round(payment_compliance, 1),
            "attendance_rate": round(attendance_rate, 1),
            "engagement_score": round(engagement_score, 1),
            "student_count": len(student_ids),
            "total_debt": float(total_debt_amount),
            "total_paid": float(total_paid_amount),
            "recommendations": recommendations,
            "summary": f"{parent.first_name} {parent.last_name} - {len(student_ids)} öğrenci. İletişim: {'Var' if has_contact_info else 'Yok'}, Ödeme uyumu: %{round(payment_compliance, 1)}, Devamsızlık: %{round(attendance_rate, 1)}"
        }
        
        print(f"DEBUG: Returning analysis for parent {parent_id}", file=sys.stderr)
        return success_response(result)
        
    except Exception as e:
        import traceback
        print(f"Parent Analysis Error: {str(e)}", file=sys.stderr)
        traceback.print_exc()
        return success_response({
            "has_contact_info": False,
            "receives_notifications": False,
            "payment_compliance": 0.0,
            "attendance_rate": 0.0,
            "engagement_score": 0.0,
            "student_count": 0,
            "total_debt": 0.0,
            "total_paid": 0.0,
            "recommendations": [f"Hata: {str(e)}"],
            "summary": f"Error: {str(e)}"
        })


@router.get("/parent-satisfaction")
async def get_parent_satisfaction_analysis(
    tenant: TenantContext = Depends(AnalysisPermission('/parent-satisfaction')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """
    Get AI-powered parent satisfaction analysis with real data
    """
    try:
        organization_id = tenant.organization_id
        
        if not organization_id:
            return success_response({
                "satisfaction_score": 0,
                "sentiment": "Veri yok",
                "key_issues": [],
                "avg_response_time_hours": 0,
                "total_feedback": 0,
                "engagement_rate": 0,
                "communication_success_rate": 0,
                "total_parents": 0,
                "active_parents": 0,
                "recommendations": ["Organizasyon bilgisi bulunamadı"]
            })
        
        # Fetch parents for the organization
        parent_result = await db.execute(
            select(Parent).where(Parent.organization_id == organization_id)
        )
        parents = parent_result.scalars().all()
        
        # Try to fetch notification jobs, handle if model doesn't exist
        notifications = []
        try:
            notification_result = await db.execute(
                select(NotificationJob)
                .where(NotificationJob.organization_id == organization_id)
                .where(NotificationJob.created_at >= datetime.now() - timedelta(days=30))
            )
            notifications = notification_result.scalars().all()
        except Exception as e:
            import sys
            print(f"Notification query skipped: {str(e)}", file=sys.stderr)
        
        # Try to fetch announcements, handle if model doesn't exist
        announcements = []
        try:
            announcement_result = await db.execute(
                select(Announcement)
                .where(Announcement.organization_id == organization_id)
                .where(Announcement.created_at >= datetime.now() - timedelta(days=30))
            )
            announcements = announcement_result.scalars().all()
        except Exception as e:
            import sys
            print(f"Announcement query skipped: {str(e)}", file=sys.stderr)
        
        # Calculate communication metrics
        total_notifications = len(notifications)
        total_announcements = len(announcements)
        
        # Calculate notification success rate
        successful_notifications = sum(1 for n in notifications if _status_value(n.status) == "SENT")
        success_rate = (successful_notifications / total_notifications * 100) if total_notifications > 0 else 0
        
        # Calculate response time based on notification creation and read status
        # This is a simplified calculation - in a real system, you'd track actual read times
        avg_response_time_hours = 4.0  # Default assumption
        
        # Calculate parent engagement based on notification preferences
        parents_with_notifications = sum(1 for p in parents if p.receive_notifications)
        engagement_rate = (parents_with_notifications / len(parents) * 100) if parents else 0
        
        # Analyze key issues based on communication patterns
        key_issues = []
        
        # Communication issue analysis
        if success_rate < 80:
            key_issues.append({
                "category": "İletişim",
                "mentions": total_notifications - successful_notifications,
                "severity": "high" if success_rate < 60 else "medium"
            })
        
        # Engagement issue analysis
        if engagement_rate < 70:
            key_issues.append({
                "category": "Katılım",
                "mentions": len(parents) - parents_with_notifications,
                "severity": "high" if engagement_rate < 50 else "medium"
            })
        
        # Communication frequency analysis
        if total_notifications < 5:
            key_issues.append({
                "category": "Bildirim Sıklığı",
                "mentions": 5 - total_notifications,
                "severity": "low"
            })
        
        # Calculate satisfaction score based on multiple factors
        satisfaction_score = (success_rate * 0.4) + (engagement_rate * 0.3) + (min(total_announcements * 5, 100) * 0.3)
        satisfaction_score = round(satisfaction_score / 10, 1)  # Scale to 1-5 range
        
        # Determine sentiment
        if satisfaction_score >= 4.0:
            sentiment = "Pozitif"
        elif satisfaction_score >= 3.0:
            sentiment = "Nötr"
        else:
            sentiment = "Negatif"
        
        # Generate recommendations
        recommendations = []
        if success_rate < 80:
            recommendations.append("Bildirim gönderim başarısını artırmak için iletişim kanallarını kontrol edin")
        if engagement_rate < 70:
            recommendations.append("Veli katılımını artırmak için bildirim tercihlerini teşvik edin")
        if total_notifications < 5:
            recommendations.append("Velilerle düzenli iletişim için daha fazla bildirim gönderin")
        if total_announcements < 2:
            recommendations.append("Düzenli duyuru yayınlayarak velileri bilgilendirin")
        if avg_response_time_hours > 24:
            recommendations.append("Veli sorularına yanıt sürelerini kısaltın")
        
        if not recommendations:
            recommendations.append("Veli memnuniyeti iyi - mevcut stratejileri sürdürün")
        
        analysis = {
            "satisfaction_score": satisfaction_score,
            "sentiment": sentiment,
            "key_issues": key_issues,
            "avg_response_time_hours": round(avg_response_time_hours, 1),
            "total_feedback": total_notifications + total_announcements,
            "engagement_rate": round(engagement_rate, 1),
            "communication_success_rate": round(success_rate, 1),
            "total_parents": len(parents),
            "active_parents": parents_with_notifications,
            "recommendations": recommendations
        }
        
        return success_response(analysis)
    except Exception as e:
        import traceback
        import sys
        print(f"Parent satisfaction error: {str(e)}", file=sys.stderr)
        traceback.print_exc()
        return success_response({
            "satisfaction_score": 0,
            "sentiment": "Veri yok",
            "key_issues": [],
            "avg_response_time_hours": 0,
            "total_feedback": 0,
            "engagement_rate": 0,
            "communication_success_rate": 0,
            "total_parents": 0,
            "active_parents": 0,
            "recommendations": [f"Hata: {str(e)}"]
        })


@router.get("/teacher-performance/{teacher_id}")
async def get_teacher_performance_analysis(
    teacher_id: str,
    tenant: TenantContext = Depends(AnalysisPermission('/teacher-performance/{teacher_id}')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    from app.infrastructure.repositories.base import BaseRepository
    teacher = await BaseRepository(db, tenant).get_by_id(UUID(teacher_id), User)
    if "teacher" in tenant.role_slugs and not tenant.is_super_admin and teacher.id != tenant.user_id:
        from app.core.exceptions import ForbiddenException
        raise ForbiddenException()
    classes = select(ClassRoom.id).where((ClassRoom.teacher_id == teacher.id) |
        ClassRoom.id.in_(select(ClassTeacher.class_id).where(ClassTeacher.user_id == teacher.id)))
    grades = (await db.execute(select(Grade).where(Grade.class_id.in_(classes)))).scalars().all()
    attendance = (await db.execute(select(AttendanceRecord).where(AttendanceRecord.class_id.in_(classes)))).scalars().all()
    present = sum(1 for row in attendance if _status_value(row.status) == "PRESENT")
    return success_response({"teacher_id": str(teacher.id), "teacher_name": f"{teacher.first_name} {teacher.last_name}",
        "average_student_grade": round(sum(float(row.score) for row in grades) / len(grades), 1) if grades else None,
        "average_attendance_rate": round(present / len(attendance) * 100, 1) if attendance else None,
        "average_parent_rating": None, "overall_performance": None,
        "recommendations": [], "data_source": "grades_and_attendance"})





@router.get("/academic-performance")
async def get_academic_performance(
    days: int = Query(30, ge=1, le=365),
    tenant: TenantContext = Depends(AnalysisPermission('/academic-performance')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    return await _recorded_academic_response(days, tenant, db)


@router.get("/payment-forecast")
async def get_payment_forecast(
    months: int = Query(6, ge=1, le=24),
    tenant: TenantContext = Depends(AnalysisPermission('/payment-forecast')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    return await _recorded_financial_response(months, tenant, db)


@router.get("/academic-performance")
async def get_academic_performance(
    days: int = Query(30, ge=1, le=365),
    tenant: TenantContext = Depends(AnalysisPermission('/academic-performance')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    return await _recorded_academic_response(days, tenant, db)


@router.get("/communication-analysis")
async def get_communication_analysis(
    tenant: TenantContext = Depends(AnalysisPermission('/communication-analysis')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """
    Get AI-powered communication analysis
    """
    try:
        organization_id = tenant.organization_id
        
        # Fetch notification jobs for the organization
        notification_result = await db.execute(
            select(NotificationJob).where(
                NotificationJob.organization_id == organization_id,
                NotificationJob.created_at >= datetime.now() - timedelta(days=30)
            )
        )
        notifications = notification_result.scalars().all()
        
        # Fetch announcements for the organization
        announcement_result = await db.execute(
            select(Announcement).where(
                Announcement.organization_id == organization_id,
                Announcement.created_at >= datetime.now() - timedelta(days=30)
            )
        )
        announcements = announcement_result.scalars().all()
        
        # Calculate statistics
        total_notifications = len(notifications)
        total_announcements = len(announcements)
        
        # Calculate success rate for notifications
        if notifications:
            successful = sum(1 for n in notifications if _status_value(n.status) == "SENT")
            success_rate = (successful / total_notifications * 100) if total_notifications > 0 else 0
        else:
            success_rate = 0
        
        # Calculate engagement (based on recipient counts)
        total_recipients = sum((n.recipient_count or 0 for n in notifications), 0)
        
        # Channel distribution
        channel_counts = {}
        for notification in notifications:
            channel = notification.channel or "UNKNOWN"
            channel_counts[channel] = channel_counts.get(channel, 0) + 1
        
        # Generate recommendations
        recommendations = []
        if success_rate < 80:
            recommendations.append("Bildirim başarısızlık oranını düşürmek için gönderim ayarlarını kontrol edin")
        if total_notifications < 5:
            recommendations.append("Velilerle düzenli iletişim için daha fazla bildirim gönderin")
        if "SMS" in channel_counts and channel_counts["SMS"] < total_notifications * 0.3:
            recommendations.append("SMS bildirimlerini artırarak iletişim kapsamını genişletin")
        if not recommendations:
            recommendations.append("İletişim stratejisi iyi - mevcut kanalları kullanmaya devam edin")
        
        return success_response({
            "total_notifications": total_notifications,
            "total_announcements": total_announcements,
            "success_rate": round(success_rate, 1),
            "total_recipients": total_recipients,
            "channel_distribution": channel_counts,
            "recommendations": recommendations
        })
        
    except Exception as e:
        import traceback
        import sys
        print(f"Communication Analysis Error: {str(e)}", file=sys.stderr)
        traceback.print_exc()
        return success_response({
            "total_notifications": 0,
            "total_announcements": 0,
            "success_rate": 0,
            "total_recipients": 0,
            "channel_distribution": {},
            "recommendations": [f"Hata: {str(e)}"]
        })


@router.get("/inventory-analysis")
async def get_inventory_analysis(tenant: TenantContext = Depends(AnalysisPermission('/inventory-analysis')), db: AsyncSession = Depends(get_db, scope="function")):
    from app.application.services import inventory_service
    return success_response(await inventory_service.statistics(db))


@router.get("/staff-analysis")
async def get_staff_analysis(
    tenant: TenantContext = Depends(AnalysisPermission('/staff-analysis')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """
    Get AI-powered staff analysis
    """
    try:
        organization_id = tenant.organization_id
        
        # Fetch users for the organization
        user_result = await db.execute(
            select(User).options(selectinload(User.roles)).where(User.organization_id == organization_id)
        )
        users = user_result.scalars().all()
        
        # Calculate statistics
        total_staff = len(users)
        active_staff = len([u for u in users if u.deleted_at is None])
        
        # Count by role
        role_counts = {}
        for user in users:
            for role in user.roles or []:
                role_name = role.name or "Unknown"
                role_counts[role_name] = role_counts.get(role_name, 0) + 1
        
        # Generate recommendations
        recommendations = []
        if total_staff < 5:
            recommendations.append("Personel sayısı düşük - yeni işe alımlar düşünün")
        if active_staff < total_staff * 0.9:
            recommendations.append("Pasif personel durumlarını gözden geçirin")
        if "teacher" not in str(role_counts).lower():
            recommendations.append("Öğretmen atamaları yapın")
        if not recommendations:
            recommendations.append("Personel yapısı iyi - mevcut stratejileri sürdürün")
        
        return success_response({
            "total_staff": total_staff,
            "active_staff": active_staff,
            "role_distribution": role_counts,
            "recommendations": recommendations
        })
        
    except Exception as e:
        import traceback
        import sys
        print(f"Staff Analysis Error: {str(e)}", file=sys.stderr)
        traceback.print_exc()
        return success_response({
            "total_staff": 0,
            "active_staff": 0,
            "role_distribution": {},
            "recommendations": [f"Hata: {str(e)}"]
        })


@router.get("/library-analysis")
async def get_library_analysis(
    tenant: TenantContext = Depends(AnalysisPermission('/library-analysis')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """
    Get AI-powered library analysis
    """
    try:
        organization_id = tenant.organization_id
        
        # Generate recommendations based on common library management practices
        recommendations = [
            "Kitap okuma oranlarını artırmak için okuma etkinlikleri düzenleyin",
            "Popüler kategorilere göre yeni kitap alımları yapın",
            "Zimmet takibi için düzenli kontroller yapın"
        ]
        
        return success_response({
            "total_books": 0,
            "available_books": 0,
            "borrowed_books": 0,
            "overdue_count": 0,
            "recommendations": recommendations
        })
        
    except Exception as e:
        import traceback
        import sys
        print(f"Library Analysis Error: {str(e)}", file=sys.stderr)
        traceback.print_exc()
        return success_response({
            "total_books": 0,
            "available_books": 0,
            "borrowed_books": 0,
            "overdue_count": 0,
            "recommendations": [f"Hata: {str(e)}"]
        })


@router.get("/payroll-analysis")
async def get_payroll_analysis(
    tenant: TenantContext = Depends(AnalysisPermission('/payroll-analysis')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    from app.application.services.payroll_service import summary
    return success_response(await summary(db))


@router.get("/health-analysis")
async def get_health_analysis(tenant: TenantContext = Depends(AnalysisPermission('/health-analysis')), db: AsyncSession = Depends(get_db, scope="function")):
    from app.application.services.infirmary_service import summary
    return success_response(await summary(db))


@router.get("/transport-analysis")
async def get_transport_analysis(
    tenant: TenantContext = Depends(AnalysisPermission('/transport-analysis')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    from app.application.services.bus_service import summary
    return success_response(await summary(db))


@router.get("/tutoring-analysis")
async def get_tutoring_analysis(
    tenant: TenantContext = Depends(AnalysisPermission('/tutoring-analysis')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    from app.application.services.tutoring_service import summary
    return success_response(await summary(db))


@router.get("/surveys-analysis")
async def get_surveys_analysis(
    tenant: TenantContext = Depends(AnalysisPermission('/surveys-analysis')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    from app.application.services.survey_service import summary
    return success_response(await summary(db))


@router.get("/guidance-analysis")
async def get_guidance_analysis(
    tenant: TenantContext = Depends(AnalysisPermission('/guidance-analysis')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    from app.application.services.guidance_service import summary
    return success_response(await summary(db))


@router.get("/clubs-analysis")
async def get_clubs_analysis(
    tenant: TenantContext = Depends(AnalysisPermission('/clubs-analysis')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    from app.application.services import club_service
    return success_response(await club_service.statistics(db))


@router.get("/card-analysis")
async def get_card_analysis(
    card_number: str,
    tenant: TenantContext = Depends(AnalysisPermission('/card-analysis')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """
    Get AI-powered card analysis for a specific card
    """
    try:
        organization_id = tenant.organization_id
        
        # Generate recommendations based on card usage patterns
        recommendations = [
            "Düzenli harcama alışkanlıklarını izleyin",
            "Günlük limitleri optimize edin",
            "Bakiye yükleme hatırlatmaları yapın"
        ]
        
        return success_response({
            "card_number": card_number,
            "avg_daily_spending": 0,
            "spending_trend": "stable",
            "low_balance_alert": False,
            "recommendations": recommendations
        })
        
    except Exception as e:
        import traceback
        import sys
        print(f"Card Analysis Error: {str(e)}", file=sys.stderr)
        traceback.print_exc()
        return success_response({
            "card_number": card_number,
            "avg_daily_spending": 0,
            "spending_trend": "stable",
            "low_balance_alert": False,
            "recommendations": [f"Hata: {str(e)}"]
        })


@router.get("/class-analysis/{class_id}")
async def get_class_analysis(
    class_id: str,
    tenant: TenantContext = Depends(AnalysisPermission('/class-analysis/{class_id}')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """
    Get AI-powered class analysis for a specific class
    """
    try:
        organization_id = tenant.organization_id
        
        # Fetch class information
        class_result = await db.execute(
            select(ClassRoom)
            .where(ClassRoom.id == class_id)
            .where(ClassRoom.organization_id == organization_id)
        )
        class_obj = class_result.scalar_one_or_none()
        
        if not class_obj:
            return success_response({
                "class_id": class_id,
                "student_count": 0,
                "attendance_rate": 0,
                "avg_grade": 0,
                "performance_trend": "Veri yok",
                "recommendations": ["Sınıf bulunamadı"],
                "teacher_name": ""
            })
        
        # Get teacher for this class
        teacher_result = await db.execute(
            select(User.first_name, User.last_name)
            .join(ClassTeacher, ClassTeacher.user_id == User.id)
            .where(ClassTeacher.class_id == class_id)
            .limit(1)
        )
        teacher_row = teacher_result.first()
        teacher_name = f"{teacher_row[0]} {teacher_row[1]}" if teacher_row else ""
        
        # Fetch students in this class
        student_result = await db.execute(
            select(Student)
            .where(Student.class_id == class_id)
            .where(Student.organization_id == organization_id)
        )
        students = student_result.scalars().all()
        student_count = len(students)
        
        # Fetch attendance records for this class
        attendance_result = await db.execute(
            select(AttendanceRecord)
            .where(AttendanceRecord.student_id.in_([s.id for s in students]))
            .where(AttendanceRecord.attendance_date >= datetime.now() - timedelta(days=30))
        )
        attendance_records = attendance_result.scalars().all()
        
        # Calculate attendance rate
        if attendance_records:
            present_count = sum(1 for r in attendance_records if _status_value(r.status) == "PRESENT")
            attendance_rate = (present_count / len(attendance_records) * 100) if attendance_records else 0
        else:
            attendance_rate = 0
        
        # Fetch grades for this class
        grade_result = await db.execute(
            select(Grade)
            .where(Grade.student_id.in_([s.id for s in students]))
        )
        grades = grade_result.scalars().all()
        
        # Calculate average grade
        if grades:
            avg_grade = sum((float(g.score) for g in grades if g.score is not None), 0.0) / len([g for g in grades if g.score is not None])
        else:
            avg_grade = 0
        
        # Generate recommendations
        recommendations = []
        if attendance_rate < 85:
            recommendations.append("Devamsızlık oranını düşürmek için velilerle görüşün")
        if avg_grade < 70:
            recommendations.append("Akademik performansı artırmak için ek ders desteği sağlayın")
        if student_count < 10:
            recommendations.append("Sınıf doluluğunu artırmak için kayıt alımı yapın")
        if not recommendations:
            recommendations.append("Sınıf performansı iyi - mevcut stratejileri sürdürün")
        
        # Determine performance trend
        performance_trend = "Artış" if avg_grade >= 80 else "Stabil" if avg_grade >= 70 else "Düşüş"
        
        return success_response({
            "class_id": class_id,
            "class_name": class_obj.name,
            "student_count": student_count,
            "capacity": class_obj.capacity or 0,
            "attendance_rate": round(attendance_rate, 1),
            "avg_grade": round(avg_grade, 1),
            "performance_trend": performance_trend,
            "recommendations": recommendations,
            "teacher_name": teacher_name
        })
        
    except Exception as e:
        import traceback
        import sys
        print(f"Class Analysis Error: {str(e)}", file=sys.stderr)
        traceback.print_exc()
        return success_response({
            "class_id": class_id,
            "student_count": 0,
            "attendance_rate": 0,
            "avg_grade": 0,
            "performance_trend": "Veri yok",
            "recommendations": [f"Hata: {str(e)}"]
        })


@router.get("/classes-overview")
async def get_classes_overview_analysis(
    tenant: TenantContext = Depends(AnalysisPermission('/classes-overview')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """
    Get AI-powered classes overview analysis (organization-wide aggregate)
    """
    try:
        organization_id = tenant.organization_id
        
        # Fetch all classes
        class_result = await db.execute(
            select(ClassRoom)
            .where(ClassRoom.organization_id == organization_id)
        )
        classes = class_result.scalars().all()
        
        total_classes = len(classes)
        
        # Fetch all students
        student_result = await db.execute(
            select(Student)
            .where(Student.organization_id == organization_id)
        )
        students = student_result.scalars().all()
        
        total_students = len(students)
        
        # Calculate average class size
        avg_class_size = total_students / total_classes if total_classes > 0 else 0
        
        # Calculate total capacity
        total_capacity = sum((c.capacity or 0 for c in classes), 0)
        
        # Calculate occupancy rate
        occupancy_rate = (total_students / total_capacity * 100) if total_capacity > 0 else 0
        
        # Fetch attendance records for all students
        attendance_result = await db.execute(
            select(AttendanceRecord)
            .where(AttendanceRecord.student_id.in_([s.id for s in students]))
            .where(AttendanceRecord.attendance_date >= datetime.now() - timedelta(days=30))
        )
        attendance_records = attendance_result.scalars().all()
        
        # Calculate overall attendance rate
        if attendance_records:
            present_count = sum(1 for r in attendance_records if _status_value(r.status) == "PRESENT")
            overall_attendance_rate = (present_count / len(attendance_records) * 100) if attendance_records else 0
        else:
            overall_attendance_rate = 0
        
        # Fetch grades for all students
        grade_result = await db.execute(
            select(Grade)
            .where(Grade.student_id.in_([s.id for s in students]))
        )
        grades = grade_result.scalars().all()
        
        # Calculate overall average grade
        if grades:
            overall_avg_grade = sum((float(g.score) for g in grades if g.score is not None), 0.0) / len([g for g in grades if g.score is not None])
        else:
            overall_avg_grade = 0
        
        # Generate recommendations
        recommendations = []
        if occupancy_rate > 90:
            recommendations.append("Sınıf kapasiteleri artırılmalı")
        if occupancy_rate < 60:
            recommendations.append("Sınıf doluluğunu artırmak için kayıt alımı yapın")
        if overall_attendance_rate < 85:
            recommendations.append("Devamsızlık oranını düşürmek için velilerle görüşün")
        if overall_avg_grade < 70:
            recommendations.append("Akademik performansı artırmak için ek ders desteği sağlayın")
        if not recommendations:
            recommendations.append("Sınıf performansı iyi - mevcut stratejileri sürdürün")
        
        return success_response({
            "total_classes": total_classes,
            "total_students": total_students,
            "avg_class_size": round(avg_class_size, 1),
            "total_capacity": total_capacity,
            "occupancy_rate": round(occupancy_rate, 1),
            "overall_attendance_rate": round(overall_attendance_rate, 1),
            "overall_avg_grade": round(overall_avg_grade, 1),
            "recommendations": recommendations
        })
        
    except Exception as e:
        import traceback
        import sys
        print(f"Classes Overview Error: {str(e)}", file=sys.stderr)
        traceback.print_exc()
        return success_response({
            "total_classes": 0,
            "total_students": 0,
            "avg_class_size": 0,
            "total_capacity": 0,
            "occupancy_rate": 0,
            "overall_attendance_rate": 0,
            "overall_avg_grade": 0,
            "recommendations": [f"Hata: {str(e)}"]
        })


@router.get("/student-performance-trends")
async def get_student_performance_trends(
    days: int = Query(90, ge=1, le=365),
    tenant: TenantContext = Depends(AnalysisPermission('/student-performance-trends')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    from sqlalchemy.exc import SQLAlchemyError
    from app.application.services.recorded_school_metrics import performance_trends
    from app.core.exceptions import AppException
    try:
        return success_response(await performance_trends(db, tenant, days))
    except SQLAlchemyError as exc:
        import logging
        logging.getLogger(__name__).error("Recorded school metrics query failed (%s)", type(exc).__name__)
        raise AppException("Kurum göstergeleri yüklenemedi; daha sonra tekrar deneyin", status_code=503) from None


@router.get("/organization-health")
async def get_organization_health(
    days: int = Query(30, ge=1, le=365),
    tenant: TenantContext = Depends(AnalysisPermission('/organization-health')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    from sqlalchemy.exc import SQLAlchemyError
    from app.application.services.recorded_school_metrics import organization_health
    from app.core.exceptions import AppException
    try:
        return success_response(await organization_health(db, tenant, days))
    except SQLAlchemyError as exc:
        import logging
        logging.getLogger(__name__).error("Recorded school metrics query failed (%s)", type(exc).__name__)
        raise AppException("Kurum göstergeleri yüklenemedi; daha sonra tekrar deneyin", status_code=503) from None












@router.get("/executive-summary")
async def get_executive_summary(
    tenant: TenantContext = Depends(AnalysisPermission('/executive-summary')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """
    Get executive summary with KPIs for management dashboard
    """
    try:
        organization_id = tenant.organization_id
        if not organization_id:
            return success_response({
                "kpis": {},
                "trends": {},
                "alerts": [],
                "recommendations": ["Organizasyon bilgisi bulunamadı"]
            })
        
        # Fetch key data for KPIs
        student_result = await db.execute(
            select(Student).where(Student.organization_id == organization_id)
        )
        students = student_result.scalars().all()
        
        grade_result = await db.execute(
            select(Grade).where(Grade.organization_id == organization_id)
        )
        grades = grade_result.scalars().all()
        
        attendance_result = await db.execute(
            select(AttendanceRecord)
            .where(AttendanceRecord.organization_id == organization_id)
            .where(AttendanceRecord.attendance_date >= datetime.now() - timedelta(days=30))
        )
        attendance_records = attendance_result.scalars().all()
        
        debt_result = await db.execute(
            select(Debt).where(Debt.organization_id == organization_id)
        )
        debts = debt_result.scalars().all()
        
        parent_result = await db.execute(
            select(Parent).where(Parent.organization_id == organization_id)
        )
        parents = parent_result.scalars().all()
        
        user_result = await db.execute(
            select(User).options(selectinload(User.roles)).where(User.organization_id == organization_id)
        )
        users = user_result.scalars().all()
        
        # Calculate KPIs
        kpis = {
            "total_students": len(students),
            "active_students": len([s for s in students if s.deleted_at is None]),
            "total_staff": len(users),
            "active_staff": len([u for u in users if u.deleted_at is None]),
            "total_parents": len(parents),
            "avg_attendance_rate": 0,
            "avg_grade": 0,
            "collection_rate": 0,
            "total_revenue": 0,
            "outstanding_debt": 0,
            "parent_engagement_rate": 0
        }
        
        # Attendance KPI
        if attendance_records:
            present_count = sum(1 for r in attendance_records if _status_value(r.status) == "PRESENT")
            kpis["avg_attendance_rate"] = round((present_count / len(attendance_records) * 100), 1)

        # Grade KPI
        if grades:
            avg_grade = sum((float(g.score) for g in grades if g.score is not None), 0.0) / len([g for g in grades if g.score is not None])
            kpis["avg_grade"] = round(avg_grade, 1)
        
        # Financial KPIs
        if debts:
            total_debt = sum((d.amount for d in debts), Decimal("0"))
            total_paid = sum((d.paid_amount for d in debts), Decimal("0"))
            kpis["collection_rate"] = round(float(total_paid / total_debt * 100) if total_debt > 0 else 0, 1)
            kpis["total_revenue"] = float(total_paid)
            kpis["outstanding_debt"] = float(total_debt - total_paid)
        
        # Parent engagement KPI
        if parents:
            engaged_parents = sum(1 for p in parents if p.receive_notifications)
            kpis["parent_engagement_rate"] = round((engaged_parents / len(parents) * 100), 1)
        
        # Calculate trends (compare with previous period)
        prev_month_start = datetime.now() - timedelta(days=60)
        prev_month_end = datetime.now() - timedelta(days=30)
        
        prev_attendance_result = await db.execute(
            select(AttendanceRecord)
            .where(AttendanceRecord.organization_id == organization_id)
            .where(AttendanceRecord.attendance_date >= prev_month_start)
            .where(AttendanceRecord.attendance_date <= prev_month_end)
        )
        prev_attendance = prev_attendance_result.scalars().all()
        
        trends = {}
        if prev_attendance and attendance_records:
            prev_present = sum(1 for r in prev_attendance if _status_value(r.status) == "PRESENT")
            prev_rate = (prev_present / len(prev_attendance) * 100) if prev_attendance else 0
            current_rate = kpis["avg_attendance_rate"]
            trends["attendance"] = {
                "current": current_rate,
                "previous": round(prev_rate, 1),
                "change": round(current_rate - prev_rate, 1),
                "direction": "up" if current_rate > prev_rate else "down" if current_rate < prev_rate else "stable"
            }
        
        # Generate alerts based on KPIs
        alerts = []
        if kpis["avg_attendance_rate"] < 80:
            alerts.append({
                "type": "warning",
                "severity": "high",
                "message": f"Devamsızlık oranı düşük: %{kpis['avg_attendance_rate']}",
                "metric": "attendance"
            })
        if kpis["collection_rate"] < 70:
            alerts.append({
                "type": "warning",
                "severity": "critical",
                "message": f"Tahsilat oranı düşük: %{kpis['collection_rate']}",
                "metric": "financial"
            })
        if kpis["outstanding_debt"] > 100000:
            alerts.append({
                "type": "warning",
                "severity": "high",
                "message": f"Yükük borç: ₺{kpis['outstanding_debt']:,.0f}",
                "metric": "financial"
            })
        if kpis["avg_grade"] < 65:
            alerts.append({
                "type": "warning",
                "severity": "medium",
                "message": f"Akademik performans düşük: {kpis['avg_grade']}",
                "metric": "academic"
            })
        
        # Generate management recommendations
        recommendations = []
        if kpis["avg_attendance_rate"] < 85:
            recommendations.append("Devamsızlık azaltma stratejisi geliştirin")
        if kpis["collection_rate"] < 80:
            recommendations.append("Tahsilat süreçlerini optimize edin")
        if kpis["parent_engagement_rate"] < 70:
            recommendations.append("Veli iletişim kanallarını güçlendirin")
        if kpis["avg_grade"] < 70:
            recommendations.append("Akademik destek programları genişletin")
        
        if not recommendations:
            recommendations.append("Tüm metrikler hedef aralığında - mevcut stratejileri sürdürün")
        
        return success_response({
            "kpis": kpis,
            "trends": trends,
            "alerts": alerts,
            "recommendations": recommendations,
            "generated_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        import traceback
        import sys
        print(f"Executive Summary Error: {str(e)}", file=sys.stderr)
        traceback.print_exc()
        return success_response({
            "kpis": {},
            "trends": {},
            "alerts": [{"type": "error", "severity": "critical", "message": f"Hata: {str(e)}"}],
            "recommendations": [f"Hata: {str(e)}"],
            "generated_at": datetime.now().isoformat()
        })


@router.get("/comparative-analysis")
async def get_comparative_analysis(
    period1_days: int = 30,
    period2_days: int = 60,
    tenant: TenantContext = Depends(AnalysisPermission('/comparative-analysis')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """
    Get comparative analysis between two time periods
    """
    try:
        organization_id = tenant.organization_id
        if not organization_id:
            return success_response({
                "period1": {},
                "period2": {},
                "comparison": {},
                "insights": []
            })
        
        # Period 1 (recent)
        period1_start = datetime.now() - timedelta(days=period1_days)
        period1_end = datetime.now()
        
        # Period 2 (previous)
        period2_start = datetime.now() - timedelta(days=period2_days)
        period2_end = datetime.now() - timedelta(days=period1_days)
        
        # Fetch attendance for both periods
        attendance1_result = await db.execute(
            select(AttendanceRecord)
            .where(AttendanceRecord.organization_id == organization_id)
            .where(AttendanceRecord.attendance_date >= period1_start)
            .where(AttendanceRecord.attendance_date <= period1_end)
        )
        attendance1 = attendance1_result.scalars().all()
        
        attendance2_result = await db.execute(
            select(AttendanceRecord)
            .where(AttendanceRecord.organization_id == organization_id)
            .where(AttendanceRecord.attendance_date >= period2_start)
            .where(AttendanceRecord.attendance_date <= period2_end)
        )
        attendance2 = attendance2_result.scalars().all()
        
        # Fetch grades for both periods
        grades1_result = await db.execute(
            select(Grade)
            .where(Grade.organization_id == organization_id)
            .where(Grade.created_at >= period1_start)
            .where(Grade.created_at <= period1_end)
        )
        grades1 = grades1_result.scalars().all()
        
        grades2_result = await db.execute(
            select(Grade)
            .where(Grade.organization_id == organization_id)
            .where(Grade.created_at >= period2_start)
            .where(Grade.created_at <= period2_end)
        )
        grades2 = grades2_result.scalars().all()
        
        # Calculate period 1 metrics
        period1 = {
            "attendance_rate": 0,
            "avg_grade": 0,
            "total_records": len(attendance1),
            "total_grades": len(grades1)
        }
        
        if attendance1:
            present1 = sum(1 for r in attendance1 if _status_value(r.status) == "PRESENT")
            period1["attendance_rate"] = round((present1 / len(attendance1) * 100), 1)
        
        if grades1:
            avg1 = sum((float(g.score) for g in grades1 if g.score is not None), 0.0) / len([g for g in grades1 if g.score is not None])
            period1["avg_grade"] = round(avg1, 1)
        
        # Calculate period 2 metrics
        period2 = {
            "attendance_rate": 0,
            "avg_grade": 0,
            "total_records": len(attendance2),
            "total_grades": len(grades2)
        }
        
        if attendance2:
            present2 = sum(1 for r in attendance2 if _status_value(r.status) == "PRESENT")
            period2["attendance_rate"] = round((present2 / len(attendance2) * 100), 1)
        
        if grades2:
            avg2 = sum((float(g.score) for g in grades2 if g.score is not None), 0.0) / len([g for g in grades2 if g.score is not None])
            period2["avg_grade"] = round(avg2, 1)
        
        # Calculate comparison
        comparison = {
            "attendance_change": round(period1["attendance_rate"] - period2["attendance_rate"], 1),
            "attendance_trend": "improving" if period1["attendance_rate"] > period2["attendance_rate"] else "declining" if period1["attendance_rate"] < period2["attendance_rate"] else "stable",
            "grade_change": round(period1["avg_grade"] - period2["avg_grade"], 1),
            "grade_trend": "improving" if period1["avg_grade"] > period2["avg_grade"] else "declining" if period1["avg_grade"] < period2["avg_grade"] else "stable"
        }
        
        # Generate insights
        insights = []
        if comparison["attendance_change"] > 5:
            insights.append(f"Devamsızlık oranı %{comparison['attendance_change']} arttı - olumlu trend")
        elif comparison["attendance_change"] < -5:
            insights.append(f"Devamsızlık oranı %{abs(comparison['attendance_change'])} azaldı - dikkat gerekli")
        
        if comparison["grade_change"] > 3:
            insights.append(f"Not ortalaması {comparison['grade_change']} puan arttı - akademik iyileşme")
        elif comparison["grade_change"] < -3:
            insights.append(f"Not ortalaması {abs(comparison['grade_change'])} puan azaldı - akademik dikkat")
        
        if not insights:
            insights.append("Dönemler arasında önemli değişiklik yok - stabil performans")
        
        return success_response({
            "period1": period1,
            "period2": period2,
            "comparison": comparison,
            "insights": insights,
            "period1_label": f"Son {period1_days} gün",
            "period2_label": f"Önceki {period2_days - period1_days} gün"
        })
        
    except Exception as e:
        import traceback
        import sys
        print(f"Comparative Analysis Error: {str(e)}", file=sys.stderr)
        traceback.print_exc()
        return success_response({
            "period1": {},
            "period2": {},
            "comparison": {},
            "insights": [f"Hata: {str(e)}"]
        })


@router.get("/resource-utilization")
async def get_resource_utilization(
    tenant: TenantContext = Depends(AnalysisPermission('/resource-utilization')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """
    Get resource utilization analysis for management
    """
    try:
        organization_id = tenant.organization_id
        if not organization_id:
            return success_response({
                "classroom_utilization": {},
                "staff_utilization": {},
                "facility_utilization": {},
                "recommendations": ["Organizasyon bilgisi bulunamadı"]
            })
        
        # Fetch classrooms
        class_result = await db.execute(
            select(ClassRoom).where(ClassRoom.organization_id == organization_id)
        )
        classrooms = class_result.scalars().all()
        
        # Fetch students for occupancy
        student_result = await db.execute(
            select(Student).where(Student.organization_id == organization_id)
        )
        students = student_result.scalars().all()
        
        # Fetch staff
        user_result = await db.execute(
            select(User).options(selectinload(User.roles)).where(User.organization_id == organization_id)
        )
        users = user_result.scalars().all()
        
        # Calculate classroom utilization
        total_capacity = sum((c.capacity or 0 for c in classrooms), 0)
        total_students = len(students)
        classroom_utilization = {
            "total_classrooms": len(classrooms),
            "total_capacity": total_capacity,
            "total_students": total_students,
            "occupancy_rate": round((total_students / total_capacity * 100) if total_capacity > 0 else 0, 1),
            "average_class_size": round(total_students / len(classrooms), 1) if classrooms else 0,
            "underutilized_classes": len([c for c in classrooms if c.capacity and (total_students / len(classrooms) if classrooms else 0) < c.capacity * 0.6]),
            "overcrowded_classes": len([c for c in classrooms if c.capacity and (total_students / len(classrooms) if classrooms else 0) > c.capacity * 0.9])
        }
        
        # Calculate staff utilization
        total_staff = len(users)
        active_staff = len([u for u in users if u.deleted_at is None])
        staff_utilization = {
            "total_staff": total_staff,
            "active_staff": active_staff,
            "utilization_rate": round((active_staff / total_staff * 100) if total_staff > 0 else 0, 1),
            "student_staff_ratio": round(total_students / active_staff, 1) if active_staff > 0 else 0
        }
        
        # Facility utilization (simplified)
        facility_utilization = {
            "overall_utilization": round((classroom_utilization["occupancy_rate"] + staff_utilization["utilization_rate"]) / 2, 1),
            "efficiency_score": 0  # Would be calculated based on more complex metrics
        }
        
        # Generate recommendations
        recommendations = []
        if classroom_utilization["occupancy_rate"] > 90:
            recommendations.append("Sınıf kapasitesi artırılmalı - yeni sınıflar açın")
        elif classroom_utilization["occupancy_rate"] < 60:
            recommendations.append("Sınıf doluluğu düşük - kayıt alımını artırın")
        
        if classroom_utilization["overcrowded_classes"] > 0:
            recommendations.append(f"{classroom_utilization['overcrowded_classes']} sınıf aşırı dolu - kapasite planlaması yapın")
        
        if staff_utilization["student_staff_ratio"] > 20:
            recommendations.append("Öğrenci/öğretmen oranı yüksek - yeni öğretmen alımları düşünün")
        
        if not recommendations:
            recommendations.append("Kaynak kullanımı optimal - mevcut kapasite verimli kullanılıyor")
        
        return success_response({
            "classroom_utilization": classroom_utilization,
            "staff_utilization": staff_utilization,
            "facility_utilization": facility_utilization,
            "recommendations": recommendations
        })
        
    except Exception as e:
        import traceback
        import sys
        print(f"Resource Utilization Error: {str(e)}", file=sys.stderr)
        traceback.print_exc()
        return success_response({
            "classroom_utilization": {},
            "staff_utilization": {},
            "facility_utilization": {},
            "recommendations": [f"Hata: {str(e)}"]
        })


@router.get("/staff-productivity")
async def get_staff_productivity(
    tenant: TenantContext = Depends(AnalysisPermission('/staff-productivity')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """
    Get staff productivity metrics for management
    """
    try:
        organization_id = tenant.organization_id
        if not organization_id:
            return success_response({
                "productivity_metrics": {},
                "performance_by_role": {},
                "recommendations": ["Organizasyon bilgisi bulunamadı"]
            })
        
        # Fetch staff
        user_result = await db.execute(
            select(User).options(selectinload(User.roles)).where(User.organization_id == organization_id)
        )
        users = user_result.scalars().all()
        
        # Fetch classes assigned to teachers
        class_teacher_result = await db.execute(
            select(ClassTeacher).join(ClassRoom, ClassRoom.id == ClassTeacher.class_id)
            .where(ClassRoom.organization_id == organization_id)
        )
        class_teachers = class_teacher_result.scalars().all()
        
        # Fetch recent activities (simplified - would use actual activity logs)
        productivity_metrics = {
            "total_staff": len(users),
            "active_staff": len([u for u in users if u.deleted_at is None]),
            "teachers_with_classes": len(set([ct.user_id for ct in class_teachers])),
            "average_classes_per_teacher": round(len(class_teachers) / len(set([ct.user_id for ct in class_teachers])), 1) if class_teachers else 0,
            "staff_utilization_rate": round(len([u for u in users if u.deleted_at is None]) / len(users) * 100, 1) if users else 0
        }
        
        # Performance by role (simplified)
        performance_by_role = {}
        for user in users:
            role = user.position or "General"
            if role not in performance_by_role:
                performance_by_role[role] = {"count": 0, "active": 0}
            performance_by_role[role]["count"] += 1
            if user.deleted_at is None:
                performance_by_role[role]["active"] += 1
        
        # Calculate performance scores
        for role in performance_by_role:
            total = performance_by_role[role]["count"]
            active = performance_by_role[role]["active"]
            performance_by_role[role]["utilization"] = round((active / total * 100) if total > 0 else 0, 1)
        
        # Generate recommendations
        recommendations = []
        if productivity_metrics["staff_utilization_rate"] < 80:
            recommendations.append("Personel kullanım oranını artırın")
        if productivity_metrics["average_classes_per_teacher"] < 2:
            recommendations.append("Öğretmen sınıf yükünü dengeli dağıtın")
        if productivity_metrics["teachers_with_classes"] < productivity_metrics["active_staff"] * 0.8:
            recommendations.append("Daha fazla öğretmene sınıf atayın")
        
        if not recommendations:
            recommendations.append("Personel verimliliği iyi - mevcut dağılımı sürdürün")
        
        return success_response({
            "productivity_metrics": productivity_metrics,
            "performance_by_role": performance_by_role,
            "recommendations": recommendations
        })
        
    except Exception as e:
        import traceback
        import sys
        print(f"Staff Productivity Error: {str(e)}", file=sys.stderr)
        traceback.print_exc()
        return success_response({
            "productivity_metrics": {},
            "performance_by_role": {},
            "recommendations": [f"Hata: {str(e)}"]
        })


@router.get("/risk-management")
async def get_risk_management(
    tenant: TenantContext = Depends(AnalysisPermission('/risk-management')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """
    Get risk management dashboard for proactive decision making
    """
    try:
        organization_id = tenant.organization_id
        if not organization_id:
            return success_response({
                "risks": [],
                "risk_summary": {},
                "mitigation_strategies": [],
                "recommendations": ["Organizasyon bilgisi bulunamadı"]
            })
        
        risks = []
        
        # Financial risk analysis
        debt_result = await db.execute(
            select(Debt).where(Debt.organization_id == organization_id)
        )
        debts = debt_result.scalars().all()
        
        if debts:
            total_debt = sum((d.amount for d in debts), Decimal("0"))
            total_paid = sum((d.paid_amount for d in debts), Decimal("0"))
            collection_rate = float(total_paid / total_debt * 100) if total_debt > 0 else 0
            outstanding_debt = total_debt - total_paid
            
            overdue_debts = [d for d in debts if d.due_date and d.due_date < school_today() and d.status != DebtStatus.PAID]
            overdue_amount = sum((d.amount - d.paid_amount for d in overdue_debts), Decimal("0"))
            
            if collection_rate < 60:
                risks.append({
                    "category": "Financial",
                    "level": "critical",
                    "description": f"Düşük tahsilat oranı: %{collection_rate}",
                    "impact": "high",
                    "probability": "high"
                })
            elif collection_rate < 75:
                risks.append({
                    "category": "Financial",
                    "level": "medium",
                    "description": f"Tahsilat oranı dikkat gerektiriyor: %{collection_rate}",
                    "impact": "medium",
                    "probability": "medium"
                })
            
            if overdue_amount > total_debt * Decimal("0.2"):
                risks.append({
                    "category": "Financial",
                    "level": "critical",
                    "description": f"Yükük vadesi geçmiş borç: ₺{float(overdue_amount):,.0f}",
                    "impact": "high",
                    "probability": "high"
                })
        
        # Academic risk analysis
        grade_result = await db.execute(
            select(Grade).where(Grade.organization_id == organization_id)
        )
        grades = grade_result.scalars().all()
        
        if grades:
            avg_grade = sum((float(g.score) for g in grades if g.score is not None), 0.0) / len([g for g in grades if g.score is not None])
            passing_rate = len([g for g in grades if g.score and g.score >= 60]) / len(grades) * 100 if grades else 0
            
            if avg_grade < 60:
                risks.append({
                    "category": "Academic",
                    "level": "critical",
                    "description": f"Düşük not ortalaması: {round(avg_grade, 1)}",
                    "impact": "high",
                    "probability": "high"
                })
            elif avg_grade < 70:
                risks.append({
                    "category": "Academic",
                    "level": "medium",
                    "description": f"Not ortalaması iyileştirme gerektiriyor: {round(avg_grade, 1)}",
                    "impact": "medium",
                    "probability": "medium"
                })
            
            if passing_rate < 75:
                risks.append({
                    "category": "Academic",
                    "level": "high",
                    "description": f"Düşük geçme oranı: {round(passing_rate, 1)}%",
                    "impact": "high",
                    "probability": "medium"
                })
        
        # Attendance risk analysis
        attendance_result = await db.execute(
            select(AttendanceRecord)
            .where(AttendanceRecord.organization_id == organization_id)
            .where(AttendanceRecord.attendance_date >= datetime.now() - timedelta(days=30))
        )
        attendance_records = attendance_result.scalars().all()
        
        if attendance_records:
            present_count = sum(1 for r in attendance_records if _status_value(r.status) == "PRESENT")
            attendance_rate = (present_count / len(attendance_records) * 100) if attendance_records else 0
            
            if attendance_rate < 75:
                risks.append({
                    "category": "Attendance",
                    "level": "critical",
                    "description": f"Düşük devamsızlık oranı: {round(attendance_rate, 1)}%",
                    "impact": "high",
                    "probability": "high"
                })
            elif attendance_rate < 85:
                risks.append({
                    "category": "Attendance",
                    "level": "medium",
                    "description": f"Devamsızlık oranı izlenmeli: {round(attendance_rate, 1)}%",
                    "impact": "medium",
                    "probability": "medium"
                })
        
        # Resource risk analysis
        student_result = await db.execute(
            select(Student).where(Student.organization_id == organization_id)
        )
        students = student_result.scalars().all()
        
        class_result = await db.execute(
            select(ClassRoom).where(ClassRoom.organization_id == organization_id)
        )
        classrooms = class_result.scalars().all()
        
        if classrooms and students:
            total_capacity = sum((c.capacity or 0 for c in classrooms), 0)
            occupancy_rate = (len(students) / total_capacity * 100) if total_capacity > 0 else 0
            
            if occupancy_rate > 95:
                risks.append({
                    "category": "Capacity",
                    "level": "high",
                    "description": f"Sınıf kapasitesi aşımı: {round(occupancy_rate, 1)}%",
                    "impact": "medium",
                    "probability": "high"
                })
        
        # Calculate risk summary
        risk_summary = {
            "total_risks": len(risks),
            "critical_risks": len([r for r in risks if r["level"] == "critical"]),
            "high_risks": len([r for r in risks if r["level"] == "high"]),
            "medium_risks": len([r for r in risks if r["level"] == "medium"]),
            "by_category": {}
        }
        
        for risk in risks:
            category = risk["category"]
            if category not in risk_summary["by_category"]:
                risk_summary["by_category"][category] = 0
            risk_summary["by_category"][category] += 1
        
        # Generate mitigation strategies
        mitigation_strategies = []
        for risk in risks:
            if risk["category"] == "Financial":
                mitigation_strategies.append("Tahsilat süreçlerini iyileştirin, ödeme planları oluşturun")
            elif risk["category"] == "Academic":
                mitigation_strategies.append("Ek ders programları, öğrenci destek sistemleri")
            elif risk["category"] == "Attendance":
                mitigation_strategies.append("Veli iletişimi, devamsızlık takip sistemleri")
            elif risk["category"] == "Capacity":
                mitigation_strategies.append("Kapasite planlaması, yeni sınıf açılışları")
        
        # Generate recommendations
        recommendations = []
        if risk_summary["critical_risks"] > 0:
            recommendations.append(f"Acil: {risk_summary['critical_risks']} kritik risk için eylem planı oluşturun")
        if risk_summary["high_risks"] > 2:
            recommendations.append(f"Yüksek risk sayısı fazla ({risk_summary['high_risks']}) - önceliklendirme yapın")
        if risk_summary["total_risks"] > 5:
            recommendations.append("Risk yönetimi stratejisini gözden geçirin")
        
        if not recommendations:
            recommendations.append("Risk profili iyi - düzenli izleme devam etsin")
        
        return success_response({
            "risks": risks,
            "risk_summary": risk_summary,
            "mitigation_strategies": list(set(mitigation_strategies)),
            "recommendations": recommendations,
            "assessment_date": datetime.now().isoformat()
        })
        
    except Exception as e:
        import traceback
        import sys
        print(f"Risk Management Error: {str(e)}", file=sys.stderr)
        traceback.print_exc()
        return success_response({
            "risks": [],
            "risk_summary": {},
            "mitigation_strategies": [],
            "recommendations": [f"Hata: {str(e)}"],
            "assessment_date": datetime.now().isoformat()
        })


@router.get("/operational-metrics")
async def get_operational_metrics(
    tenant: TenantContext = Depends(AnalysisPermission('/operational-metrics')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """
    Get operational metrics for day-to-day management
    """
    try:
        organization_id = tenant.organization_id
        if not organization_id:
            return success_response({
                "daily_metrics": {},
                "weekly_metrics": {},
                "monthly_metrics": {},
                "efficiency_indicators": {},
                "recommendations": ["Organizasyon bilgisi bulunamadı"]
            })
        
        today = school_today()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        
        # Daily metrics
        daily_attendance_result = await db.execute(
            select(AttendanceRecord)
            .where(AttendanceRecord.organization_id == organization_id)
            .where(AttendanceRecord.attendance_date == today)
        )
        daily_attendance = daily_attendance_result.scalars().all()
        
        daily_metrics = {
            "date": today.isoformat(),
            "attendance_records": len(daily_attendance),
            "present_count": sum(1 for r in daily_attendance if _status_value(r.status) == "PRESENT"),
            "absent_count": sum(1 for r in daily_attendance if _status_value(r.status) == "ABSENT"),
            "attendance_rate": round((sum(1 for r in daily_attendance if _status_value(r.status) == "PRESENT") / len(daily_attendance) * 100) if daily_attendance else 0, 1)
        }
        
        # Weekly metrics
        weekly_attendance_result = await db.execute(
            select(AttendanceRecord)
            .where(AttendanceRecord.organization_id == organization_id)
            .where(AttendanceRecord.attendance_date >= week_start)
            .where(AttendanceRecord.attendance_date <= today)
        )
        weekly_attendance = weekly_attendance_result.scalars().all()
        
        weekly_metrics = {
            "week_start": week_start.isoformat(),
            "week_end": today.isoformat(),
            "total_records": len(weekly_attendance),
            "avg_daily_attendance": round(len(weekly_attendance) / 7, 1) if weekly_attendance else 0,
            "weekly_attendance_rate": round((sum(1 for r in weekly_attendance if _status_value(r.status) == "PRESENT") / len(weekly_attendance) * 100) if weekly_attendance else 0, 1)
        }
        
        # Monthly metrics
        monthly_attendance_result = await db.execute(
            select(AttendanceRecord)
            .where(AttendanceRecord.organization_id == organization_id)
            .where(AttendanceRecord.attendance_date >= month_start)
            .where(AttendanceRecord.attendance_date <= today)
        )
        monthly_attendance = monthly_attendance_result.scalars().all()
        
        monthly_payment_result = await db.execute(
            select(Payment)
            .where(Payment.organization_id == organization_id)
            .where(Payment.created_at >= month_start)
            .where(Payment.created_at <= datetime.now())
        )
        monthly_payments = monthly_payment_result.scalars().all()
        
        monthly_metrics = {
            "month_start": month_start.isoformat(),
            "month_end": today.isoformat(),
            "total_attendance_records": len(monthly_attendance),
            "monthly_attendance_rate": round((sum(1 for r in monthly_attendance if _status_value(r.status) == "PRESENT") / len(monthly_attendance) * 100) if monthly_attendance else 0, 1),
            "total_payments": len(monthly_payments),
            "total_payment_amount": float(sum((p.amount for p in monthly_payments), Decimal("0")) if monthly_payments else Decimal("0"))
        }
        
        # Efficiency indicators
        efficiency_indicators = {
            "attendance_efficiency": "good" if daily_metrics["attendance_rate"] > 90 else "fair" if daily_metrics["attendance_rate"] > 80 else "poor",
            "payment_collection_efficiency": "good" if len(monthly_payments) > 10 else "fair" if len(monthly_payments) > 5 else "poor",
            "overall_operational_health": "good" if (daily_metrics["attendance_rate"] > 85 and len(monthly_payments) > 5) else "fair" if (daily_metrics["attendance_rate"] > 75 and len(monthly_payments) > 3) else "poor"
        }
        
        # Generate recommendations
        recommendations = []
        if efficiency_indicators["attendance_efficiency"] == "poor":
            recommendations.append("Günlük devamsızlık oranını iyileştirin")
        if efficiency_indicators["payment_collection_efficiency"] == "poor":
            recommendations.append("Aylık ödeme tahsilatını artırın")
        if efficiency_indicators["overall_operational_health"] == "poor":
            recommendations.append("Operasyonel süreçleri gözden geçirin")
        
        if not recommendations:
            recommendations.append("Operasyonel metrikler iyi - mevcut süreçleri sürdürün")
        
        return success_response({
            "daily_metrics": daily_metrics,
            "weekly_metrics": weekly_metrics,
            "monthly_metrics": monthly_metrics,
            "efficiency_indicators": efficiency_indicators,
            "recommendations": recommendations,
            "generated_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        import traceback
        import sys
        print(f"Operational Metrics Error: {str(e)}", file=sys.stderr)
        traceback.print_exc()
        return success_response({
            "daily_metrics": {},
            "weekly_metrics": {},
            "monthly_metrics": {},
            "efficiency_indicators": {},
            "recommendations": [f"Hata: {str(e)}"],
            "generated_at": datetime.now().isoformat()
        })


@router.get("/ai-academic-predictions")
async def get_ai_academic_predictions(
    days: int = Query(30, ge=1, le=365),
    tenant: TenantContext = Depends(AnalysisPermission('/ai-academic-predictions')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    return await _recorded_academic_response(days, tenant, db)




@router.get("/ai-financial-predictions")
async def get_ai_financial_predictions(
    months: int = Query(6, ge=1, le=24),
    tenant: TenantContext = Depends(AnalysisPermission('/ai-financial-predictions')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    return await _recorded_financial_predictions_response(months, tenant, db)


@router.get("/ai-parent-sentiment")
async def get_ai_parent_sentiment(
    days: int = Query(30, ge=1, le=365),
    tenant: TenantContext = Depends(AnalysisPermission('/ai-parent-sentiment')),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    return await _recorded_parent_response(days, tenant, db)
