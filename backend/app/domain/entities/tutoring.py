from datetime import datetime, date, time
from uuid import UUID, uuid4

from sqlalchemy import String, DateTime, Date, Time, ForeignKey, Boolean, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TutoringSession(Base):
    __tablename__ = "tutoring_sessions"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    teacher_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    subject: Mapped[str] = mapped_column(String(100), nullable=True)
    session_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="SCHEDULED")
    notes: Mapped[str] = mapped_column(nullable=True)
    attendance_status: Mapped[str] = mapped_column(String(20), nullable=True)
    progress_score: Mapped[int] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TutoringRequest(Base):
    __tablename__ = "tutoring_requests"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    teacher_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=True)
    subject: Mapped[str] = mapped_column(String(100), nullable=True)
    requested_date: Mapped[date] = mapped_column(Date, nullable=False)
    preferred_time_start: Mapped[time] = mapped_column(Time, nullable=True)
    preferred_time_end: Mapped[time] = mapped_column(Time, nullable=True)
    reason: Mapped[str] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    approved_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TeacherAvailability(Base):
    __tablename__ = "teacher_availability"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    teacher_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    max_students: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
