"""
Sınıflara rastgele teacher_id atamak için script
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select
from app.core.database import get_db
from app.infrastructure.models.models import User, ClassRoom


async def assign_teachers_to_classes():
    """Sınıflara rastgele öğretmen atar"""
    async for db in get_db():
        try:
            # Get all classes
            classes_result = await db.execute(select(ClassRoom))
            classes = classes_result.scalars().all()
            
            # Get all users (potential teachers)
            users_result = await db.execute(select(User).where(User.deleted_at.is_(None)))
            users = users_result.scalars().all()
            
            if not classes:
                print("Sınıf bulunamadı")
                return
            
            if not users:
                print("Kullanıcı bulunamadı")
                return
            
            print(f"Toplam {len(classes)} sınıf ve {len(users)} kullanıcı bulundu")
            
            # Assign teachers to classes
            updated_count = 0
            for class_obj in classes:
                if not class_obj.teacher_id:
                    # Assign a random user as teacher
                    import random
                    teacher = random.choice(users)
                    class_obj.teacher_id = teacher.id
                    updated_count += 1
                    print(f"Sınıf '{class_obj.name}' öğretmen olarak atandı: {teacher.first_name} {teacher.last_name}")
            
            await db.commit()
            print(f"\nToplam {updated_count} sınıfa öğretmen atandı")
            
        except Exception as e:
            print(f"Hata: {e}")
            await db.rollback()
        finally:
            await db.close()


if __name__ == "__main__":
    asyncio.run(assign_teachers_to_classes())
