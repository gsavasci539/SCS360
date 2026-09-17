from datetime import datetime, date, time
from uuid import UUID, uuid4

from sqlalchemy import String, DateTime, Date, Time, ForeignKey, Integer, Numeric, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Exam(Base):
    __tablename__ = "exams"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    class_id: Mapped[UUID] = mapped_column(ForeignKey("classes.id"), nullable=False)
    subject_id: Mapped[UUID] = mapped_column(nullable=True)
    teacher_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    exam_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="SCHEDULED")
    exam_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    max_score: Mapped[float] = mapped_column(Numeric(5, 2), default=100.00)
    weight: Mapped[float] = mapped_column(Numeric(3, 2), default=1.00)
    description: Mapped[str] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=True)


class ExamResult(Base):
    __tablename__ = "exam_results"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    exam_id: Mapped[UUID] = mapped_column(ForeignKey("exams.id"), nullable=False)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=True)
    grade_scale: Mapped[str] = mapped_column(String(10), nullable=True)
    notes: Mapped[str] = mapped_column(String(1000), nullable=True)
    submitted_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ReportCard(Base):
    __tablename__ = "report_cards"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    academic_year: Mapped[str] = mapped_column(String(20), nullable=False)
    semester: Mapped[str] = mapped_column(String(20), nullable=False)
    gpa: Mapped[float] = mapped_column(Numeric(3, 2), nullable=True)
    class_rank: Mapped[int] = mapped_column(Integer, nullable=True)
    total_students: Mapped[int] = mapped_column(Integer, nullable=True)
    attendance_rate: Mapped[float] = mapped_column(Numeric(5, 2), nullable=True)
    teacher_comments: Mapped[str] = mapped_column(String(2000), nullable=True)
    principal_comments: Mapped[str] = mapped_column(String(2000), nullable=True)
    generated_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    pdf_url: Mapped[str] = mapped_column(String(500), nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
