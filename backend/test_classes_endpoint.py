"""
Classes endpoint'ini test etmek için script
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select
from app.core.database import get_db
from app.repositories import ClassRepository


async def test_classes_endpoint():
    """Classes endpoint'ini test eder"""
    async for db in get_db():
        try:
            repo = ClassRepository()
            
            # Test get_by_organization
            organization_id = "b5c1a4ad-8e94-4bc7-81a0-cda7f4b36e83"
            classes = await repo.get_by_organization(db, organization_id, 0, 100)
            
            print(f"get_by_organization sonucu:")
            for cls in classes:
                print(f"  Sınıf: {cls.get('name')}")
                print(f"  Teacher ID: {cls.get('teacher_id')}")
                print(f"  Teacher Name: {cls.get('teacher_name')}")
                print(f"  Tüm keys: {list(cls.keys())}")
                print()
            
        except Exception as e:
            print(f"Hata: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await db.close()


if __name__ == "__main__":
    asyncio.run(test_classes_endpoint())
