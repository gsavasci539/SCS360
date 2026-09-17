import asyncio
from app.core.database import AsyncSessionLocal
from sqlalchemy import select, update
from app.infrastructure.models.models import User

async def make_admin_super():
    """Update admin@demo.com to be a super admin"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.email == "admin@demo.com")
        )
        admin_user = result.scalar_one_or_none()
        
        if admin_user:
            admin_user.is_super_admin = True
            await session.commit()
            print(f"✓ User {admin_user.email} is now a super admin")
        else:
            print("✗ Admin user not found")

if __name__ == "__main__":
    asyncio.run(make_admin_super())
