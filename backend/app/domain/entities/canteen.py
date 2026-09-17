from datetime import datetime, date, time
from uuid import UUID, uuid4

from sqlalchemy import String, DateTime, Date, Time, ForeignKey, Boolean, Integer, Numeric, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CanteenProduct(Base):
    __tablename__ = "canteen_products"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    branch_id: Mapped[UUID] = mapped_column(ForeignKey("branches.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=True)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    image_url: Mapped[str] = mapped_column(String(500), nullable=True)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    allergens: Mapped[list] = mapped_column(JSON, default=list)
    nutritional_info: Mapped[dict] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=True)


class CanteenDietaryRestriction(Base):
    __tablename__ = "canteen_dietary_restrictions"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    restriction: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=True)


class CanteenOrder(Base):
    __tablename__ = "canteen_orders"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    branch_id: Mapped[UUID] = mapped_column(ForeignKey("branches.id"), nullable=True)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("canteen_products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    total_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="COMPLETED")
    payment_method: Mapped[str] = mapped_column(String(50), nullable=True)
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    order_time: Mapped[time] = mapped_column(Time, nullable=False)
    processed_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=True)
    notes: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CanteenWalletTransaction(Base):
    __tablename__ = "canteen_wallet_transactions"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)  # CREDIT or DEBIT
    payment_method: Mapped[str] = mapped_column(String(50), nullable=True)
    reference_number: Mapped[str] = mapped_column(String(100), nullable=True)
    processed_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="COMPLETED")
    notes: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
