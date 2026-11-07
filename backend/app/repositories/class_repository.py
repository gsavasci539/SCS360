from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.domain.entities.class_ import Class
from app.repositories.base_repository import BaseRepository


class ClassRepository(BaseRepository[Class]):
    def __init__(self):
        super().__init__(Class)
    
    async def get_by_code(
        self, db: AsyncSession, code: str, organization_id: UUID
    ) -> Optional[Class]:
        result = await db.execute(
            select(Class).where(
                and_(Class.code == code, Class.organization_id == organization_id)
            )
        )
        return result.scalar_one_or_none()

    async def get_by_branch(
        self, db: AsyncSession, branch_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[dict]:
        from app.infrastructure.models.models import User
        
        result = await db.execute(
            select(Class)
            .where(Class.branch_id == branch_id)
            .offset(skip)
            .limit(limit)
        )
        
        classes = result.scalars().all()
        
        classes_data = []
        for class_obj in classes:
            # Get teacher for this class using teacher_id
            teacher_name = ""
            if class_obj.teacher_id:
                teacher_result = await db.execute(
                    select(User.first_name, User.last_name)
                    .where(User.id == class_obj.teacher_id)
                )
                teacher_row = teacher_result.first()
                teacher_name = f"{teacher_row[0]} {teacher_row[1]}" if teacher_row else ""
            
            class_dict = {
                "id": str(class_obj.id),
                "name": class_obj.name or "",
                "code": class_obj.code or "",
                "capacity": class_obj.capacity or 0,
                "occupancy": 0,
                "academic_year": class_obj.academic_year or "",
                "is_active": class_obj.is_active,
                "status": "ACTIVE" if class_obj.is_active else "PASSIVE",
                "teacher_name": teacher_name,
                "teacher_id": str(class_obj.teacher_id) if class_obj.teacher_id else None
            }
            classes_data.append(class_dict)
        
        return classes_data

    async def get_by_organization(
        self, db: AsyncSession, organization_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[dict]:
        from app.infrastructure.models.models import User, Student
        from sqlalchemy import func
        
        print(f"DEBUG: get_by_organization called with org_id={organization_id}, skip={skip}, limit={limit}")
        
        # Get classes
        result = await db.execute(
            select(Class)
            .where(Class.organization_id == organization_id)
            .offset(skip)
            .limit(limit)
        )
        
        classes = result.scalars().all()
        print(f"DEBUG: Found {len(classes)} classes")
        
        classes_data = []
        for class_obj in classes:
            print(f"DEBUG: Processing class {class_obj.name}, teacher_id={class_obj.teacher_id}")
            
            # Get teacher for this class using teacher_id
            teacher_name = ""
            if class_obj.teacher_id:
                teacher_result = await db.execute(
                    select(User.first_name, User.last_name)
                    .where(User.id == class_obj.teacher_id)
                )
                teacher_row = teacher_result.first()
                teacher_name = f"{teacher_row[0]} {teacher_row[1]}" if teacher_row else ""
                print(f"DEBUG: Teacher found: {teacher_name}")
            else:
                print(f"DEBUG: No teacher_id for class {class_obj.name}")
            
            class_dict = {
                "id": str(class_obj.id),
                "name": class_obj.name or "",
                "code": class_obj.code or "",
                "capacity": class_obj.capacity or 0,
                "occupancy": 0,
                "academic_year": class_obj.academic_year or "",
                "is_active": class_obj.is_active,
                "status": "ACTIVE" if class_obj.is_active else "PASSIVE",
                "teacher_name": teacher_name,
                "teacher_id": str(class_obj.teacher_id) if class_obj.teacher_id else None
            }
            print(f"DEBUG: Class dict teacher_name: {class_dict['teacher_name']}")
            classes_data.append(class_dict)
        
        print(f"DEBUG: Returning {len(classes_data)} classes with data")
        return classes_data

    async def get_active_classes(
        self, db: AsyncSession, organization_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Class]:
        result = await db.execute(
            select(Class)
            .where(
                and_(
                    Class.organization_id == organization_id,
                    Class.is_active == True
                )
            )
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_teacher(
        self, db: AsyncSession, teacher_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[dict]:
        from app.infrastructure.models.models import User
        
        result = await db.execute(
            select(Class)
            .where(Class.teacher_id == teacher_id)
            .offset(skip)
            .limit(limit)
        )
        
        classes = result.scalars().all()
        
        classes_data = []
        for class_obj in classes:
            # Get teacher for this class using teacher_id
            teacher_name = ""
            if class_obj.teacher_id:
                teacher_result = await db.execute(
                    select(User.first_name, User.last_name)
                    .where(User.id == class_obj.teacher_id)
                )
                teacher_row = teacher_result.first()
                teacher_name = f"{teacher_row[0]} {teacher_row[1]}" if teacher_row else ""
            
            class_dict = {
                "id": str(class_obj.id),
                "name": class_obj.name or "",
                "code": class_obj.code or "",
                "capacity": class_obj.capacity or 0,
                "occupancy": 0,
                "academic_year": class_obj.academic_year or "",
                "is_active": class_obj.is_active,
                "status": "ACTIVE" if class_obj.is_active else "PASSIVE",
                "teacher_name": teacher_name,
                "teacher_id": str(class_obj.teacher_id) if class_obj.teacher_id else None
            }
            classes_data.append(class_dict)
        
        return classes_data
