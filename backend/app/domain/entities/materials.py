from datetime import datetime, date
from uuid import UUID, uuid4

from sqlalchemy import String, DateTime, Date, ForeignKey, Boolean, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CourseMaterial(Base):
    __tablename__ = "course_materials"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    class_id: Mapped[UUID] = mapped_column(ForeignKey("classes.id"), nullable=True)
    subject_id: Mapped[UUID] = mapped_column(nullable=True)
    teacher_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=True)
    material_type: Mapped[str] = mapped_column(String(20), nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=True)
    unit_topic: Mapped[str] = mapped_column(String(255), nullable=True)
    visibility: Mapped[str] = mapped_column(String(20), default="CLASS_ONLY")
    visible_from: Mapped[date] = mapped_column(Date, nullable=True)
    visible_until: Mapped[date] = mapped_column(Date, nullable=True)
    download_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=True)
