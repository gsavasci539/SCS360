from datetime import datetime, date
from uuid import UUID, uuid4

from sqlalchemy import String, DateTime, Date, ForeignKey, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PickupAuthorization(Base):
    __tablename__ = "pickup_authorizations"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    authorized_person_name: Mapped[str] = mapped_column(String(255), nullable=False)
    authorized_person_id: Mapped[str] = mapped_column(String(50), nullable=True)
    relationship: Mapped[str] = mapped_column(String(100), nullable=True)
    photo_url: Mapped[str] = mapped_column(String(500), nullable=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=True)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    notes: Mapped[str] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=True)


class PickupLog(Base):
    __tablename__ = "pickup_logs"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    authorization_id: Mapped[UUID] = mapped_column(ForeignKey("pickup_authorizations.id"), nullable=True)
    pickup_person_name: Mapped[str] = mapped_column(String(255), nullable=False)
    pickup_person_id: Mapped[str] = mapped_column(String(50), nullable=True)
    verified_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    pickup_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    verification_method: Mapped[str] = mapped_column(String(50), default="ID_CARD")
    notes: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
