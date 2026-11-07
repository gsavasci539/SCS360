"""Create missing parent permissions."""

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


async def create_parent_permissions():
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
        
        # Permissions to create
        permissions_to_create = [
            {
                "code": "parent.view_daily_report",
                "name": "Günlük Raporları Görüntüle",
                "module": "parent",
                "description": "Veli çocuklarının günlük gelişim raporlarını görüntüleyebilir"
            },
            {
                "code": "parent.send_excuse",
                "name": "Mazeret Talebi Gönder",
                "module": "parent",
                "description": "Veli çocukları için mazeret talebi gönderebilir"
            },
            {
                "code": "parent.medicine_request",
                "name": "İlaç Talebi Gönder",
                "module": "parent",
                "description": "Veli çocukları için ilaç talebi gönderebilir"
            },
        ]
        
        for perm_data in permissions_to_create:
            # Check if permission already exists
            existing = await db.execute(
                select(Permission).where(Permission.code == perm_data["code"])
            )
            existing_perm = existing.scalar_one_or_none()
            
            if existing_perm:
                print(f"Permission already exists: {perm_data['code']}")
                permission = existing_perm
            else:
                print(f"Creating permission: {perm_data['code']}")
                permission = Permission(**perm_data)
                db.add(permission)
                await db.flush()
            
            # Check if role already has this permission
            existing_role_perm = await db.execute(
                select(RolePermission).where(
                    RolePermission.role_id == parent_role.id,
                    RolePermission.permission_id == permission.id
                )
            )
            
            if not existing_role_perm.scalar_one_or_none():
                print(f"Adding permission to role: {perm_data['code']}")
                db.add(RolePermission(
                    role_id=parent_role.id,
                    permission_id=permission.id
                ))
            else:
                print(f"Role already has permission: {perm_data['code']}")
        
        await db.commit()
        print("Permissions created and assigned successfully!")


if __name__ == "__main__":
    asyncio.run(create_parent_permissions())
