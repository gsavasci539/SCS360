from typing import Optional, List
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.domain.entities.attendance import Attendance
from app.repositories.base_repository import BaseRepository


class AttendanceRepository(BaseRepository[Attendance]):
    def __init__(self):
        super().__init__(Attendance)
    async def get_by_student_and_date(
        self, db: AsyncSession, student_id: UUID, date: datetime
    ) -> Optional[Attendance]:
        result = await db.execute(
            select(Attendance).where(
                and_(
                    Attendance.student_id == student_id,
                    func.date(Attendance.date) == func.date(date)
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_by_class_and_date(
        self, db: AsyncSession, class_id: UUID, date: datetime
    ) -> List[Attendance]:
        result = await db.execute(
            select(Attendance).where(
                and_(
                    Attendance.class_id == class_id,
                    func.date(Attendance.date) == func.date(date)
                )
            )
        )
        return result.scalars().all()

    async def get_by_date_range(
        self,
        db: AsyncSession,
        student_id: UUID,
        start_date: datetime,
        end_date: datetime
    ) -> List[Attendance]:
        result = await db.execute(
            select(Attendance).where(
                and_(
                    Attendance.student_id == student_id,
                    Attendance.date >= start_date,
                    Attendance.date <= end_date
                )
            )
        )
        return result.scalars().all()

    async def get_by_class_date_range(
        self,
        db: AsyncSession,
        class_id: UUID,
        start_date: datetime,
        end_date: datetime
    ) -> List[Attendance]:
        result = await db.execute(
            select(Attendance).where(
                and_(
                    Attendance.class_id == class_id,
                    Attendance.date >= start_date,
                    Attendance.date <= end_date
                )
            )
        )
        return result.scalars().all()

    async def get_by_status(
        self,
        db: AsyncSession,
        class_id: UUID,
        date: datetime,
        status: str
    ) -> List[Attendance]:
        result = await db.execute(
            select(Attendance).where(
                and_(
                    Attendance.class_id == class_id,
                    func.date(Attendance.date) == func.date(date),
                    Attendance.status == status
                )
            )
        )
        return result.scalars().all()
