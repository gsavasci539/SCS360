"""
Fix medication schedule student_id to match students table format
"""
import asyncio
import uuid
from sqlalchemy import text
from app.core.database import AsyncSessionLocal


async def fix_medication_student_id():
    """Fix medication schedule student_id to match students table format"""
    async with AsyncSessionLocal() as db:
        # Get all medication schedules
        result = await db.execute(
            text("SELECT id, student_id FROM medication_schedules")
        )
        schedules = result.fetchall()
        
        print(f"Found {len(schedules)} medication schedules")
        
        for schedule in schedules:
            schedule_id = schedule[0]
            student_id = schedule[1]
            
            # Try to find matching student
            result = await db.execute(
                text("SELECT id FROM students WHERE id = :student_id"),
                {"student_id": student_id}
            )
            student = result.fetchone()
            
            if not student:
                # Try without hyphens
                student_id_no_hyphens = str(student_id).replace('-', '')
                result = await db.execute(
                    text("SELECT id FROM students WHERE id = :student_id"),
                    {"student_id": student_id_no_hyphens}
                )
                student = result.fetchone()
                
                if student:
                    print(f"Found matching student: {student[0]}")
                    # Update medication schedule with correct student_id
                    await db.execute(
                        text("UPDATE medication_schedules SET student_id = :new_student_id WHERE id = :schedule_id"),
                        {"new_student_id": student[0], "schedule_id": schedule_id}
                    )
                    print(f"Updated schedule {schedule_id} student_id from {student_id} to {student[0]}")
                else:
                    print(f"No matching student found for schedule {schedule_id} with student_id {student_id}")
        
        await db.commit()
        print("Medication schedule student_id fix completed")


if __name__ == "__main__":
    asyncio.run(fix_medication_student_id())
