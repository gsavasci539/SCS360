from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from app.repositories import (
    StudentRepository,
    AttendanceRepository,
    DebtRepository,
    PaymentRepository,
    ClassRepository,
    UserRepository
)
from app.infrastructure.pdf import PDFService


class ReportService:
    """Service for generating various reports"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.student_repo = StudentRepository()
        self.attendance_repo = AttendanceRepository()
        self.debt_repo = DebtRepository()
        self.payment_repo = PaymentRepository()
        self.class_repo = ClassRepository()
        self.user_repo = UserRepository()
        self.pdf_service = PDFService()
    
    async def get_attendance_report(
        self,
        organization_id: UUID,
        class_id: Optional[UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Generate attendance report"""
        
        # Get students
        if class_id:
            students = await self.student_repo.get_by_class(self.db, class_id)
        else:
            students = await self.student_repo.get_active_students(self.db, organization_id)
        
        # Get attendance data
        attendance_data = []
        for student in students:
            if start_date and end_date:
                attendance = await self.attendance_repo.get_by_date_range(
                    self.db, student.id, start_date, end_date
                )
            else:
                attendance = []
            
            present = len([a for a in attendance if a.status == "present"])
            absent = len([a for a in attendance if a.status == "absent"])
            late = len([a for a in attendance if a.status == "late"])
            excused = len([a for a in attendance if a.status == "excused"])
            
            attendance_data.append({
                "student_id": str(student.id),
                "student_name": f"{student.first_name} {student.last_name}",
                "present": present,
                "absent": absent,
                "late": late,
                "excused": excused,
                "total": len(attendance)
            })
        
        return {
            "type": "attendance",
            "class_id": str(class_id) if class_id else None,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "data": attendance_data
        }
    
    async def get_financial_report(
        self,
        organization_id: UUID,
        branch_id: Optional[UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Generate financial report"""
        
        # Get total debts
        debts = await self.debt_repo.get_by_organization(self.db, organization_id)
        total_debt = sum(d.remaining_amount for d in debts if d.remaining_amount > 0)
        
        # Get payments
        if start_date and end_date:
            payments = await self.payment_repo.get_by_date_range(
                self.db, organization_id, start_date, end_date
            )
        else:
            payments = await self.payment_repo.get_by_organization(self.db, organization_id)
        
        total_payments = sum(p.amount for p in payments if p.status == "completed")
        
        # Payment breakdown by method
        payment_methods = {}
        for payment in payments:
            if payment.status == "completed":
                method = payment.payment_method
                payment_methods[method] = payment_methods.get(method, Decimal("0")) + payment.amount
        
        # Debt breakdown by type
        debt_types = {}
        for debt in debts:
            if debt.remaining_amount > 0:
                dtype = debt.debt_type
                debt_types[dtype] = debt_types.get(dtype, Decimal("0")) + debt.remaining_amount
        
        return {
            "type": "financial",
            "branch_id": str(branch_id) if branch_id else None,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "total_debt": float(total_debt),
            "total_payments": float(total_payments),
            "payment_methods": {k: float(v) for k, v in payment_methods.items()},
            "debt_types": {k: float(v) for k, v in debt_types.items()}
        }
    
    async def get_student_report(
        self,
        student_id: UUID
    ) -> Dict[str, Any]:
        """Generate individual student report"""
        
        student = await self.student_repo.get(self.db, student_id)
        if not student:
            return None
        
        # Get attendance
        attendance = await self.attendance_repo.get_by_student_and_date(
            self.db, student_id, datetime.utcnow()
        )
        
        # Get debts
        debts = await self.debt_repo.get_by_student(self.db, student_id)
        total_debt = sum(d.remaining_amount for d in debts if d.remaining_amount > 0)
        
        # Get payments
        payments = await self.payment_repo.get_by_student(self.db, student_id)
        total_payments = sum(p.amount for p in payments if p.status == "completed")
        
        # Get parents
        parents = await self.student_repo.get_with_parents(self.db, student_id)
        
        return {
            "type": "student",
            "student_id": str(student.id),
            "student_name": f"{student.first_name} {student.last_name}",
            "enrollment_date": student.enrollment_date.isoformat(),
            "class_id": str(student.class_id) if student.class_id else None,
            "total_debt": float(total_debt),
            "total_payments": float(total_payments),
            "attendance_status": attendance.status if attendance else None,
            "parents_count": len(parents.student_parents) if parents else 0
        }
    
    async def get_class_report(
        self,
        class_id: UUID
    ) -> Dict[str, Any]:
        """Generate class report"""
        
        cls = await self.class_repo.get(self.db, class_id)
        if not cls:
            return None
        
        # Get students
        students = await self.student_repo.get_by_class(self.db, class_id)
        
        # Get attendance for today
        today = datetime.utcnow().date()
        attendance_today = await self.attendance_repo.get_by_class_and_date(
            self.db, class_id, datetime(today.year, today.month, today.day)
        )
        
        present_count = len([a for a in attendance_today if a.status == "present"])
        absent_count = len([a for a in attendance_today if a.status == "absent"])
        
        return {
            "type": "class",
            "class_id": str(cls.id),
            "class_name": cls.name,
            "class_code": cls.code,
            "capacity": cls.capacity,
            "student_count": len(students),
            "present_today": present_count,
            "absent_today": absent_count,
            "teacher_id": str(cls.teacher_id) if cls.teacher_id else None
        }
    
    async def generate_report_pdf(
        self,
        report_data: Dict[str, Any],
        organization_data: Dict[str, Any]
    ) -> Optional[bytes]:
        """Generate PDF from report data"""
        
        report_type = report_data.get("type")
        
        if report_type == "attendance":
            return self.pdf_service.generate_attendance_report(report_data, organization_data)
        elif report_type == "financial":
            # TODO: Implement financial report PDF
            return None
        elif report_type == "student":
            # TODO: Implement student report PDF
            return None
        elif report_type == "class":
            # TODO: Implement class report PDF
            return None
        
        return None
