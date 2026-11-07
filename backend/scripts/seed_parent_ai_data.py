"""Populate relationship-linked demo children with data used by parent AI views.

Safe to run repeatedly: it adds only missing grade/attendance series.
WARNING: Only run in development with SEED_DEMO_DATA=true
"""

import asyncio
import os
import sys
from datetime import date, time, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

# Permit ``python scripts/seed_parent_ai_data.py`` from the backend directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import AsyncSessionLocal
from app.infrastructure.models.models import (
    AttendanceRecord,
    AttendanceStatus,
    DailyDevelopmentReport,
    Grade,
    GradeType,
    Parent,
    Student,
    StudentParent,
    SubjectType,
    User,
)


async def seed() -> None:
    # Check if running in production
    seed_demo_data = os.getenv("SEED_DEMO_DATA", "false").lower() == "true"
    app_env = os.getenv("APP_ENV", "production").lower()
    
    if not seed_demo_data and app_env == "production":
        print("ERROR: Cannot seed parent AI data in production. Set SEED_DEMO_DATA=true to override.")
        return
    
    async with AsyncSessionLocal() as db:
        child_rows = await db.execute(
            select(Student)
            .join(StudentParent, StudentParent.student_id == Student.id)
            .join(Parent, Parent.id == StudentParent.parent_id)
            .where(Parent.user_id.is_not(None), Student.deleted_at.is_(None))
        )
        children = child_rows.scalars().unique().all()
        recorder = (await db.execute(select(User).where(User.deleted_at.is_(None)).limit(1))).scalar_one_or_none()
        if not children or recorder is None:
            print("No linked parent child or recorder user found; nothing added.")
            return

        grades_added = attendance_added = 0
        for student in children:
            has_grades = (
                await db.execute(select(Grade.id).where(Grade.student_id == student.id).limit(1))
            ).scalar_one_or_none()
            if has_grades is None:
                for index, (subject, score) in enumerate([
                    (SubjectType.MATHEMATICS, 76),
                    (SubjectType.TURKISH, 82),
                    (SubjectType.SCIENCE, 71),
                    (SubjectType.ENGLISH, 88),
                    (SubjectType.SOCIAL_STUDIES, 79),
                ]):
                    db.add(Grade(
                        organization_id=student.organization_id,
                        branch_id=student.branch_id,
                        class_id=student.class_id,
                        student_id=student.id,
                        teacher_id=recorder.id,
                        subject=subject,
                        grade_type=GradeType.EXAM if index < 3 else GradeType.HOMEWORK,
                        score=Decimal(str(score)),
                        max_score=Decimal("100"),
                        exam_date=date.today() - timedelta(days=35 - index * 6),
                        term="2026-2027",
                        notes="Veli AI analizi için örnek değerlendirme verisi",
                        created_by=recorder.id,
                        updated_by=recorder.id,
                    ))
                    grades_added += 1

            for days_ago in range(1, 29):
                attendance_day = date.today() - timedelta(days=days_ago)
                if attendance_day.weekday() >= 5:
                    continue
                exists = (
                    await db.execute(
                        select(AttendanceRecord.id).where(
                            AttendanceRecord.student_id == student.id,
                            AttendanceRecord.attendance_date == attendance_day,
                        )
                    )
                ).scalar_one_or_none()
                if exists is None:
                    status = AttendanceStatus.ABSENT if days_ago in {8, 19} else (
                        AttendanceStatus.LATE if days_ago == 13 else AttendanceStatus.PRESENT
                    )
                    db.add(AttendanceRecord(
                        organization_id=student.organization_id,
                        branch_id=student.branch_id,
                        class_id=student.class_id,
                        student_id=student.id,
                        attendance_date=attendance_day,
                        status=status,
                        check_in_time=None if status == AttendanceStatus.ABSENT else time(8, 35),
                        notes="Veli AI analizi için örnek devam verisi",
                        recorded_by=recorder.id,
                    ))
                    attendance_added += 1

            today_record = (
                await db.execute(
                    select(AttendanceRecord.id).where(
                        AttendanceRecord.student_id == student.id,
                        AttendanceRecord.attendance_date == date.today(),
                    )
                )
            ).scalar_one_or_none()
            if today_record is None:
                db.add(AttendanceRecord(
                    organization_id=student.organization_id,
                    branch_id=student.branch_id,
                    class_id=student.class_id,
                    student_id=student.id,
                    attendance_date=date.today(),
                    status=AttendanceStatus.PRESENT,
                    check_in_time=time(8, 30),
                    notes="Bugünkü örnek yoklama kaydı",
                    recorded_by=recorder.id,
                ))
                attendance_added += 1

            today_report = (
                await db.execute(
                    select(DailyDevelopmentReport.id).where(
                        DailyDevelopmentReport.student_id == student.id,
                        DailyDevelopmentReport.date == date.today(),
                    )
                )
            ).scalar_one_or_none()
            if today_report is None:
                db.add(DailyDevelopmentReport(
                    student_id=student.id,
                    class_id=student.class_id,
                    date=date.today(),
                    meal_status="ALL",
                    sleep_status="SLEPT_WELL",
                    mood="HAPPY",
                    activities=["Matematik etkinliği", "Bahçe oyunu", "Hikâye saati"],
                    teacher_notes="Derse katılımı iyi, gün içindeki etkinliklere istekle katıldı.",
                    recorded_by=recorder.id,
                ))

        await db.commit()
        print(f"Added {grades_added} grades and {attendance_added} attendance records.")


if __name__ == "__main__":
    asyncio.run(seed())
