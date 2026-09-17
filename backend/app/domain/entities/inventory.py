from datetime import datetime, date
from uuid import UUID, uuid4
from decimal import Decimal

from sqlalchemy import String, DateTime, Date, ForeignKey, Boolean, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class InventoryItem(Base):
    __tablename__ = "inventory_items"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    branch_id: Mapped[UUID] = mapped_column(ForeignKey("branches.id"), nullable=False)
    item_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=True)
    description: Mapped[str] = mapped_column(nullable=True)
    purchase_date: Mapped[date] = mapped_column(Date, nullable=True)
    purchase_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=True)
    current_value: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=True)
    location_id: Mapped[UUID] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    condition: Mapped[str] = mapped_column(String(50), nullable=True)
    qr_code: Mapped[str] = mapped_column(String(255), nullable=True)
    barcode: Mapped[str] = mapped_column(String(255), nullable=True)
    warranty_expiry: Mapped[date] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class InventoryLocation(Base):
    __tablename__ = "inventory_locations"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    branch_id: Mapped[UUID] = mapped_column(ForeignKey("branches.id"), nullable=False)
    location_name: Mapped[str] = mapped_column(String(255), nullable=False)
    location_type: Mapped[str] = mapped_column(String(50), nullable=True)
    description: Mapped[str] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AssetAssignment(Base):
    __tablename__ = "asset_assignments"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    item_id: Mapped[UUID] = mapped_column(ForeignKey("inventory_items.id"), nullable=False)
    assigned_to: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    assigned_date: Mapped[date] = mapped_column(Date, nullable=False)
    return_date: Mapped[date] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="ASSIGNED")
    notes: Mapped[str] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MaintenanceRequest(Base):
    __tablename__ = "maintenance_requests"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    item_id: Mapped[UUID] = mapped_column(ForeignKey("inventory_items.id"), nullable=False)
    reported_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    issue_description: Mapped[str] = mapped_column(nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="MEDIUM")
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    assigned_to: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=True)
    resolved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_notes: Mapped[str] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
