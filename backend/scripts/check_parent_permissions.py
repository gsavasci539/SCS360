"""Check parent user permissions"""

import asyncio
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.infrastructure.models.models import User, Role, UserRole, RolePermission, Permission


async def check_parent_permissions():
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
                
                # Get permissions for this role
                role_permissions = await db.execute(
                    select(RolePermission).where(RolePermission.role_id == role.id)
                )
                role_permissions = role_permissions.scalars().all()
                
                print(f"    Permissions ({len(role_permissions)}):")
                for rp in role_permissions:
                    perm = await db.execute(
                        select(Permission).where(Permission.id == rp.permission_id)
                    )
                    perm = perm.scalar_one_or_none()
                    if perm:
                        print(f"      - {perm.code} ({perm.name})")


if __name__ == "__main__":
    asyncio.run(check_parent_permissions())
