"""
Database şemasını kontrol etmek için script
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from app.core.database import get_db


async def check_db_schema():
    """Database şemasını kontrol eder"""
    async for db in get_db():
        try:
            # Check actual data
            result = await db.execute(text("SELECT id, name, teacher_id FROM classes"))
            rows = result.fetchall()
            print(f"Classes tablosu verileri:")
            for row in rows:
                print(f"  ID: {row[0]}, Name: {row[1]}, Teacher ID: {row[2]}")
            
            # Check if teacher_id column exists
            try:
                result = await db.execute(text("PRAGMA table_info(classes)"))
                columns = result.fetchall()
                print(f"\nClasses tablosu sütunları:")
                for col in columns:
                    print(f"  {col[1]}: {col[2]}")
                
                teacher_id_exists = any(col[1] == 'teacher_id' for col in columns)
                print(f"\nteacher_id alanı var mı: {teacher_id_exists}")
            except Exception as e:
                print(f"PRAGMA hatası: {e}")
            
        except Exception as e:
            print(f"Hata: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await db.close()


if __name__ == "__main__":
    asyncio.run(check_db_schema())
