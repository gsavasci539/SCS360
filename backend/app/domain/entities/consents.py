from datetime import datetime, date
from uuid import UUID, uuid4

from sqlalchemy import String, DateTime, Date, ForeignKey, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ConsentDocument(Base):
    __tablename__ = "consent_documents"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(nullable=True)
    version: Mapped[str] = mapped_column(String(20), default="1.0")
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class StudentConsent(Base):
    __tablename__ = "student_consents"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    consent_document_id: Mapped[UUID] = mapped_column(ForeignKey("consent_documents.id"), nullable=False)
    parent_id: Mapped[UUID] = mapped_column(ForeignKey("parents.id"), nullable=True)
    consent_status: Mapped[str] = mapped_column(String(20), default="PENDING")
    consent_method: Mapped[str] = mapped_column(String(50), nullable=True)
    consented_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str] = mapped_column(nullable=True)
    signature_data: Mapped[str] = mapped_column(nullable=True)
    notes: Mapped[str] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
