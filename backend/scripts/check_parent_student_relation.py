"""Check parent-student relationship in database."""

import asyncio
import uuid
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.infrastructure.models.models import (
    Parent,
    Student,
    StudentParent,
    User,
)

DEMO_ORG_ID = uuid.UUID("b0000000-0000-4000-8000-000000000001")


async def check_relation():
    async with AsyncSessionLocal() as db:
        # Find parent user
        parent_user = await db.execute(
            select(User).where(User.email == "veli@demo.com")
        )
        parent_user = parent_user.scalar_one_or_none()
        
        if not parent_user:
            print("Parent user not found!")
            return
        
        print(f"Parent User: {parent_user.email} (ID: {parent_user.id})")
        print(f"Parent User Name: {parent_user.first_name} {parent_user.last_name}")
        
        # Find parent record linked to this user
        parent = await db.execute(
            select(Parent).where(Parent.user_id == parent_user.id)
        )
        parent = parent.scalar_one_or_none()
        
        if not parent:
            print("No parent record found for this user!")
            return
        
        print(f"\nParent Record: {parent.first_name} {parent.last_name} (ID: {parent.id})")
        print(f"Parent User ID in parent record: {parent.user_id}")
        
        # Find student-parent relationships
        student_parents = await db.execute(
            select(StudentParent).where(StudentParent.parent_id == parent.id)
        )
        student_parents = student_parents.scalars().all()
        
        print(f"\nFound {len(student_parents)} student-parent relationships:")
        
        for sp in student_parents:
            # Get student details
            student = await db.execute(
                select(Student).where(Student.id == sp.student_id)
            )
            student = student.scalar_one_or_none()
            
            if student:
                print(f"  - Student: {student.first_name} {student.last_name} (ID: {student.id})")
                print(f"    Is Primary: {sp.is_primary}")
                print(f"    Student Number: {student.student_number}")
                print(f"    Class ID: {student.class_id}")
                print(f"    Status: {student.status}")
            else:
                print(f"  - Student ID: {sp.student_id} (not found in students table)")


if __name__ == "__main__":
    asyncio.run(check_relation())
