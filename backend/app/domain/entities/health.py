from datetime import datetime, date, time
from uuid import UUID, uuid4

from sqlalchemy import String, DateTime, Date, Time, ForeignKey, Boolean, Numeric, JSON, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class HealthRecord(Base):
    __tablename__ = "health_records"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    blood_type: Mapped[str] = mapped_column(String(5), nullable=True)
    allergies: Mapped[str] = mapped_column(String(1000), nullable=True)
    chronic_conditions: Mapped[str] = mapped_column(String(1000), nullable=True)
    emergency_contact_name: Mapped[str] = mapped_column(String(255), nullable=True)
    emergency_contact_phone: Mapped[str] = mapped_column(String(20), nullable=True)
    emergency_contact_relation: Mapped[str] = mapped_column(String(50), nullable=True)
    insurance_info: Mapped[dict] = mapped_column(JSON, nullable=True)
    last_checkup_date: Mapped[date] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=True)


class MedicationSchedule(Base):
    __tablename__ = "medication_schedules"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    medication_name: Mapped[str] = mapped_column(String(255), nullable=False)
    dosage: Mapped[str] = mapped_column(String(100), nullable=False)
    frequency: Mapped[str] = mapped_column(String(100), nullable=False)
    instruction: Mapped[str] = mapped_column(String(50), default="AFTER_MEAL")
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=True)
    parent_notes: Mapped[str] = mapped_column(String(1000), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    request_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=True)


class MedicationLog(Base):
    __tablename__ = "medication_logs"
    __table_args__ = (Index("uq_medication_log_dose", "schedule_id", "scheduled_date", "scheduled_time", unique=True), {"extend_existing": True})

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    schedule_id: Mapped[UUID] = mapped_column(ForeignKey("medication_schedules.id"), nullable=False)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    scheduled_time: Mapped[time] = mapped_column(Time, nullable=False)
    scheduled_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    given_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="SCHEDULED")
    given_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=True)
    notes: Mapped[str] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InfirmaryVisit(Base):
    __tablename__ = "infirmary_visits"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    branch_id: Mapped[UUID] = mapped_column(ForeignKey("branches.id"), nullable=True)
    visit_date: Mapped[date] = mapped_column(Date, nullable=False)
    visit_time: Mapped[time] = mapped_column(Time, nullable=False)
    complaint: Mapped[str] = mapped_column(String(1000), nullable=True)
    temperature: Mapped[float] = mapped_column(Numeric(4, 1), nullable=True)
    blood_pressure_systolic: Mapped[int] = mapped_column(nullable=True)
    blood_pressure_diastolic: Mapped[int] = mapped_column(nullable=True)
    severity: Mapped[str] = mapped_column(String(20), default="LOW")
    treatment_given: Mapped[str] = mapped_column(String(1000), nullable=True)
    follow_up_required: Mapped[bool] = mapped_column(Boolean, default=False)
    follow_up_notes: Mapped[str] = mapped_column(String(1000), nullable=True)
    parent_notified: Mapped[bool] = mapped_column(Boolean, default=False)
    notification_method: Mapped[str] = mapped_column(String(50), nullable=True)
    examined_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
