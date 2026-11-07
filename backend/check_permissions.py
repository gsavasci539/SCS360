"""
Check if superadmin has health permissions
"""
import asyncio
import uuid
from sqlalchemy import text
from app.core.database import AsyncSessionLocal


async def check_permissions():
    """Check superadmin permissions"""
    async with AsyncSessionLocal() as db:
        # Check health permissions exist
        result = await db.execute(
            text("SELECT id, code, name FROM permissions WHERE code IN ('health.read', 'health.write')")
        )
        health_perms = result.fetchall()
        print("Health permissions in DB:")
        for perm in health_perms:
            print(f"  {perm[1]}: {perm[2]} (ID: {perm[0]})")
        
        # Check superadmin role permissions
        super_admin_role_id = uuid.UUID('a0000000-0000-4000-8000-000000000001')
        result = await db.execute(
            text("""
                SELECT p.code, p.name 
                FROM role_permissions rp
                JOIN permissions p ON rp.permission_id = p.id
                WHERE rp.role_id = :role_id
                AND p.code IN ('health.read', 'health.write')
            """),
            {"role_id": str(super_admin_role_id)}
        )
        superadmin_perms = result.fetchall()
        print("\nSuperadmin health permissions:")
        for perm in superadmin_perms:
            print(f"  {perm[0]}: {perm[1]}")
        
        # Check superadmin user
        result = await db.execute(
            text("SELECT id, email, is_super_admin FROM users WHERE is_super_admin = TRUE")
        )
        superadmin_users = result.fetchall()
        print("\nSuperadmin users:")
        for user in superadmin_users:
            print(f"  {user[1]} (ID: {user[0]}, is_super_admin: {user[2]})")
        
        # Check medication schedules
        result = await db.execute(
            text("SELECT COUNT(*) FROM medication_schedules")
        )
        count = result.scalar()
        print(f"\nMedication schedules count: {count}")


if __name__ == "__main__":
    asyncio.run(check_permissions())
