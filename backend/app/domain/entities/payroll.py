from datetime import datetime, date
from uuid import UUID, uuid4
from decimal import Decimal

from sqlalchemy import String, DateTime, Date, ForeignKey, Boolean, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class StaffTimesheet(Base):
    __tablename__ = "staff_timesheets"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    staff_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    check_in_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    check_out_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    work_hours: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    status: Mapped[str] = mapped_column(String(20), default="PRESENT")
    notes: Mapped[str] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AdditionalCourseHours(Base):
    __tablename__ = "additional_course_hours"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    staff_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    period: Mapped[str] = mapped_column(String(20), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=True)
    total_hours: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    hourly_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    approved_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PayrollRecord(Base):
    __tablename__ = "payroll_records"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    staff_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    period: Mapped[str] = mapped_column(String(20), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=True)
    base_salary: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    additional_course_payment: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    bonus: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    advance_payment: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    deductions: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    net_salary: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    payment_date: Mapped[date] = mapped_column(Date, nullable=True)
    payment_method: Mapped[str] = mapped_column(String(50), nullable=True)
    bank_account: Mapped[str] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    approved_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
