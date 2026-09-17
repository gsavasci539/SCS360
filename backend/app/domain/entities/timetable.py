from datetime import datetime, time
from uuid import UUID, uuid4

from sqlalchemy import String, DateTime, Time, ForeignKey, Boolean, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TimetableSlot(Base):
    __tablename__ = "timetable_slots"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    day: Mapped[str] = mapped_column(String(20), nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    is_break: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ClassroomAssignment(Base):
    __tablename__ = "classroom_assignments"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    class_id: Mapped[UUID] = mapped_column(ForeignKey("classes.id"), nullable=False)
    teacher_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=True)
    subject_id: Mapped[UUID] = mapped_column(nullable=True)
    room_number: Mapped[str] = mapped_column(String(50), nullable=True)
    capacity: Mapped[int] = mapped_column(Integer, default=30)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Timetable(Base):
    __tablename__ = "timetables"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    class_id: Mapped[UUID] = mapped_column(ForeignKey("classes.id"), nullable=False)
    slot_id: Mapped[UUID] = mapped_column(ForeignKey("timetable_slots.id"), nullable=False)
    classroom_assignment_id: Mapped[UUID] = mapped_column(ForeignKey("classroom_assignments.id"), nullable=True)
    academic_year: Mapped[str] = mapped_column(String(20), nullable=False)
    semester: Mapped[str] = mapped_column(String(20), default="FALL")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=True)
