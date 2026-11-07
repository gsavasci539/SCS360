"""Fix parent user link and add student"""

import asyncio
from sqlalchemy import select, text

from app.core.database import AsyncSessionLocal
from app.infrastructure.models.models import User, Parent, StudentParent, Student


async def fix_parent_link():
    async with AsyncSessionLocal() as db:
        # Get parent user
        parent_user = await db.execute(
            select(User).where(User.email == "veli@demo.com")
        )
        parent_user = parent_user.scalar_one_or_none()
        
        if not parent_user:
            print("Parent user not found")
            return
        
        print(f"Parent user: {parent_user.email}")
        print(f"User ID: {parent_user.id}")
        
        # Check if parent record exists for this user
        parent = await db.execute(
            select(Parent).where(Parent.user_id == parent_user.id)
        )
        parent = parent.scalar_one_or_none()
        
        if parent:
            print(f"Parent record already exists: {parent.id}")
        else:
            # Find any parent record without user_id
            orphan_parent = await db.execute(
                select(Parent).where(Parent.user_id == None).limit(1)
            )
            orphan_parent = orphan_parent.scalar_one_or_none()
            
            if orphan_parent:
                print(f"Found orphan parent record: {orphan_parent.id}")
                # Link it to the user
                await db.execute(
                    text("UPDATE parents SET user_id = :user_id, first_name = :first_name, last_name = :last_name, email = :email WHERE id = :parent_id"),
                    {
                        "user_id": str(parent_user.id),
                        "first_name": parent_user.first_name,
                        "last_name": parent_user.last_name,
                        "email": parent_user.email,
                        "parent_id": str(orphan_parent.id)
                    }
                )
                await db.commit()
                parent = orphan_parent
                print(f"Linked parent record to user")
            else:
                # Create a new parent record
                print("Creating new parent record")
                new_parent = Parent(
                    organization_id=parent_user.organization_id,
                    user_id=parent_user.id,
                    first_name=parent_user.first_name,
                    last_name=parent_user.last_name,
                    email=parent_user.email,
                    receive_notifications=True
                )
                db.add(new_parent)
                await db.flush()
                await db.commit()
                parent = new_parent
                print(f"Created new parent record: {parent.id}")
        
        # Get first student
        student = await db.execute(
            select(Student).limit(1)
        )
        student = student.scalar_one_or_none()
        
        if not student:
            print("No students found in database")
            return
        
        print(f"Found student: {student.first_name} {student.last_name} (ID: {student.id})")
        
        # Check if already linked
        existing_link = await db.execute(
            select(StudentParent).where(
                StudentParent.parent_id == parent.id,
                StudentParent.student_id == student.id
            )
        )
        existing_link = existing_link.scalar_one_or_none()
        
        if existing_link:
            print("Parent already linked to this student")
        else:
            # Link parent to student
            db.add(StudentParent(
                parent_id=parent.id,
                student_id=student.id,
                is_primary=True
            ))
            await db.commit()
            print("Successfully linked parent to student")
        
        print("\n=== Summary ===")
        print(f"Parent: {parent_user.first_name} {parent_user.last_name}")
        print(f"Student: {student.first_name} {student.last_name}")
        print("Link established successfully")


if __name__ == "__main__":
    asyncio.run(fix_parent_link())
