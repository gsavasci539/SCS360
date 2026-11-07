"""Check parent user role"""

import asyncio
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.infrastructure.models.models import User, Role, UserRole


async def check_parent_role():
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
        
        # Get user roles
        user_roles = await db.execute(
            select(UserRole).where(UserRole.user_id == parent_user.id)
        )
        user_roles = user_roles.scalars().all()
        
        print(f"\nUser has {len(user_roles)} role(s):")
        
        for ur in user_roles:
            role = await db.execute(
                select(Role).where(Role.id == ur.role_id)
            )
            role = role.scalar_one_or_none()
            if role:
                print(f"  - {role.name} (slug: {role.slug}, id: {role.id})")


if __name__ == "__main__":
    asyncio.run(check_parent_role())
