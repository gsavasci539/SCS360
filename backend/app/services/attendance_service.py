from typing import Optional, List
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import AttendanceRepository
from app.domain.entities.attendance import Attendance
from app.core.exceptions import AppException


class AttendanceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.attendance_repo = AttendanceRepository()

    async def create_attendance(
        self,
        organization_id: UUID,
        branch_id: UUID,
        class_id: UUID,
        student_id: UUID,
        date: datetime,
        status: str,
        **kwargs
    ) -> Attendance:
        # Check if attendance already exists
        existing = await self.attendance_repo.get_by_student_and_date(
            self.db, student_id, date
        )
        if existing:
            raise AppException("Bu öğrenci için bu tarihte zaten yoklama var", status_code=400)
        
        attendance_data = {
            "organization_id": organization_id,
            "branch_id": branch_id,
            "class_id": class_id,
            "student_id": student_id,
            "date": date,
            "status": status,
            **kwargs
        }
        
        return await self.attendance_repo.create(self.db, attendance_data)

    async def bulk_create_attendance(
        self,
        attendance_list: List[dict]
    ) -> List[Attendance]:
        created = []
        for attendance_data in attendance_list:
            try:
                attendance = await self.create_attendance(**attendance_data)
                created.append(attendance)
            except AppException:
                continue
        return created

    async def update_attendance(
        self,
        attendance_id: UUID,
        **kwargs
    ) -> Attendance:
        attendance = await self.attendance_repo.get(self.db, attendance_id)
        if not attendance:
            raise AppException("Yoklama bulunamadı", status_code=404)
        
        return await self.attendance_repo.update(self.db, attendance, kwargs)
