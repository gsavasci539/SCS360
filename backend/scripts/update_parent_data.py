import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uuid
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, update
from app.infrastructure.models.models import Parent, ParentRelationType
from app.core.database import get_db

# Parent data to update - will be used cyclically for all parents
PARENT_DATA = [
    {
        "first_name": "Hasan",
        "last_name": "Yılmaz",
        "email": "hasan.yilmaz@example.com",
        "phone": "+905321234567",
        "sms_phone": "+905321234567",
        "whatsapp_phone": "+905321234567",
        "relation_type": ParentRelationType.FATHER
    },
    {
        "first_name": "Zeynep",
        "last_name": "Demir",
        "email": "zeynep.demir@example.com",
        "phone": "+905322345678",
        "sms_phone": "+905322345678",
        "whatsapp_phone": "+905322345678",
        "relation_type": ParentRelationType.MOTHER
    },
    {
        "first_name": "İbrahim",
        "last_name": "Kaya",
        "email": "ibrahim.kaya@example.com",
        "phone": "+905323456789",
        "sms_phone": "+905323456789",
        "whatsapp_phone": "+905323456789",
        "relation_type": ParentRelationType.FATHER
    },
    {
        "first_name": "Ahmet",
        "last_name": "Veli",
        "email": "parent1@scs360.com",
        "phone": "05562072879",
        "sms_phone": "05562072879",
        "whatsapp_phone": "05562072879",
        "relation_type": ParentRelationType.FATHER
    },
    {
        "first_name": "Fatma",
        "last_name": "Çelik",
        "email": "fatma.çelik@example.com",
        "phone": "5558158468",
        "sms_phone": "5558158468",
        "whatsapp_phone": "5558158468",
        "relation_type": ParentRelationType.MOTHER
    },
    {
        "first_name": "Ali",
        "last_name": "Şahin",
        "email": "ali.şahin@example.com",
        "phone": "5550898425",
        "sms_phone": "5550898425",
        "whatsapp_phone": "5550898425",
        "relation_type": ParentRelationType.FATHER
    },
    {
        "first_name": "Mehmet",
        "last_name": "Özkan",
        "email": "mehmet.ozkan@example.com",
        "phone": "+905324567890",
        "sms_phone": "+905324567890",
        "whatsapp_phone": "+905324567890",
        "relation_type": ParentRelationType.FATHER
    },
    {
        "first_name": "Ayşe",
        "last_name": "Yıldız",
        "email": "ayse.yildiz@example.com",
        "phone": "+905325678901",
        "sms_phone": "+905325678901",
        "whatsapp_phone": "+905325678901",
        "relation_type": ParentRelationType.MOTHER
    },
    {
        "first_name": "Mustafa",
        "last_name": "Aydın",
        "email": "mustafa.aydin@example.com",
        "phone": "+905326789012",
        "sms_phone": "+905326789012",
        "whatsapp_phone": "+905326789012",
        "relation_type": ParentRelationType.FATHER
    },
    {
        "first_name": "Elif",
        "last_name": "Kara",
        "email": "elif.kara@example.com",
        "phone": "+905327890123",
        "sms_phone": "+905327890123",
        "whatsapp_phone": "+905327890123",
        "relation_type": ParentRelationType.MOTHER
    }
]

async def update_parents():
    from app.core.config import get_settings
    
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Get all existing parents
        result = await session.execute(select(Parent))
        parents = result.scalars().all()
        
        print(f"Found {len(parents)} parents in database")
        
        # Update each parent with the corresponding data (cycle through data if more parents than data entries)
        for i, parent in enumerate(parents):
            data = PARENT_DATA[i % len(PARENT_DATA)]  # Cycle through data
            print(f"Updating parent {parent.id}: {parent.first_name} {parent.last_name} -> {data['first_name']} {data['last_name']}")
            
            await session.execute(
                update(Parent)
                .where(Parent.id == parent.id)
                .values(
                    first_name=data["first_name"],
                    last_name=data["last_name"],
                    email=data["email"],
                    phone=data["phone"],
                    sms_phone=data["sms_phone"],
                    whatsapp_phone=data["whatsapp_phone"],
                    relation_type=data["relation_type"],
                    receive_notifications=True
                )
            )
        
        await session.commit()
        print("Parent data updated successfully!")

if __name__ == "__main__":
    asyncio.run(update_parents())
