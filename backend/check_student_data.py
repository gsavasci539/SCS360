"""
Check student data and medication schedule relationship
"""
import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionLocal


async def check_student_data():
    """Check student and medication schedule data"""
    async with AsyncSessionLocal() as db:
        # Get all students
        result = await db.execute(
            text("SELECT id, first_name, last_name FROM students LIMIT 5")
        )
        students = result.fetchall()
        print("Students:")
        for student in students:
            print(f"  {student[0]}: {student[1]} {student[2]}")
        
        # Get medication schedules
        result = await db.execute(
            text("SELECT id, student_id, medication_name FROM medication_schedules")
        )
        schedules = result.fetchall()
        print("\nMedication schedules:")
        for schedule in schedules:
            print(f"  {schedule[0]}: student_id={schedule[1]}, medication={schedule[2]}")
        
        # Check if student_id in schedules matches any student
        result = await db.execute(
            text("""
                SELECT ms.id, ms.student_id, ms.medication_name, s.first_name, s.last_name
                FROM medication_schedules ms
                LEFT JOIN students s ON ms.student_id = s.id
            """)
        )
        joined = result.fetchall()
        print("\nJoined data:")
        for row in joined:
            print(f"  Schedule {row[0]}: student_id={row[1]}, medication={row[2]}, student={row[3]} {row[4]}")


if __name__ == "__main__":
    asyncio.run(check_student_data())
