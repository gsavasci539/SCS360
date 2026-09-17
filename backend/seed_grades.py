"""
Seed script to add sample grades for students
"""
import asyncio
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.infrastructure.models.models import (
    Student, Grade, GradeType, SubjectType, Organization, Branch, ClassRoom
)


async def seed_grades():
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
        
        print(f"Found {len(students)} students")
        
        subjects = [
            SubjectType.MATHEMATICS,
            SubjectType.SCIENCE,
            SubjectType.TURKISH,
            SubjectType.SOCIAL_STUDIES,
            SubjectType.ENGLISH
        ]
        
        grade_types = [
            GradeType.EXAM,
            GradeType.QUIZ,
            GradeType.HOMEWORK,
            GradeType.PROJECT,
            GradeType.MIDTERM,
            GradeType.FINAL
        ]
        
        base_date = date.today()
        
        for student in students:
            print(f"Adding grades for student {student.first_name} {student.last_name}")
            
            for subject in subjects:
                for grade_type in grade_types:
                    # Generate different scores based on student and subject
                    import hashlib
                    seed = int(hashlib.md5(f"{student.id}{subject}{grade_type}".encode()).hexdigest()[:8], 16)
                    
                    # Score between 50-95
                    score = 50 + (seed % 46)
                    
                    # Exam date varies by grade type
                    if grade_type == GradeType.FINAL:
                        exam_date = base_date
                    elif grade_type == GradeType.MIDTERM:
                        exam_date = base_date - timedelta(days=60)
                    elif grade_type == GradeType.EXAM:
                        exam_date = base_date - timedelta(days=30 + (seed % 30))
                    else:
                        exam_date = base_date - timedelta(days=(seed % 90))
                    
                    grade = Grade(
                        organization_id=org.id,
                        branch_id=branch.id,
                        class_id=class_room.id,
                        student_id=student.id,
                        subject=subject,
                        grade_type=grade_type,
                        score=Decimal(str(score)),
                        max_score=Decimal("100"),
                        exam_date=exam_date,
                        term="2024-2025"
                    )
                    
                    db.add(grade)
            
            await db.flush()
        
        await db.commit()
        print("Grades seeded successfully")


if __name__ == "__main__":
    asyncio.run(seed_grades())
