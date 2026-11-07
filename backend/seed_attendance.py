"""
Seed script to add more attendance data for analytics
WARNING: Only run in development with SEED_DEMO_DATA=true
"""
import asyncio
import os
from datetime import date, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.infrastructure.models.models import (
    Student, AttendanceRecord, AttendanceStatus, Organization, Branch, ClassRoom, User
)


async def seed_attendance():
    # Check if running in production
    seed_demo_data = os.getenv("SEED_DEMO_DATA", "false").lower() == "true"
    app_env = os.getenv("APP_ENV", "production").lower()
    
    if not seed_demo_data and app_env == "production":
        print("ERROR: Cannot seed attendance data in production. Set SEED_DEMO_DATA=true to override.")
        return
    
    async for db in get_db():
        # Get organization
        org_result = await db.execute(select(Organization).limit(1))
        org = org_result.scalar_one_or_none()
        
        if not org:
            print("No organization found")
            return
        
        # Get branch
        branch_result = await db.execute(
            select(Branch).where(Branch.organization_id == org.id).limit(1)
        )
        branch = branch_result.scalar_one_or_none()
        
        if not branch:
            print("No branch found")
            return
        
        # Get class
        class_result = await db.execute(
            select(ClassRoom).where(ClassRoom.branch_id == branch.id).limit(1)
        )
        class_room = class_result.scalar_one_or_none()
        
        if not class_room:
            print("No class found")
            return
        
        # Get students
        students_result = await db.execute(
            select(Student).where(Student.class_id == class_room.id)
        )
        students = students_result.scalars().all()
        
        # Get a user for recorded_by
        user_result = await db.execute(select(User).limit(1))
        user = user_result.scalar_one_or_none()
        
        print(f"Found {len(students)} students")
        
        # Add attendance for the last 30 days
        base_date = date.today()
        attendance_statuses = [
            AttendanceStatus.PRESENT,
            AttendanceStatus.PRESENT,
            AttendanceStatus.PRESENT,
            AttendanceStatus.PRESENT,
            AttendanceStatus.ABSENT,
            AttendanceStatus.LATE,
            AttendanceStatus.EXCUSED
        ]
        
        for student in students:
            print(f"Adding attendance for student {student.first_name} {student.last_name}")
            
            for days_ago in range(30):
                attendance_date = base_date - timedelta(days=days_ago)
                
                # Skip weekends
                if attendance_date.weekday() >= 5:
                    continue
                
                # Generate attendance status with some randomness
                import hashlib
                seed = int(hashlib.md5(f"{student.id}{attendance_date}".encode()).hexdigest()[:8], 16)
                status = attendance_statuses[seed % len(attendance_statuses)]
                
                # Check if attendance already exists
                existing_result = await db.execute(
                    select(AttendanceRecord).where(
                        AttendanceRecord.student_id == student.id,
                        AttendanceRecord.attendance_date == attendance_date
                    )
                )
                existing = existing_result.scalar_one_or_none()
                
                if not existing:
                    attendance = AttendanceRecord(
                        organization_id=org.id,
                        branch_id=branch.id,
                        class_id=class_room.id,
                        student_id=student.id,
                        attendance_date=attendance_date,
                        status=status,
                        recorded_by=user.id if user else None
                    )
                    db.add(attendance)
            
            await db.flush()
        
        await db.commit()
        print("Attendance data seeded successfully")


if __name__ == "__main__":
    asyncio.run(seed_attendance())
