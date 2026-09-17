from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import StudentRepository, ParentRepository
from app.domain.entities.student import Student
from app.domain.entities.student_parent import StudentParent
from app.core.exceptions import AppException


class StudentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.student_repo = StudentRepository()
        self.parent_repo = ParentRepository()

    async def create_student(
        self,
        organization_id: UUID,
        branch_id: UUID,
        first_name: str,
        last_name: str,
        enrollment_date,
        parent_ids: Optional[List[UUID]] = None,
        **kwargs
    ) -> Student:
        student_data = {
            "organization_id": organization_id,
            "branch_id": branch_id,
            "first_name": first_name,
            "last_name": last_name,
            "enrollment_date": enrollment_date,
            **kwargs
        }
        
        student = await self.student_repo.create(self.db, student_data)
        
        # Assign parents
        if parent_ids:
            for parent_id in parent_ids:
                student_parent = StudentParent(student_id=student.id, parent_id=parent_id)
                self.db.add(student_parent)
            await self.db.flush()
        
        return student

    async def update_student(
        self,
        student_id: UUID,
        parent_ids: Optional[List[UUID]] = None,
        **kwargs
    ) -> Student:
        student = await self.student_repo.get(self.db, student_id)
        if not student:
            raise AppException("Öğrenci bulunamadı", status_code=404)
        
        student = await self.student_repo.update(self.db, student, kwargs)
        
        # Update parent relationships if provided
        if parent_ids is not None:
            # Remove existing relationships
            await self.db.execute(
                f"DELETE FROM student_parents WHERE student_id = '{student_id}'"
            )
            
            # Add new relationships
            for parent_id in parent_ids:
                student_parent = StudentParent(student_id=student_id, parent_id=parent_id)
                self.db.add(student_parent)
            
            await self.db.flush()
        
        return student

    async def get_student_parents(self, student_id: UUID) -> List:
        from sqlalchemy import select
        from app.domain.entities.parent import Parent
        from app.domain.entities.student_parent import StudentParent
        
        result = await self.db.execute(
            select(Parent)
            .join(StudentParent, Parent.id == StudentParent.parent_id)
            .where(StudentParent.student_id == student_id)
        )
        return result.scalars().all()
