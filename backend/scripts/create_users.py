"""
Create demo users for all roles in SCS360.
This script creates test users for OWNER, ADMIN, TEACHER, PARENT, and STAFF roles.
"""

import asyncio
import uuid
from datetime import datetime

from sqlalchemy import select, text

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.infrastructure.models.models import (
    Branch,
    ClassTeacher,
    Parent,
    ParentRelationType,
    Role,
    Student,
    StudentParent,
    StudentStatus,
    User,
    UserRole,
    UserBranch,
    UserStatus,
)

# Demo organization ID
DEMO_ORG_ID = uuid.UUID("b0000000-0000-4000-8000-000000000001")

# Demo branch IDs
BRANCH_IDS = [
    uuid.UUID("c0000000-0000-4000-8000-000000000001"),
    uuid.UUID("c0000000-0000-4000-8000-000000000002"),
    uuid.UUID("c0000000-0000-4000-8000-000000000003"),
]

# Demo class IDs
CLASS_IDS = [
    uuid.UUID("d0000000-0000-4000-8000-000000000001"),
    uuid.UUID("d0000000-0000-4000-8000-000000000002"),
    uuid.UUID("d0000000-0000-4000-8000-000000000003"),
    uuid.UUID("d0000000-0000-4000-8000-000000000004"),
]

# Role IDs (these should match the roles in your database)
ROLE_OWNER = uuid.UUID("a0000000-0000-4000-8000-000000000001")
ROLE_ADMIN = uuid.UUID("a0000000-0000-4000-8000-000000000002")
ROLE_TEACHER = uuid.UUID("a0000000-0000-4000-8000-000000000004")
ROLE_PARENT = uuid.UUID("a0000000-0000-4000-8000-000000000006")
ROLE_STAFF = uuid.UUID("a0000000-0000-4000-8000-000000000007")


async def get_or_create_role(db, role_id, role_name):
    """Get or create a role by ID"""
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if not role:
        # Try to find role by slug/name
        result = await db.execute(select(Role).where(Role.slug == role_name.lower()))
        role = result.scalar_one_or_none()
        if role:
            return role
        # Create new role
        role = Role(id=role_id, name=role_name, slug=role_name.lower(), description=f"{role_name} role")
        db.add(role)
        await db.flush()
    return role


async def create_user(db, email, password, first_name, last_name, role_id, branch_ids=None):
    """Create a user with specified role and branches"""
    # Check if user exists
    result = await db.execute(select(User).where(User.email == email))
    existing = result.scalar_one_or_none()
    
    if existing:
        print(f"  ✓ User {email} already exists, updating password...")
        existing.password_hash = hash_password(password)
        existing.first_name = first_name
        existing.last_name = last_name
        existing.status = UserStatus.ACTIVE
        return existing
    
    # Create new user
    user = User(
        organization_id=DEMO_ORG_ID,
        email=email,
        password_hash=hash_password(password),
        first_name=first_name,
        last_name=last_name,
        status=UserStatus.ACTIVE,
        created_by=uuid.UUID("00000000-0000-0000-0000-000000000000"),
    )
    db.add(user)
    await db.flush()
    
    # Assign role
    role = await get_or_create_role(db, role_id, email.split("@")[0].upper())
    db.add(UserRole(user_id=user.id, role_id=role.id))
    
    # Assign branches
    if branch_ids:
        for branch_id in branch_ids:
            # Check if branch exists
            branch_result = await db.execute(select(Branch).where(Branch.id == branch_id))
            if branch_result.scalar_one_or_none():
                db.add(UserBranch(user_id=user.id, branch_id=branch_id))
    
    print(f"  ✓ Created user: {email}")
    return user


async def create_demo_users():
    """Create all demo users"""
    async with AsyncSessionLocal() as db:
        print("Creating demo users...")
        
        # OWNER user
        print("\n1. Creating OWNER user...")
        owner_user = await create_user(
            db,
            email="owner@scs360.com",
            password="Owner123*",
            first_name="Kurucu",
            last_name="Yönetici",
            role_id=ROLE_OWNER,
            branch_ids=BRANCH_IDS,
        )
        
        # ADMIN users
        print("\n2. Creating ADMIN users...")
        admin_users = [
            ("admin@scs360.com", "Admin123*", "Sistem", "Yöneticisi"),
            ("admin2@scs360.com", "Admin123*", "Okul", "Müdürü"),
        ]
        for email, password, first, last in admin_users:
            await create_user(
                db, email, password, first, last, ROLE_ADMIN, BRANCH_IDS[:2]
            )
        
        # TEACHER users
        print("\n3. Creating TEACHER users...")
        teacher_users = [
            ("teacher1@scs360.com", "Teacher123*", "Ayşe", "Yılmaz"),
            ("teacher2@scs360.com", "Teacher123*", "Mehmet", "Kaya"),
            ("teacher3@scs360.com", "Teacher123*", "Zeynep", "Demir"),
        ]
        for i, (email, password, first, last) in enumerate(teacher_users):
            teacher = await create_user(
                db, email, password, first, last, ROLE_TEACHER, [BRANCH_IDS[i % 3]]
            )
            # Assign teacher to a class
            if i < len(CLASS_IDS):
                db.add(
                    ClassTeacher(
                        class_id=CLASS_IDS[i],
                        user_id=teacher.id,
                        is_primary=True,
                        assigned_by=owner_user.id,
                    )
                )
        
        # PARENT users
        print("\n4. Creating PARENT users...")
        parent_users = [
            ("parent1@scs360.com", "Parent123*", "Ahmet", "Veli"),
            ("parent2@scs360.com", "Parent123*", "Fatma", "Anne"),
            ("parent3@scs360.com", "Parent123*", "Ali", "Baba"),
        ]
        for email, password, first, last in parent_users:
            parent_user = await create_user(
                db, email, password, first, last, ROLE_PARENT, [BRANCH_IDS[0]]
            )
            
            # Create parent record
            parent = Parent(
                organization_id=DEMO_ORG_ID,
                first_name=first,
                last_name=last,
                relation_type=ParentRelationType.FATHER if "Baba" in last else ParentRelationType.MOTHER,
                phone=f"05{500000000 + hash(email) % 999999999}",
                sms_phone=f"05{500000000 + hash(email) % 999999999}",
                email=email,
                receive_notifications=True,
                created_by=owner_user.id,
            )
            db.add(parent)
            await db.flush()
            
            # Link parent to a demo student if exists
            student_result = await db.execute(
                select(Student).where(Student.organization_id == DEMO_ORG_ID).limit(1)
            )
            student = student_result.scalar_one_or_none()
            if student:
                db.add(
                    StudentParent(
                        student_id=student.id, parent_id=parent.id, is_primary=True
                    )
                )
        
        # STAFF users
        print("\n5. Creating STAFF users...")
        staff_users = [
            ("staff1@scs360.com", "Staff123*", "Personel", "Güvenlik"),
            ("staff2@scs360.com", "Staff123*", "Personel", "Temizlik"),
            ("staff3@scs360.com", "Staff123*", "Personel", "Mutfak"),
        ]
        for email, password, first, last in staff_users:
            await create_user(
                db, email, password, first, last, ROLE_STAFF, BRANCH_IDS
            )
        
        await db.commit()
        print("\n✓ All demo users created successfully!")
        print("\n=== Demo User Credentials ===")
        print("OWNER: owner@scs360.com / Owner123*")
        print("ADMIN: admin@scs360.com / Admin123*")
        print("TEACHER: teacher1@scs360.com / Teacher123*")
        print("PARENT: parent1@scs360.com / Parent123*")
        print("STAFF: staff1@scs360.com / Staff123*")
        print("==============================")


if __name__ == "__main__":
    asyncio.run(create_demo_users())
