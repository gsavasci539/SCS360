"""Assign a student to the parent account."""

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
ADMIN_ID = uuid.UUID("e0000000-0000-4000-8000-000000000001")


async def assign_student_to_parent():
    async with AsyncSessionLocal() as db:
        # Find the parent user
        parent_user = await db.execute(
            select(User).where(User.email == "veli@demo.com")
        )
        parent_user = parent_user.scalar_one_or_none()
        
        if not parent_user:
            print("Parent user not found!")
            return
        
        print(f"Found parent user: {parent_user.email} (ID: {parent_user.id})")
        
        # Find a student to assign
        student = await db.execute(
            select(Student).where(Student.organization_id == DEMO_ORG_ID).limit(1)
        )
        student = student.scalar_one_or_none()
        
        if not student:
            print("No student found!")
            return
        
        print(f"Found student: {student.first_name} {student.last_name} (ID: {student.id})")
        
        # Check if parent record exists for this user
        parent = await db.execute(
            select(Parent).where(Parent.user_id == parent_user.id)
        )
        parent = parent.scalar_one_or_none()
        
        if parent:
            print(f"Parent record already exists: {parent.first_name} {parent.last_name}")
            
            # Check if student is already assigned to this parent
            existing_assignment = await db.execute(
                select(StudentParent).where(
                    StudentParent.parent_id == parent.id,
                    StudentParent.student_id == student.id
                )
            )
            if existing_assignment.scalar_one_or_none():
                print("Student is already assigned to this parent!")
                return
            
            # Assign student to parent
            db.add(StudentParent(
                student_id=student.id,
                parent_id=parent.id,
                is_primary=True
            ))
            print("Assigned student to existing parent record")
        else:
            # Create new parent record for the user
            parent = Parent(
                organization_id=DEMO_ORG_ID,
                user_id=parent_user.id,
                first_name=parent_user.first_name,
                last_name=parent_user.last_name,
                email=parent_user.email,
                receive_notifications=True,
                created_by=ADMIN_ID,
            )
            db.add(parent)
            await db.flush()
            
            # Assign student to parent
            db.add(StudentParent(
                student_id=student.id,
                parent_id=parent.id,
                is_primary=True
            ))
            print("Created new parent record and assigned student")
        
        await db.commit()
        print("Successfully assigned student to parent account!")


if __name__ == "__main__":
    asyncio.run(assign_student_to_parent())
