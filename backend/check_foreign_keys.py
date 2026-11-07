"""
Check foreign key relationships for students table
"""
import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionLocal


async def check_foreign_keys():
    """Check foreign key relationships"""
    async with AsyncSessionLocal() as db:
        # Get foreign key info for SQLite
        result = await db.execute(
            text("PRAGMA foreign_keys")
        )
        fk_enabled = result.fetchone()
        print(f"Foreign keys enabled: {fk_enabled}")
        
        # Get table schema
        result = await db.execute(
            text("SELECT sql FROM sqlite_master WHERE type='table' AND name='students'")
        )
        schema = result.fetchone()
        print(f"\nStudents table schema:\n{schema[0] if schema else 'Not found'}")
        
        # Check medication_schedules table
        result = await db.execute(
            text("SELECT sql FROM sqlite_master WHERE type='table' AND name='medication_schedules'")
        )
        schema = result.fetchone()
        print(f"\nMedication schedules table schema:\n{schema[0] if schema else 'Not found'}")
        
        # Get some sample data
        result = await db.execute(
            text("SELECT id FROM students LIMIT 3")
        )
        students = result.fetchall()
        print(f"\nSample student IDs:")
        for student in students:
            print(f"  {student[0]} (type: {type(student[0]).__name__})")
        
        result = await db.execute(
            text("SELECT student_id FROM medication_schedules LIMIT 3")
        )
        schedules = result.fetchall()
        print(f"\nSample medication schedule student_ids:")
        for schedule in schedules:
            print(f"  {schedule[0]} (type: {type(schedule[0]).__name__})")


if __name__ == "__main__":
    asyncio.run(check_foreign_keys())
