"""
Check and update user permissions for superadmin
"""
import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionLocal


async def check_user_permissions():
    """Check superadmin user permissions"""
    async with AsyncSessionLocal() as db:
        # Get superadmin user
        result = await db.execute(
            text("SELECT id, email, is_super_admin FROM users WHERE email = 'admin@demo.com'")
        )
        user = result.fetchone()
        
        if not user:
            print("Superadmin user not found")
            return
        
        print(f"User: {user[1]} (ID: {user[0]}, is_super_admin: {user[2]})")
        
        # Get user roles
        result = await db.execute(
            text("""
                SELECT r.id, r.name, r.slug 
                FROM user_roles ur
                JOIN roles r ON ur.role_id = r.id
                WHERE ur.user_id = :user_id
            """),
            {"user_id": str(user[0])}
        )
        roles = result.fetchall()
        print(f"\nUser roles:")
        for role in roles:
            print(f"  {role[1]} ({role[2]})")
        
        # Get user permissions through roles
        result = await db.execute(
            text("""
                SELECT DISTINCT p.code, p.name, p.module
                FROM role_permissions rp
                JOIN permissions p ON rp.permission_id = p.id
                JOIN user_roles ur ON rp.role_id = ur.role_id
                WHERE ur.user_id = :user_id
                ORDER BY p.module, p.code
            """),
            {"user_id": str(user[0])}
        )
        permissions = result.fetchall()
        print(f"\nUser permissions ({len(permissions)} total):")
        for perm in permissions:
            print(f"  {perm[0]}: {perm[1]} ({perm[2]})")
        
        # Check if health permissions exist
        health_perms = [p for p in permissions if p[2] == 'health']
        print(f"\nHealth permissions: {len(health_perms)}")
        for perm in health_perms:
            print(f"  {perm[0]}: {perm[1]}")


if __name__ == "__main__":
    asyncio.run(check_user_permissions())
