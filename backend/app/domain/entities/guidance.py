from datetime import datetime, date, time
from uuid import UUID, uuid4

from sqlalchemy import String, DateTime, Date, Time, ForeignKey, Boolean, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class GuidanceSession(Base):
    __tablename__ = "guidance_sessions"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    counselor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    session_type: Mapped[str] = mapped_column(String(20), default="INDIVIDUAL")
    session_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=True)
    end_time: Mapped[time] = mapped_column(Time, nullable=True)
    summary: Mapped[str] = mapped_column(String(2000), nullable=True)
    action_plan: Mapped[str] = mapped_column(String(2000), nullable=True)
    confidentiality_level: Mapped[str] = mapped_column(String(20), default="STANDARD")
    follow_up_date: Mapped[date] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class BehavioralIncident(Base):
    __tablename__ = "behavioral_incidents"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    reported_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    incident_date: Mapped[date] = mapped_column(Date, nullable=False)
    incident_time: Mapped[time] = mapped_column(Time, nullable=True)
    location: Mapped[str] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(String(2000), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="MINOR")
    witnesses: Mapped[str] = mapped_column(String(1000), nullable=True)
    action_taken: Mapped[str] = mapped_column(String(2000), nullable=True)
    parent_notified: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolution_date: Mapped[date] = mapped_column(Date, nullable=True)
    resolution_notes: Mapped[str] = mapped_column(String(2000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class GuidanceNote(Base):
    __tablename__ = "guidance_notes"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    counselor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    note_type: Mapped[str] = mapped_column(String(50), default="OBSERVATION")
    content: Mapped[str] = mapped_column(String(5000), nullable=False)
    confidentiality_level: Mapped[str] = mapped_column(String(20), default="STANDARD")
    tags: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
