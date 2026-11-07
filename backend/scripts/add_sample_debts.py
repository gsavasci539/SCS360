import asyncio
import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.infrastructure.models.models import Debt, Payment, DebtStatus, DebtType, Student, StudentParent, Parent, User
from app.core.config import get_settings

async def add_sample_debts():
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Get a user for received_by field
        user_result = await session.execute(select(User).limit(1))
        user = user_result.scalar_one_or_none()
        
        if not user:
            print("No user found. Please create a user first.")
            return
        
        # Get all students
        student_result = await session.execute(select(Student))
        students = student_result.scalars().all()
        
        print(f"Found {len(students)} students")
        
        if not students:
            print("No students found. Please create students first.")
            return
        
        # Create debts for students
        debt_types = [DebtType.EDUCATION, DebtType.FOOD, DebtType.SERVICE, DebtType.STATIONERY]
        
        for student in students:
            # Skip students without branch_id
            if not student.branch_id:
                print(f"Skipping student {student.first_name} {student.last_name} - no branch_id")
                continue
            
            # Create 1-3 debts per student
            num_debts = random.randint(1, 3)
            for i in range(num_debts):
                debt_type = random.choice(debt_types)
                amount = Decimal(str(random.randint(1000, 5000)))
                due_date = datetime.now() + timedelta(days=random.randint(30, 90))
                
                debt = Debt(
                    organization_id=student.organization_id,
                    branch_id=student.branch_id,
                    student_id=student.id,
                    debt_type=debt_type,
                    amount=amount,
                    paid_amount=Decimal("0"),
                    due_date=due_date,
                    status=random.choice([DebtStatus.UNPAID, DebtStatus.PARTIALLY_PAID, DebtStatus.PAID]),
                    description=f"{debt_type.value} ücreti"
                )
                
                session.add(debt)
                await session.flush()  # Get debt ID
                
                # If partially paid or paid, add some payment
                if debt.status in [DebtStatus.PARTIALLY_PAID, DebtStatus.PAID]:
                    if debt.status == DebtStatus.PAID:
                        debt.paid_amount = amount
                    else:
                        debt.paid_amount = amount * Decimal("0.5")  # 50% paid
                    
                    # Create payment record with debt_id
                    payment = Payment(
                        organization_id=student.organization_id,
                        branch_id=student.branch_id,
                        student_id=student.id,
                        debt_id=debt.id,  # Now we have the debt ID
                        amount=debt.paid_amount,
                        payment_method=random.choice(["CASH", "BANK_TRANSFER", "CREDIT_CARD"]),
                        payment_date=datetime.now() - timedelta(days=random.randint(1, 30)),
                        notes=f"{debt_type.value} ödemesi",
                        received_by=user.id
                    )
                    session.add(payment)
                
                print(f"Added debt for student {student.first_name} {student.last_name}: {amount} TL ({debt_type.value})")
        
        await session.commit()
        print("Sample debts and payments added successfully!")

if __name__ == "__main__":
    asyncio.run(add_sample_debts())
