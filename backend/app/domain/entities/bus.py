from datetime import datetime, date, time
from uuid import UUID, uuid4
from decimal import Decimal

from sqlalchemy import String, DateTime, Date, Time, ForeignKey, Boolean, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class BusRoute(Base):
    __tablename__ = "bus_routes"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    branch_id: Mapped[UUID] = mapped_column(ForeignKey("branches.id"), nullable=False)
    route_name: Mapped[str] = mapped_column(String(255), nullable=False)
    route_number: Mapped[str] = mapped_column(String(50), nullable=True)
    description: Mapped[str] = mapped_column(String(1000), nullable=True)
    driver_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=True)
    vehicle_plate: Mapped[str] = mapped_column(String(20), nullable=True)
    capacity: Mapped[int] = mapped_column(Integer, default=40)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=True)


class BusStop(Base):
    __tablename__ = "bus_stops"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    route_id: Mapped[UUID] = mapped_column(ForeignKey("bus_routes.id"), nullable=False)
    stop_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stop_order: Mapped[int] = mapped_column(Integer, nullable=False)
    latitude: Mapped[Decimal] = mapped_column(Numeric(10, 8), nullable=True)
    longitude: Mapped[Decimal] = mapped_column(Numeric(11, 8), nullable=True)
    estimated_arrival: Mapped[time] = mapped_column(Time, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BusTelemetryLog(Base):
    __tablename__ = "bus_telemetry_logs"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    route_id: Mapped[UUID] = mapped_column(ForeignKey("bus_routes.id"), nullable=False)
    latitude: Mapped[Decimal] = mapped_column(Numeric(10, 8), nullable=True)
    longitude: Mapped[Decimal] = mapped_column(Numeric(11, 8), nullable=True)
    speed: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=True)
    heading: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=True)
    ignition_status: Mapped[bool] = mapped_column(Boolean, default=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BusAttendance(Base):
    __tablename__ = "bus_attendance"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    route_id: Mapped[UUID] = mapped_column(ForeignKey("bus_routes.id"), nullable=False)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    stop_id: Mapped[UUID] = mapped_column(ForeignKey("bus_stops.id"), nullable=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    pickup_time: Mapped[time] = mapped_column(Time, nullable=True)
    dropoff_time: Mapped[time] = mapped_column(Time, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="PRESENT")
    notes: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
