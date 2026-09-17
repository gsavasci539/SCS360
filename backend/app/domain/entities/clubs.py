from datetime import datetime, date, time
from uuid import UUID, uuid4

from sqlalchemy import String, DateTime, Date, Time, ForeignKey, Boolean, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SchoolClub(Base):
    __tablename__ = "school_clubs"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    branch_id: Mapped[UUID] = mapped_column(ForeignKey("branches.id"), nullable=False)
    club_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(nullable=True)
    advisor_teacher_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=True)
    max_members: Mapped[int] = mapped_column(Integer, default=30)
    current_members: Mapped[int] = mapped_column(Integer, default=0)
    meeting_day: Mapped[str] = mapped_column(String(20), nullable=True)
    meeting_time: Mapped[time] = mapped_column(Time, nullable=True)
    meeting_location: Mapped[str] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ClubMembership(Base):
    __tablename__ = "club_memberships"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    club_id: Mapped[UUID] = mapped_column(ForeignKey("school_clubs.id"), nullable=False)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    joined_date: Mapped[date] = mapped_column(Date, nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="MEMBER")
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    notes: Mapped[str] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ClubEvent(Base):
    __tablename__ = "club_events"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    club_id: Mapped[UUID] = mapped_column(ForeignKey("school_clubs.id"), nullable=False)
    event_name: Mapped[str] = mapped_column(String(255), nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    event_time: Mapped[time] = mapped_column(Time, nullable=True)
    location: Mapped[str] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(nullable=True)
    max_participants: Mapped[int] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class StudentCertificate(Base):
    __tablename__ = "student_certificates"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    certificate_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(nullable=True)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    issued_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=True)
    event_id: Mapped[UUID] = mapped_column(ForeignKey("club_events.id"), nullable=True)
    template_id: Mapped[str] = mapped_column(String(100), nullable=True)
    pdf_url: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
