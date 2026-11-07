"""
Fix UUID format in students table to match medication schedules
"""
import asyncio
import uuid
from sqlalchemy import text
from app.core.database import AsyncSessionLocal


async def fix_uuid_format():
    """Fix UUID format in students table"""
    async with AsyncSessionLocal() as db:
        # Get all students
        result = await db.execute(
            text("SELECT id FROM students")
        )
        students = result.fetchall()
        
        print(f"Found {len(students)} students")
        
        for student in students:
            student_id = student[0]
            # Check if it's missing hyphens
            if isinstance(student_id, str) and '-' not in student_id:
                # Convert to proper UUID format
                try:
                    proper_uuid = uuid.UUID(student_id)
                    proper_str = str(proper_uuid)
                    print(f"Converting {student_id} -> {proper_str}")
                    
                    # Update the student record
                    await db.execute(
                        text("UPDATE students SET id = :new_id WHERE id = :old_id"),
                        {"new_id": proper_str, "old_id": student_id}
                    )
                except ValueError as e:
                    print(f"Error converting {student_id}: {e}")
        
        await db.commit()
        print("UUID format fix completed")


if __name__ == "__main__":
    asyncio.run(fix_uuid_format())
