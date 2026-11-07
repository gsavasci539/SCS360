"""Test the exact query that backend uses to find parent"""

import asyncio
from sqlalchemy import select
from uuid import UUID

from app.core.database import AsyncSessionLocal
from app.infrastructure.models.models import User, Parent, StudentParent


async def test_parent_query():
    async with AsyncSessionLocal() as db:
        # Get parent user
        parent_user = await db.execute(
            select(User).where(User.email == "veli@demo.com")
        )
        parent_user = parent_user.scalar_one_or_none()
        
        if not parent_user:
            print("Parent user not found")
            return
        
        print(f"Parent user ID: {parent_user.id}")
        print(f"Parent user ID type: {type(parent_user.id)}")
        
        # This is the exact query from students.py
        parent = await db.execute(
            select(Parent).where(Parent.user_id == parent_user.id)
        )
        parent = parent.scalar_one_or_none()
        
        if parent:
            print(f"Parent record found: {parent.id}")
            print(f"Parent user_id: {parent.user_id}")
            
            # Get student IDs
            student_parents = await db.execute(
                select(StudentParent).where(StudentParent.parent_id == parent.id)
            )
            student_ids = [sp.student_id for sp in student_parents.scalars().all()]
            print(f"Student IDs: {student_ids}")
        else:
            print("Parent record NOT found!")
            
            # Check all parent records
            all_parents = await db.execute(select(Parent))
            all_parents = all_parents.scalars().all()
            print(f"\nAll parent records ({len(all_parents)}):")
            for p in all_parents[:5]:
                print(f"  ID: {p.id}, user_id: {p.user_id}")


if __name__ == "__main__":
    asyncio.run(test_parent_query())
