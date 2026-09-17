from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import String, DateTime, ForeignKey, Boolean, Integer, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SMSProvider(Base):
    __tablename__ = "sms_providers"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    provider_name: Mapped[str] = mapped_column(String(100), nullable=False)
    api_endpoint: Mapped[str] = mapped_column(String(500), nullable=True)
    api_key_encrypted: Mapped[str] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class BroadcastJob(Base):
    __tablename__ = "broadcast_jobs"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message_content: Mapped[str] = mapped_column(nullable=True)
    target_audience: Mapped[str] = mapped_column(String(50), nullable=False)
    target_class_id: Mapped[UUID] = mapped_column(ForeignKey("classes.id"), nullable=True)
    target_branch_id: Mapped[UUID] = mapped_column(ForeignKey("branches.id"), nullable=True)
    channel: Mapped[str] = mapped_column(String(50), default="SMS")
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    total_recipients: Mapped[int] = mapped_column(Integer, default=0)
    sent_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)


class DeliveryReport(Base):
    __tablename__ = "delivery_reports"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    broadcast_job_id: Mapped[UUID] = mapped_column(ForeignKey("broadcast_jobs.id"), nullable=False)
    recipient_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    recipient_name: Mapped[str] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    provider_response: Mapped[str] = mapped_column(String(1000), nullable=True)
    error_message: Mapped[str] = mapped_column(String(1000), nullable=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
