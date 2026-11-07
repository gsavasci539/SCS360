"""Fix parent-student relationship by removing invalid entries."""

import asyncio
from sqlalchemy import select, delete

from app.core.database import AsyncSessionLocal
from app.infrastructure.models.models import (
    Parent,
    Student,
    StudentParent,
    User,
)


async def fix_relation():
    async with AsyncSessionLocal() as db:
        # Find parent user
        parent_user = await db.execute(
            select(User).where(User.email == "veli@demo.com")
        )
        parent_user = parent_user.scalar_one_or_none()
        
        if not parent_user:
            print("Parent user not found!")
            return
        
        # Find parent record
        parent = await db.execute(
            select(Parent).where(Parent.user_id == parent_user.id)
        )
        parent = parent.scalar_one_or_none()
        
        if not parent:
            print("No parent record found!")
            return
        
        # Get all student-parent relationships
        student_parents = await db.execute(
            select(StudentParent).where(StudentParent.parent_id == parent.id)
        )
        student_parents = student_parents.scalars().all()
        
        print(f"Found {len(student_parents)} student-parent relationships")
        
        # Check each relationship
        for sp in student_parents:
            student = await db.execute(
                select(Student).where(Student.id == sp.student_id)
            )
            student = student.scalar_one_or_none()
            
            if not student:
                print(f"Removing invalid relationship for student ID: {sp.student_id}")
                await db.execute(
                    delete(StudentParent).where(
                        StudentParent.student_id == sp.student_id,
                        StudentParent.parent_id == sp.parent_id
                    )
                )
            else:
                print(f"Valid relationship: {student.first_name} {student.last_name}")
        
        await db.commit()
        print("Cleaned up invalid relationships")


if __name__ == "__main__":
    asyncio.run(fix_relation())
