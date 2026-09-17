"""Seed demo data for EduPanel."""

import asyncio
import random
import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select, text

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.infrastructure.models.models import (
    AttendanceRecord,
    AttendanceStatus,
    Branch,
    ClassRoom,
    ClassTeacher,
    Debt,
    DebtStatus,
    DebtType,
    GenderType,
    Parent,
    ParentRelationType,
    Payment,
    PaymentMethod,
    Receipt,
    ReceiptStatus,
    Student,
    StudentParent,
    StudentStatus,
    User,
    UserBranch,
    UserRole,
    UserStatus,
)

DEMO_ORG_ID = uuid.UUID("b0000000-0000-4000-8000-000000000001")
ADMIN_ID = uuid.UUID("e0000000-0000-4000-8000-000000000001")
ROLE_TEACHER = uuid.UUID("a0000000-0000-4000-8000-000000000004")
ROLE_ACCOUNTANT = uuid.UUID("a0000000-0000-4000-8000-000000000005")
BRANCH_IDS = [
    uuid.UUID("c0000000-0000-4000-8000-000000000001"),
    uuid.UUID("c0000000-0000-4000-8000-000000000002"),
    uuid.UUID("c0000000-0000-4000-8000-000000000003"),
]
CLASS_IDS = [
    uuid.UUID("d0000000-0000-4000-8000-000000000001"),
    uuid.UUID("d0000000-0000-4000-8000-000000000002"),
    uuid.UUID("d0000000-0000-4000-8000-000000000003"),
    uuid.UUID("d0000000-0000-4000-8000-000000000004"),
]

FIRST_NAMES = ["Ali", "Ayşe", "Mehmet", "Zeynep", "Can", "Elif", "Burak", "Selin", "Emre", "Deniz",
               "Cem", "Merve", "Kaan", "Buse", "Arda", "İrem", "Onur", "Gizem", "Barış", "Ece",
               "Tolga", "Seda", "Murat", "Pınar", "Serkan"]
LAST_NAMES = ["Yılmaz", "Kaya", "Demir", "Çelik", "Şahin", "Yıldız", "Aydın", "Öztürk", "Arslan", "Doğan"]


async def seed():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == "admin@demo.com"))
        admin = result.scalar_one_or_none()
        if admin:
            admin.password_hash = hash_password("Admin123*")

        existing = await db.execute(select(Student).where(Student.organization_id == DEMO_ORG_ID).limit(1))
        if existing.scalar_one_or_none():
            print("Demo students already exist, skipping...")
            await db.commit()
            return

        students_created = []
        for i in range(25):
            branch_id = BRANCH_IDS[i % 3]
            class_id = CLASS_IDS[i % 4]
            student = Student(
                organization_id=DEMO_ORG_ID,
                branch_id=branch_id,
                class_id=class_id,
                student_number=f"STU{2025001 + i:04d}",
                first_name=FIRST_NAMES[i % len(FIRST_NAMES)],
                last_name=LAST_NAMES[i % len(LAST_NAMES)],
                gender=GenderType.MALE if i % 2 == 0 else GenderType.FEMALE,
                birth_date=date(2018, 1, 1) + timedelta(days=i * 30),
                status=StudentStatus.ACTIVE,
                created_by=ADMIN_ID,
                updated_by=ADMIN_ID,
            )
            db.add(student)
            await db.flush()

            parent = Parent(
                organization_id=DEMO_ORG_ID,
                first_name=f"Veli{student.first_name}",
                last_name=student.last_name,
                relation_type=ParentRelationType.MOTHER if i % 2 == 0 else ParentRelationType.FATHER,
                phone=f"05{random.randint(300000000, 599999999)}",
                sms_phone=f"05{random.randint(300000000, 599999999)}",
                email=f"veli{i + 1}@demo.com",
                receive_notifications=True,
                created_by=ADMIN_ID,
            )
            db.add(parent)
            await db.flush()
            db.add(StudentParent(student_id=student.id, parent_id=parent.id, is_primary=True))

            if i % 3 == 0:
                debt = Debt(
                    organization_id=DEMO_ORG_ID,
                    branch_id=branch_id,
                    student_id=student.id,
                    debt_type=DebtType.EDUCATION,
                    description="Aylık eğitim ücreti",
                    amount=Decimal("5000.00"),
                    paid_amount=Decimal("0"),
                    status=DebtStatus.UNPAID if i % 2 == 0 else DebtStatus.OVERDUE,
                    due_date=date.today() - timedelta(days=5) if i % 2 == 0 else date.today() + timedelta(days=15),
                    created_by=ADMIN_ID,
                )
                db.add(debt)
                await db.flush()
                if i % 6 == 0:
                    payment = Payment(
                        organization_id=DEMO_ORG_ID,
                        branch_id=branch_id,
                        student_id=student.id,
                        debt_id=debt.id,
                        amount=Decimal("2500.00"),
                        payment_method=PaymentMethod.CASH,
                        received_by=ADMIN_ID,
                    )
                    db.add(payment)
                    await db.flush()
                    debt.paid_amount = Decimal("2500.00")
                    debt.status = DebtStatus.PARTIALLY_PAID
                    remaining = debt.amount - debt.paid_amount
                    db.add(Receipt(
                        organization_id=DEMO_ORG_ID,
                        branch_id=branch_id,
                        payment_id=payment.id,
                        receipt_number=f"RCP-SEED-{str(payment.id)[:8].upper()}",
                        status=ReceiptStatus.ACTIVE,
                        issued_by=ADMIN_ID,
                        remaining_debt=remaining,
                    ))

            if i % 4 == 0:
                db.add(AttendanceRecord(
                    organization_id=DEMO_ORG_ID,
                    branch_id=branch_id,
                    class_id=class_id,
                    student_id=student.id,
                    attendance_date=date.today() - timedelta(days=1),
                    status=AttendanceStatus.ABSENT if i % 8 == 0 else AttendanceStatus.PRESENT,
                    recorded_by=ADMIN_ID,
                ))

            students_created.append(student)

        # Demo öğretmen ve muhasebe kullanıcıları
        for email, first, last, role_id, branch_idx in [
            ("ogretmen@demo.com", "Ayşe", "Öğretmen", ROLE_TEACHER, 0),
            ("muhasebe@demo.com", "Mehmet", "Muhasebe", ROLE_ACCOUNTANT, 0),
        ]:
            existing_user = await db.execute(select(User).where(User.email == email))
            if not existing_user.scalar_one_or_none():
                demo_user = User(
                    organization_id=DEMO_ORG_ID,
                    email=email,
                    password_hash=hash_password("Admin123*"),
                    first_name=first,
                    last_name=last,
                    status=UserStatus.ACTIVE,
                    created_by=ADMIN_ID,
                )
                db.add(demo_user)
                await db.flush()
                db.add(UserRole(user_id=demo_user.id, role_id=role_id))
                db.add(UserBranch(user_id=demo_user.id, branch_id=BRANCH_IDS[branch_idx]))

        # Öğretmeni sınıfa ata
        teacher = (await db.execute(select(User).where(User.email == "ogretmen@demo.com"))).scalar_one_or_none()
        if teacher:
            db.add(ClassTeacher(class_id=CLASS_IDS[0], user_id=teacher.id, is_primary=True, assigned_by=ADMIN_ID))

        await db.commit()
        print(f"Seeded {len(students_created)} students with parents, debts, and attendance")


if __name__ == "__main__":
    asyncio.run(seed())
