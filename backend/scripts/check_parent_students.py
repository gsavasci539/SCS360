"""Check parent's linked students"""

import asyncio
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.infrastructure.models.models import User, Parent, StudentParent, Student


async def check_parent_students():
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
        
        # Get parent record
        parent = await db.execute(
            select(Parent).where(Parent.user_id == parent_user.id)
        )
        parent = parent.scalar_one_or_none()
        
        if not parent:
            print("Parent record not found for this user")
            return
        
        print(f"Parent record ID: {parent.id}")
        print(f"Parent name: {parent.first_name} {parent.last_name}")
        
        # Get student-parent links
        student_parents = await db.execute(
            select(StudentParent).where(StudentParent.parent_id == parent.id)
        )
        student_parents = student_parents.scalars().all()
        
        print(f"\nParent has {len(student_parents)} linked student(s):")
        
        if not student_parents:
            print("  No students linked to this parent!")
            
            # Check if there are any students in the database
            all_students = await db.execute(
                select(Student).limit(5)
            )
            all_students = all_students.scalars().all()
            
            print(f"\nTotal students in database: {len(all_students)}")
            for student in all_students:
                print(f"  - {student.first_name} {student.last_name} (ID: {student.id})")
            
            # Link this parent to the first student
            if all_students:
                print(f"\nLinking parent to first student: {all_students[0].first_name} {all_students[0].last_name}")
                db.add(StudentParent(
                    parent_id=parent.id,
                    student_id=all_students[0].id,
                    is_primary=True
                ))
                await db.commit()
                print("Parent linked to student successfully!")
        else:
            for sp in student_parents:
                student = await db.execute(
                    select(Student).where(Student.id == sp.student_id)
                )
                student = student.scalar_one_or_none()
                if student:
                    print(f"  - {student.first_name} {student.last_name} (ID: {student.id}, Primary: {sp.is_primary})")


if __name__ == "__main__":
    asyncio.run(check_parent_students())
