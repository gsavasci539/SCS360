"""Clear demo data from EduPanel database."""

import asyncio
from uuid import UUID

from sqlalchemy import select, delete, text

from app.core.database import AsyncSessionLocal
from app.infrastructure.models.models import (
    AttendanceRecord,
    Branch,
    ClassRoom,
    ClassTeacher,
    Debt,
    Parent,
    Payment,
    Receipt,
    Student,
    StudentParent,
    User,
    UserRole,
    UserBranch,
)

DEMO_ORG_ID = UUID("b0000000-0000-4000-8000-000000000001")


async def clear_demo_data():
    async with AsyncSessionLocal() as db:
        print("Clearing demo data...")
        
        # Delete in correct order due to foreign key constraints
        await db.execute(delete(AttendanceRecord).where(AttendanceRecord.organization_id == DEMO_ORG_ID))
        await db.execute(delete(Receipt).where(Receipt.organization_id == DEMO_ORG_ID))
        await db.execute(delete(Payment).where(Payment.organization_id == DEMO_ORG_ID))
        await db.execute(delete(Debt).where(Debt.organization_id == DEMO_ORG_ID))
        await db.execute(delete(StudentParent).where(StudentParent.student_id.in_(
            select(Student.id).where(Student.organization_id == DEMO_ORG_ID)
        )))
        await db.execute(delete(Parent).where(Parent.organization_id == DEMO_ORG_ID))
        await db.execute(delete(Student).where(Student.organization_id == DEMO_ORG_ID))
        await db.execute(delete(ClassTeacher).where(ClassTeacher.class_id.in_(
            select(ClassRoom.id).where(ClassRoom.organization_id == DEMO_ORG_ID)
        )))
        await db.execute(delete(ClassRoom).where(ClassRoom.organization_id == DEMO_ORG_ID))
        await db.execute(delete(UserBranch).where(UserBranch.branch_id.in_(
            select(Branch.id).where(Branch.organization_id == DEMO_ORG_ID)
        )))
        await db.execute(delete(UserRole).where(UserRole.user_id.in_(
            select(User.id).where(User.organization_id == DEMO_ORG_ID)
        )))
        await db.execute(delete(User).where(User.organization_id == DEMO_ORG_ID))
        await db.execute(delete(Branch).where(Branch.organization_id == DEMO_ORG_ID))
        
        await db.commit()
        print("Demo data cleared successfully!")


if __name__ == "__main__":
    asyncio.run(clear_demo_data())
