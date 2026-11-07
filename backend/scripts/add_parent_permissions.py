"""Add missing parent permissions to parent role."""

import asyncio
import uuid
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.infrastructure.models.models import (
    Permission,
    Role,
    RolePermission,
)

DEMO_ORG_ID = uuid.UUID("b0000000-0000-4000-8000-000000000001")
ROLE_PARENT = uuid.UUID("a0000000-0000-4000-8000-000000000008")


async def add_parent_permissions():
    async with AsyncSessionLocal() as db:
        # Get parent role
        parent_role = await db.execute(
            select(Role).where(Role.id == ROLE_PARENT)
        )
        parent_role = parent_role.scalar_one_or_none()
        
        if not parent_role:
            print("Parent role not found!")
            return
        
        print(f"Parent role: {parent_role.name} (ID: {parent_role.id})")
        
        # Get all permissions
        all_permissions = await db.execute(select(Permission))
        all_permissions = all_permissions.scalars().all()
        
        # Parent permissions that should be added
        required_permissions = [
            "parent.view_daily_report",
            "parent.send_excuse",
            "parent.medicine_request",
        ]
        
        # Check which permissions exist
        permission_map = {p.code: p for p in all_permissions}
        
        for perm_code in required_permissions:
            if perm_code not in permission_map:
                print(f"Permission {perm_code} does not exist in database, skipping...")
                continue
            
            permission = permission_map[perm_code]
            
            # Check if role already has this permission
            existing = await db.execute(
                select(RolePermission).where(
                    RolePermission.role_id == parent_role.id,
                    RolePermission.permission_id == permission.id
                )
            )
            
            if not existing.scalar_one_or_none():
                print(f"Adding permission: {perm_code}")
                db.add(RolePermission(
                    role_id=parent_role.id,
                    permission_id=permission.id
                ))
            else:
                print(f"Permission already exists: {perm_code}")
        
        await db.commit()
        print("Permissions updated successfully!")


if __name__ == "__main__":
    asyncio.run(add_parent_permissions())
