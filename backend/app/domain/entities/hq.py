from datetime import datetime
from uuid import UUID, uuid4
from decimal import Decimal

from sqlalchemy import String, DateTime, ForeignKey, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class BranchFinancialSummary(Base):
    __tablename__ = "branch_financial_summary"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    branch_id: Mapped[UUID] = mapped_column(ForeignKey("branches.id"), nullable=False)
    period: Mapped[str] = mapped_column(String(20), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=True)
    total_revenue: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    total_expenses: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    net_profit: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    collection_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=True)
    overdue_debt: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    student_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class BranchAcademicSummary(Base):
    __tablename__ = "branch_academic_summary"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    branch_id: Mapped[UUID] = mapped_column(ForeignKey("branches.id"), nullable=False)
    period: Mapped[str] = mapped_column(String(20), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    semester: Mapped[str] = mapped_column(String(20), nullable=True)
    average_attendance_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=True)
    average_exam_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=True)
    total_students: Mapped[int] = mapped_column(Integer, default=0)
    total_teachers: Mapped[int] = mapped_column(Integer, default=0)
    student_retention_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
