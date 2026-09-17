from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from app.domain.entities.student import Student
from app.domain.entities.student_parent import StudentParent
from app.repositories.base_repository import BaseRepository


class StudentRepository(BaseRepository[Student]):
    def __init__(self):
        super().__init__(Student)
    async def get_by_branch(
        self, db: AsyncSession, branch_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Student]:
        result = await db.execute(
            select(Student)
            .where(Student.branch_id == branch_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_class(
        self, db: AsyncSession, class_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Student]:
        result = await db.execute(
            select(Student)
            .where(Student.class_id == class_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_active_students(
        self, db: AsyncSession, organization_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Student]:
        result = await db.execute(
            select(Student)
            .where(
                and_(
                    Student.organization_id == organization_id,
                    Student.status == "active"
                )
            )
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def search_students(
        self,
        db: AsyncSession,
        organization_id: UUID,
        search_term: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Student]:
        result = await db.execute(
            select(Student)
            .where(
                and_(
                    Student.organization_id == organization_id,
                    or_(
                        Student.first_name.ilike(f"%{search_term}%"),
                        Student.last_name.ilike(f"%{search_term}%"),
                        Student.student_number.ilike(f"%{search_term}%")
                    )
                )
            )
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_with_parents(
        self, db: AsyncSession, student_id: UUID
    ) -> Optional[Student]:
        result = await db.execute(
            select(Student)
            .options(selectinload(Student.student_parents))
            .where(Student.id == student_id)
        )
        return result.scalar_one_or_none()
