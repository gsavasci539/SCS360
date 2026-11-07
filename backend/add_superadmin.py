import asyncio
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import hash_password
from app.infrastructure.models.models import User

async def add_super_admin():
    async for db in get_db():
        organization_id = 1
        
        # Check if super admin already exists
        existing_result = await db.execute(
            select(User).where(
                User.email == "superadmin@scs360.com",
                User.organization_id == organization_id
            )
        )
        existing_admin = existing_result.scalar_one_or_none()
        
        if existing_admin:
            print("Super Admin zaten mevcut:")
            print(f"  Email: {existing_admin.email}")
            print(f"  İsim: {existing_admin.first_name} {existing_admin.last_name}")
            print(f"  Super Admin: {existing_admin.is_super_admin}")
        else:
            # Create super admin
            super_admin = User(
                organization_id=organization_id,
                email="superadmin@scs360.com",
                password_hash=hash_password("SuperAdmin123!"),
                first_name="Super",
                last_name="Admin",
                phone="5550000000",
                position="Super Administrator",
                department="IT",
                status="ACTIVE",
                is_super_admin=True
            )
            db.add(super_admin)
            await db.commit()
            await db.refresh(super_admin)
            
            print("Super Admin başarıyla oluşturuldu:")
            print(f"  Email: {super_admin.email}")
            print(f"  İsim: {super_admin.first_name} {super_admin.last_name}")
            print(f"  Şifre: SuperAdmin123!")
            print(f"  Super Admin: {super_admin.is_super_admin}")
        
        break

if __name__ == "__main__":
    asyncio.run(add_super_admin())
