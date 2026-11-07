"""
Test medicine request creation
"""
import asyncio
import uuid
from datetime import date
from sqlalchemy import text
from app.core.database import AsyncSessionLocal


async def test_medicine_request():
    """Create a test medicine request"""
    async with AsyncSessionLocal() as db:
        # Get a parent user
        result = await db.execute(
            text("SELECT id, email FROM users WHERE email LIKE '%parent%' OR email LIKE '%veli%' LIMIT 1")
        )
        parent_user = result.fetchone()
        
        if not parent_user:
            print("No parent user found, creating test data...")
            # Create a test parent user
            parent_user_id = uuid.uuid4()
            await db.execute(
                text("""
                    INSERT INTO users (id, email, password_hash, first_name, last_name, status, is_super_admin)
                    VALUES (:id, :email, :password_hash, :first_name, :last_name, 'ACTIVE', FALSE)
                """),
                {
                    "id": str(parent_user_id),
                    "email": "testveli@demo.com",
                    "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU7qv7Xu7.2W", # Admin123*
                    "first_name": "Test",
                    "last_name": "Veli"
                }
            )
            
            # Create parent record
            parent_id = uuid.uuid4()
            await db.execute(
                text("""
                    INSERT INTO parents (id, user_id, phone, address, is_primary_contact)
                    VALUES (:id, :user_id, '5551234567', 'Test Adres', TRUE)
                """),
                {
                    "id": str(parent_id),
                    "user_id": str(parent_user_id)
                }
            )
            
            print(f"Created test parent user: testveli@demo.com (ID: {parent_user_id})")
            parent_user = (parent_user_id, "testveli@demo.com")
        
        # Get a student
        result = await db.execute(
            text("SELECT id, first_name, last_name FROM students LIMIT 1")
        )
        student = result.fetchone()
        
        if not student:
            print("No student found. Please create a student first.")
            return
        
        print(f"Using student: {student[1]} {student[2]} (ID: {student[0]})")
        
        # Get parent record
        result = await db.execute(
            text("SELECT id FROM parents WHERE user_id = :user_id"),
            {"user_id": str(parent_user[0])}
        )
        parent = result.fetchone()
        
        if not parent:
            print("No parent record found for user")
            return
        
        # Create student-parent relationship
        await db.execute(
            text("""
                INSERT OR IGNORE INTO student_parents (student_id, parent_id, is_primary)
                VALUES (:student_id, :parent_id, TRUE)
            """),
            {
                "student_id": str(student[0]),
                "parent_id": str(parent[0])
            }
        )
        
        # Create a test medication schedule
        from app.domain.entities.health import MedicationSchedule
        
        new_schedule = MedicationSchedule(
            student_id=student[0],
            medication_name="Parasetamol",
            dosage="5ml",
            frequency="Sabah-Akşam",
            instruction="AFTER_MEAL",
            start_date=date.today(),
            parent_notes="Test veli talebi",
            is_active=True,
            created_by=parent_user[0]
        )
        db.add(new_schedule)
        await db.commit()
        await db.refresh(new_schedule)
        
        print(f"Created test medicine request: {new_schedule.id}")
        print(f"Medication: {new_schedule.medication_name}")
        print(f"Dosage: {new_schedule.dosage}")
        print(f"Frequency: {new_schedule.frequency}")
        
        # Verify it was created
        result = await db.execute(
            text("SELECT COUNT(*) FROM medication_schedules")
        )
        count = result.scalar()
        print(f"Total medication schedules in DB: {count}")


if __name__ == "__main__":
    asyncio.run(test_medicine_request())
