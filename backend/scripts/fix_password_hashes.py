"""Fix password hashes for demo users"""

import asyncio
from sqlalchemy import select, text

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password


async def fix_passwords():
    async with AsyncSessionLocal() as db:
        # Update all demo user passwords
        demo_emails = [
            "admin@demo.com",
            "kurumadmin@demo.com",
            "subeyetkili@demo.com",
            "ogretmen@demo.com",
            "muhasebe@demo.com",
            "personel@demo.com",
            "kantin@demo.com",
            "veli@demo.com",
            "yonetici@demo.com",
            "idareci@demo.com",
            "kurumsahibi@demo.com",
        ]
        
        password = "Admin123*"
        password_hash = hash_password(password)
        
        for email in demo_emails:
            await db.execute(
                text("UPDATE users SET password_hash = :hash WHERE email = :email"),
                {"hash": password_hash, "email": email}
            )
            print(f"Updated password for {email}")
        
        await db.commit()
        print("All demo user passwords updated successfully")


if __name__ == "__main__":
    asyncio.run(fix_passwords())
