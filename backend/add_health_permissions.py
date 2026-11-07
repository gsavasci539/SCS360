"""
Add health.read and health.write permissions to the database
This script should be run to fix the medicine request visibility issue for superadmin
"""
import asyncio
import uuid
from sqlalchemy import text
from app.core.database import AsyncSessionLocal


async def add_health_permissions():
    """Add health permissions and assign them to appropriate roles"""
    async with AsyncSessionLocal() as db:
        # Check if permissions already exist
        result = await db.execute(
            text("SELECT id FROM permissions WHERE code IN ('health.read', 'health.write', 'parent.medicine_request')")
        )
        existing = result.fetchall()

        if len(existing) < 3:
            # Add health permissions
            health_read_id = uuid.UUID('f0000000-0000-4000-8000-00000000001e')
            health_write_id = uuid.UUID('f0000000-0000-4000-8000-00000000001f')
            parent_medicine_request_id = uuid.UUID('f0000000-0000-4000-8000-000000000020')

            await db.execute(
                text("""
                    INSERT INTO permissions (id, code, name, module)
                    VALUES
                        (:health_read_id, 'health.read', 'Sağlık Görüntüle', 'health'),
                        (:health_write_id, 'health.write', 'Sağlık Yönet', 'health'),
                        (:parent_medicine_request_id, 'parent.medicine_request', 'İlaç Talebi Oluştur', 'parent')
                    ON CONFLICT (id) DO NOTHING
                """),
                {
                    "health_read_id": str(health_read_id),
                    "health_write_id": str(health_write_id),
                    "parent_medicine_request_id": str(parent_medicine_request_id)
                }
            )
            print("Added health permissions to database.")
        else:
            print("Health permissions already exist. Adding role permissions if missing.")

        # Assign to Super Admin (all permissions)
        super_admin_role_id = uuid.UUID('a0000000-0000-4000-8000-000000000001')
        await db.execute(
            text("""
                INSERT INTO role_permissions (role_id, permission_id)
                SELECT :super_admin_role_id, id FROM permissions
                WHERE code IN ('health.read', 'health.write', 'parent.medicine_request')
                ON CONFLICT (role_id, permission_id) DO NOTHING
            """),
            {"super_admin_role_id": str(super_admin_role_id)}
        )

        # Assign to Branch Manager (read + write)
        branch_manager_role_id = uuid.UUID('a0000000-0000-4000-8000-000000000003')
        await db.execute(
            text("""
                INSERT INTO role_permissions (role_id, permission_id)
                SELECT :branch_manager_role_id, id FROM permissions
                WHERE code IN ('health.read', 'health.write')
                ON CONFLICT (role_id, permission_id) DO NOTHING
            """),
            {"branch_manager_role_id": str(branch_manager_role_id)}
        )

        # Assign to Teacher (read only)
        teacher_role_id = uuid.UUID('a0000000-0000-4000-8000-000000000004')
        await db.execute(
            text("""
                INSERT INTO role_permissions (role_id, permission_id)
                SELECT :teacher_role_id, id FROM permissions
                WHERE code = 'health.read'
                ON CONFLICT (role_id, permission_id) DO NOTHING
            """),
            {"teacher_role_id": str(teacher_role_id)}
        )

        # Assign to Parent (read only + medicine request)
        parent_role_id = uuid.UUID('a0000000-0000-4000-8000-000000000008')
        await db.execute(
            text("""
                INSERT INTO role_permissions (role_id, permission_id)
                SELECT :parent_role_id, id FROM permissions
                WHERE code IN ('health.read', 'parent.medicine_request')
                ON CONFLICT (role_id, permission_id) DO NOTHING
            """),
            {"parent_role_id": str(parent_role_id)}
        )

        # Assign to Manager (read + write)
        manager_role_id = uuid.UUID('a0000000-0000-4000-8000-000000000009')
        await db.execute(
            text("""
                INSERT INTO role_permissions (role_id, permission_id)
                SELECT :manager_role_id, id FROM permissions
                WHERE code IN ('health.read', 'health.write')
                ON CONFLICT (role_id, permission_id) DO NOTHING
            """),
            {"manager_role_id": str(manager_role_id)}
        )

        # Assign to Administrator (read + write)
        admin_role_id = uuid.UUID('a0000000-0000-4000-8000-00000000000a')
        await db.execute(
            text("""
                INSERT INTO role_permissions (role_id, permission_id)
                SELECT :admin_role_id, id FROM permissions
                WHERE code IN ('health.read', 'health.write')
                ON CONFLICT (role_id, permission_id) DO NOTHING
            """),
            {"admin_role_id": str(admin_role_id)}
        )

        # Assign to Owner (read + write)
        owner_role_id = uuid.UUID('a0000000-0000-4000-8000-00000000000b')
        await db.execute(
            text("""
                INSERT INTO role_permissions (role_id, permission_id)
                SELECT :owner_role_id, id FROM permissions
                WHERE code IN ('health.read', 'health.write')
                ON CONFLICT (role_id, permission_id) DO NOTHING
            """),
            {"owner_role_id": str(owner_role_id)}
        )

        await db.commit()
        print("Health permissions added successfully!")
        print("Assigned to: Super Admin, Branch Manager, Teacher (read), Parent (read + medicine request), Manager, Administrator, Owner")


if __name__ == "__main__":
    asyncio.run(add_health_permissions())
