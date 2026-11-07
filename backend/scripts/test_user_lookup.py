import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import asyncio
from uuid import UUID
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.infrastructure.models.models import User

async def test():
    user_id_str = "e0000000-0000-4000-8000-000000000001"
    parsed = UUID(user_id_str)
    print(f"Parsed UUID: {parsed}")
    print(f"UUID type: {type(parsed)}")
    
    async with AsyncSessionLocal() as session:
        # Test direct query
        result = await session.execute(
            select(User).where(User.id == parsed, User.deleted_at.is_(None))
        )
        user = result.scalar_one_or_none()
        print(f"User found: {user}")
        
        if user:
            print(f"User id: {user.id}, type: {type(user.id)}")
            print(f"User email: {user.email}")
            print(f"User status: {user.status}")
        else:
            # Check all users
            all_result = await session.execute(select(User.id, User.email, User.deleted_at))
            for row in all_result.fetchall():
                print(f"  DB user: id={row[0]} (type={type(row[0])}), email={row[1]}, deleted_at={row[2]}")

asyncio.run(test())
