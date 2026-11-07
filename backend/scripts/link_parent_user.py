"""Link parent user to parent record"""

import asyncio
import uuid
from sqlalchemy import select, text

from app.core.database import AsyncSessionLocal
from app.infrastructure.models.models import Parent, User, StudentParent


async def link_parent_user():
    async with AsyncSessionLocal() as db:
        # Get parent user
        parent_user = await db.execute(
            select(User).where(User.email == "veli@demo.com")
        )
        parent_user = parent_user.scalar_one_or_none()
        
        if not parent_user:
            print("Parent user not found")
            return
        
        # Get first parent record
        parent = await db.execute(
            select(Parent).limit(1)
        )
        parent = parent.scalar_one_or_none()
        
        if not parent:
            print("Parent record not found")
            return
        
        # Check if already linked
        if parent.user_id == parent_user.id:
            print(f"Parent user {parent_user.email} already linked to parent record {parent.id}")
            return
        
        # Use direct SQL to update parent record
        await db.execute(
            text("UPDATE parents SET user_id = :user_id, first_name = :first_name, last_name = :last_name, email = :email WHERE id = :parent_id"),
            {
                "user_id": str(parent_user.id),
                "first_name": parent_user.first_name,
                "last_name": parent_user.last_name,
                "email": parent_user.email,
                "parent_id": str(parent.id)
            }
        )
        
        await db.commit()
        
        print(f"Linked parent user {parent_user.email} to parent record {parent.id}")


if __name__ == "__main__":
    asyncio.run(link_parent_user())
