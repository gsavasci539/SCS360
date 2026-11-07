"""
Live Bus Telemetry Module API
Handles bus routes, stops, telemetry logs, and attendance
"""
from __future__ import annotations
from app.core.dates import school_today, school_datetime
from datetime import UTC, datetime, date, time
from typing import Literal, Optional, List
from uuid import UUID, uuid4
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_tenant_context
from app.core.responses import success_response
from app.core.permissions import PermissionChecker
from app.core.tenant import TenantContext
from app.domain.entities import User, Branch
from app.application.services import bus_service

router = APIRouter(prefix="/api/bus", tags=["Bus"])


# ==================== Schemas ====================

class BusRouteCreate(BaseModel):
    branch_id: UUID
    route_name: str = Field(..., min_length=1, max_length=255)
    route_number: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=1000)
    driver_id: Optional[UUID] = None
    vehicle_plate: Optional[str] = Field(None, max_length=20)
    capacity: int = Field(default=40, ge=1, le=2147483647)
    status: Literal["ACTIVE", "MAINTENANCE", "OUT_OF_SERVICE"] = "ACTIVE"
    request_id: UUID = Field(default_factory=uuid4, description="Aynı oluşturma işlemi tekrarında aynı UUID")
    expected_updated_at: Optional[datetime] = None

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value):
        return value.upper() if isinstance(value, str) else value

    @field_validator("route_name")
    @classmethod
    def nonblank_name(cls, value):
        if not value.strip():
            raise ValueError("Rota adı boş olamaz")
        return value

class BusStopCreate(BaseModel):
    route_id: UUID
    stop_name: str = Field(..., min_length=1, max_length=255)
    stop_order: int = Field(..., ge=1, le=2147483647)
    latitude: Optional[Decimal] = Field(None, ge=-90, le=90)
    longitude: Optional[Decimal] = Field(None, ge=-180, le=180)
    estimated_arrival: Optional[time] = None
    request_id: UUID = Field(default_factory=uuid4, description="Aynı oluşturma işlemi tekrarında aynı UUID")

    @field_validator("estimated_arrival")
    @classmethod
    def local_clock(cls, value):
        if value is not None and value.tzinfo is not None:
            raise ValueError("Durak saati okul yerel saati olarak girilmeli")
        return value

class TelemetryLogCreate(BaseModel):
    route_id: UUID
    latitude: Optional[Decimal] = Field(None, ge=-90, le=90)
    longitude: Optional[Decimal] = Field(None, ge=-180, le=180)
    speed: Optional[Decimal] = Field(None, ge=0, le=200)
    heading: Optional[Decimal] = Field(None, ge=0, le=360)
    ignition_status: bool = Field(default=True)
    request_id: UUID = Field(default_factory=uuid4, description="Aynı konum kaydı tekrarında aynı UUID")

class BusAttendanceCreate(BaseModel):
    route_id: UUID
    student_id: UUID
    stop_id: Optional[UUID] = None
    attendance_date: date = Field(default_factory=lambda: school_today())
    pickup_time: Optional[time] = None
    dropoff_time: Optional[time] = None
    status: Literal["PRESENT", "ABSENT", "LATE"] = "PRESENT"
    notes: Optional[str] = Field(None, max_length=500)

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value):
        return value.upper() if isinstance(value, str) else value

    @field_validator("pickup_time", "dropoff_time")
    @classmethod
    def local_clock(cls, value):
        if value is not None and value.tzinfo is not None:
            raise ValueError("Biniş/iniş saati okul yerel saati olarak girilmeli")
        return value


class TransportCheckInCreate(BaseModel):
    route_id: UUID
    student_id: UUID
    event: Literal["BOARDED", "DROPPED"]
    request_id: UUID = Field(default_factory=uuid4, description="Aynı biniş/iniş tekrarında aynı UUID")
    timestamp: datetime = Field(default_factory=lambda: school_datetime(datetime.now(UTC)),
        description="Saat dilimli zaman okul saatine çevrilir; saat dilimi yoksa okul yerel saati kabul edilir.")

    @field_validator("event", mode="before")
    @classmethod
    def normalize_event(cls, value):
        return value.upper() if isinstance(value, str) else value


# ==================== Bus Routes Endpoints ====================

@router.get("/routes")
async def get_bus_routes(
    branch_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    search: str = Query("", max_length=100),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("bus.read"))
):
    """Get bus routes with filtering"""
    from app.domain.entities.bus import BusRoute
    
    query = select(BusRoute)
    
    conditions = []
    if branch_id:
        conditions.append(BusRoute.branch_id == branch_id)
    if status:
        conditions.append(BusRoute.status == status.upper())
    if search.strip():
        from sqlalchemy import or_
        conditions.append(or_(BusRoute.route_name.ilike(f"%{search.strip()}%"), BusRoute.vehicle_plate.ilike(f"%{search.strip()}%")))
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(BusRoute.route_number, BusRoute.id).limit(limit).offset(offset)
    
    result = await db.execute(query)
    routes = result.scalars().all()
    
    return success_response(await bus_service.route_rows(db, routes))


@router.get("/options")
async def bus_options(branch_id: Optional[UUID] = None, route_id: Optional[UUID] = None, student_id: Optional[UUID] = None,
    search: str = Query("", max_length=100), db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("bus.read"))):
    return success_response(await bus_service.options(db, branch_id, route_id, student_id, search.strip()))


@router.get("/summary")
async def bus_summary(route_id: Optional[UUID] = None, attendance_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db, scope="function"), tenant: TenantContext = Depends(PermissionChecker("bus.read"))):
    return success_response(await bus_service.summary(db, route_id, attendance_date))


@router.get("/routes/{route_id}")
async def bus_route(route_id: UUID, db: AsyncSession = Depends(get_db, scope="function"), tenant: TenantContext = Depends(PermissionChecker("bus.read"))):
    return success_response((await bus_service.route_rows(db, [await bus_service.route(db, route_id)]))[0])


@router.post("/routes")
async def create_bus_route(route: BusRouteCreate, db: AsyncSession = Depends(get_db, scope="function"), tenant: TenantContext = Depends(PermissionChecker("bus.write"))):
    return success_response(await bus_service.create_route(db, tenant, route))


@router.put("/routes/{route_id}")
async def update_bus_route(route_id: UUID, route: BusRouteCreate, db: AsyncSession = Depends(get_db, scope="function"), tenant: TenantContext = Depends(PermissionChecker("bus.write"))):
    return success_response(await bus_service.update_route(db, tenant, route_id, route))


# ==================== Bus Stops Endpoints ====================

@router.get("/stops")
async def get_bus_stops(
    route_id: Optional[UUID] = Query(None),
    limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("bus.read"))
):
    """Get bus stops"""
    from app.domain.entities.bus import BusStop
    
    query = select(BusStop)
    
    if route_id:
        query = query.where(BusStop.route_id == route_id)
    
    query = query.order_by(BusStop.stop_order, BusStop.id).limit(limit).offset(offset)
    
    result = await db.execute(query)
    stops = result.scalars().all()
    
    enriched_stops = []
    for stop in stops:
        enriched_stops.append({
            "id": str(stop.id),
            "route_id": str(stop.route_id),
            "stop_name": stop.stop_name,
            "stop_order": stop.stop_order,
            "latitude": float(stop.latitude) if stop.latitude is not None else None,
            "longitude": float(stop.longitude) if stop.longitude is not None else None,
            "estimated_arrival": stop.estimated_arrival.strftime("%H:%M") if stop.estimated_arrival else None,
            "created_at": bus_service.iso(stop.created_at)
        })
    
    return success_response(enriched_stops)


@router.post("/stops")
async def create_bus_stop(stop: BusStopCreate, db: AsyncSession = Depends(get_db, scope="function"), tenant: TenantContext = Depends(PermissionChecker("bus.write"))):
    return success_response(await bus_service.create_stop(db, tenant, stop))


@router.put("/stops/{stop_id}")
async def update_bus_stop(stop_id: UUID, stop: BusStopCreate, db: AsyncSession = Depends(get_db, scope="function"), tenant: TenantContext = Depends(PermissionChecker("bus.write"))):
    return success_response(await bus_service.update_stop(db, tenant, stop_id, stop))


# ==================== Telemetry Endpoints ====================

@router.post("/telemetry")
async def submit_telemetry(telemetry: TelemetryLogCreate, db: AsyncSession = Depends(get_db, scope="function"), tenant: TenantContext = Depends(PermissionChecker("bus.write"))):
    return success_response(await bus_service.create_telemetry(db, tenant, telemetry))


@router.get("/telemetry/{route_id}/latest")
async def get_latest_telemetry(
    route_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("bus.read"))
):
    """Get latest telemetry for a route, or an empty result."""
    await bus_service.route(db, route_id)
    from app.domain.entities.bus import BusTelemetryLog
    
    result = await db.execute(
        select(BusTelemetryLog).where(
            BusTelemetryLog.route_id == route_id
        ).order_by(BusTelemetryLog.recorded_at.desc(), BusTelemetryLog.id.desc()).limit(1)
    )
    telemetry = result.scalar_one_or_none()
    
    if not telemetry:
        return success_response(None)
    
    return success_response({
        "id": str(telemetry.id),
        "route_id": str(telemetry.route_id),
        "latitude": float(telemetry.latitude) if telemetry.latitude is not None else None,
        "longitude": float(telemetry.longitude) if telemetry.longitude is not None else None,
        "speed": float(telemetry.speed) if telemetry.speed is not None else None,
        "heading": float(telemetry.heading) if telemetry.heading is not None else None,
        "ignition_status": telemetry.ignition_status,
        "recorded_at": bus_service.iso(telemetry.recorded_at)
    })


@router.get("/telemetry/{route_id}/history")
async def get_telemetry_history(
    route_id: UUID,
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("bus.read"))
):
    """Get telemetry history for a route"""
    await bus_service.route(db, route_id)
    start_time = bus_service.utc(start_time) if start_time else None
    end_time = bus_service.utc(end_time) if end_time else None
    if start_time and end_time and start_time > end_time:
        raise HTTPException(422, "Başlangıç bitişten sonra olamaz")
    from app.domain.entities.bus import BusTelemetryLog
    
    query = select(BusTelemetryLog).where(BusTelemetryLog.route_id == route_id)
    
    conditions = []
    if start_time:
        conditions.append(BusTelemetryLog.recorded_at >= start_time)
    if end_time:
        conditions.append(BusTelemetryLog.recorded_at <= end_time)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(BusTelemetryLog.recorded_at.desc(), BusTelemetryLog.id.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    telemetry_logs = result.scalars().all()
    
    history = []
    for log in telemetry_logs:
        history.append({
            "id": str(log.id),
            "route_id": str(log.route_id),
            "latitude": float(log.latitude) if log.latitude is not None else None,
            "longitude": float(log.longitude) if log.longitude is not None else None,
            "speed": float(log.speed) if log.speed is not None else None,
            "heading": float(log.heading) if log.heading is not None else None,
            "ignition_status": log.ignition_status,
            "recorded_at": bus_service.iso(log.recorded_at)
        })
    
    return success_response(history)


# ==================== Bus Attendance Endpoints ====================

@router.get("/attendance")
async def get_bus_attendance(
    route_id: Optional[UUID] = Query(None),
    student_id: Optional[UUID] = Query(None),
    attendance_date: Optional[date] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("bus.read"))
):
    """Get bus attendance records"""
    from app.domain.entities.bus import BusAttendance
    from app.domain.entities import Student
    
    query = select(BusAttendance)
    
    conditions = []
    if route_id:
        conditions.append(BusAttendance.route_id == route_id)
    if student_id:
        conditions.append(BusAttendance.student_id == student_id)
    if attendance_date:
        conditions.append(BusAttendance.date == attendance_date)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(BusAttendance.date.desc(), BusAttendance.pickup_time, BusAttendance.id).limit(limit).offset(offset)
    
    result = await db.execute(query)
    attendance_records = result.scalars().all()
    
    return success_response(await bus_service.attendance_rows(db, attendance_records))


@router.post("/attendance")
async def create_bus_attendance(attendance: BusAttendanceCreate, db: AsyncSession = Depends(get_db, scope="function"), tenant: TenantContext = Depends(PermissionChecker("bus.write"))):
    return success_response(await bus_service.record_attendance(db, tenant, attendance))


@router.get("/routes/{route_id}/students")
async def get_route_students(
    route_id: UUID,
    attendance_date: date = Query(..., description="Date to get students for"),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("bus.read"))
):
    """Get students assigned to a route with their attendance status"""
    from app.domain.entities.bus import BusAttendance
    from app.domain.entities import Student


    # This is a simplified version - in real app would have a route_students table
    # For now, we'll get all students with attendance for this route on the given date
    result = await db.execute(
        select(BusAttendance).where(
            and_(
                BusAttendance.route_id == route_id,
                BusAttendance.date == attendance_date
            )
        )
    )
    attendance_records = result.scalars().all()

    students = []
    for record in attendance_records:
        student_result = await db.execute(
            select(Student).where(Student.id == record.student_id)
        )
        student = student_result.scalar_one_or_none()

        if student:
            students.append({
                "student_id": str(student.id),
                "student_name": f"{student.first_name} {student.last_name}",
                "student_number": student.student_number,
                "pickup_time": record.pickup_time.strftime("%H:%M") if record.pickup_time else None,
                "dropoff_time": record.dropoff_time.strftime("%H:%M") if record.dropoff_time else None,
                "status": record.status,
                "notes": record.notes
            })

    return success_response(students)


@router.post("/check-in")
async def transport_check_in(check_in: TransportCheckInCreate, db: AsyncSession = Depends(get_db, scope="function"), tenant: TenantContext = Depends(PermissionChecker("bus.write"))):
    return success_response(await bus_service.check_in(db, tenant, check_in))
