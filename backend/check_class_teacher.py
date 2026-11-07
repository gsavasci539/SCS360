"""
Sınıfların teacher_id değerlerini kontrol etmek için script
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select
from app.core.database import get_db
from app.infrastructure.models.models import User, ClassRoom


async def check_class_teachers():
    """Sınıfların teacher_id değerlerini kontrol eder"""
    async for db in get_db():
        try:
            # Get all classes
            classes_result = await db.execute(select(ClassRoom))
            classes = classes_result.scalars().all()
            
            print(f"Toplam {len(classes)} sınıf bulundu:")
            
            for class_obj in classes:
                print(f"  Sınıf: {class_obj.name} ({class_obj.code})")
                print(f"    ID: {class_obj.id}")
                print(f"    Teacher ID: {class_obj.teacher_id}")
                
                if class_obj.teacher_id:
                    # Get teacher info
                    teacher_result = await db.execute(
                        select(User).where(User.id == class_obj.teacher_id)
                    )
                    teacher = teacher_result.scalar_one_or_none()
                    if teacher:
                        print(f"    Teacher: {teacher.first_name} {teacher.last_name}")
                else:
                    print(f"    Teacher: ATANMADI")
                print()
            
        except Exception as e:
            print(f"Hata: {e}")
        finally:
            await db.close()


if __name__ == "__main__":
    asyncio.run(check_class_teachers())
