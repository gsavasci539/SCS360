"""
Live Bus Telemetry Module API
Handles bus routes, stops, telemetry logs, and attendance
"""
from datetime import datetime, date, time
from typing import Optional, List
from uuid import UUID
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_tenant_context
from app.core.responses import success_response
from app.core.security import PermissionChecker, TenantContext
from app.domain.entities import User, Branch

router = APIRouter(prefix="/api/bus", tags=["Bus"])


# ==================== Schemas ====================

class BusRouteCreate(BaseModel):
    branch_id: UUID
    route_name: str = Field(..., max_length=255)
    route_number: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    driver_id: Optional[UUID] = None
    vehicle_plate: Optional[str] = Field(None, max_length=20)
    capacity: int = Field(default=40, ge=1)
    status: str = Field(default="ACTIVE", description="ACTIVE, MAINTENANCE, OUT_OF_SERVICE")

class BusStopCreate(BaseModel):
    route_id: UUID
    stop_name: str = Field(..., max_length=255)
    stop_order: int = Field(..., ge=1)
    latitude: Optional[Decimal] = Field(None, ge=-90, le=90)
    longitude: Optional[Decimal] = Field(None, ge=-180, le=180)
    estimated_arrival: Optional[time] = None

class TelemetryLogCreate(BaseModel):
    route_id: UUID
    latitude: Optional[Decimal] = Field(None, ge=-90, le=90)
    longitude: Optional[Decimal] = Field(None, ge=-180, le=180)
    speed: Optional[Decimal] = Field(None, ge=0, le=200)
    heading: Optional[Decimal] = Field(None, ge=0, le=360)
    ignition_status: bool = Field(default=True)

class BusAttendanceCreate(BaseModel):
    route_id: UUID
    student_id: UUID
    stop_id: Optional[UUID] = None
    attendance_date: date = Field(default_factory=lambda: date.today())
    pickup_time: Optional[time] = None
    dropoff_time: Optional[time] = None
    status: str = Field(default="PRESENT", description="PRESENT, ABSENT, LATE")
    notes: Optional[str] = None


class TransportCheckInCreate(BaseModel):
    route_id: UUID
    student_id: UUID
    event: str = Field(..., description="BOARDED, DROPPED")
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)


# ==================== Bus Routes Endpoints ====================

@router.get("/routes")
async def get_bus_routes(
    branch_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
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
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(BusRoute.route_number).limit(limit).offset(offset)
    
    result = await db.execute(query)
    routes = result.scalars().all()
    
    enriched_routes = []
    for route in routes:
        # Get branch name
        branch_name = None
        if route.branch_id:
            branch_result = await db.execute(
                select(Branch).where(Branch.id == route.branch_id)
            )
            branch = branch_result.scalar_one_or_none()
            if branch:
                branch_name = branch.name
        
        # Get driver name
        driver_name = None
        if route.driver_id:
            driver_result = await db.execute(
                select(User).where(User.id == route.driver_id)
            )
            driver = driver_result.scalar_one_or_none()
            if driver:
                driver_name = f"{driver.first_name} {driver.last_name}"
        
        enriched_routes.append({
            "id": str(route.id),
            "branch_id": str(route.branch_id),
            "branch_name": branch_name,
            "route_name": route.route_name,
            "route_number": route.route_number,
            "description": route.description,
            "driver_id": str(route.driver_id) if route.driver_id else None,
            "driver_name": driver_name,
            "vehicle_plate": route.vehicle_plate,
            "capacity": route.capacity,
            "status": route.status,
            "created_at": route.created_at.isoformat(),
            "updated_at": route.updated_at.isoformat()
        })
    
    return success_response(enriched_routes)


@router.post("/routes")
async def create_bus_route(
    route: BusRouteCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("bus.write"))
):
    """Create a new bus route"""
    from app.domain.entities.bus import BusRoute
    
    new_route = BusRoute(
        branch_id=route.branch_id,
        route_name=route.route_name,
        route_number=route.route_number,
        description=route.description,
        driver_id=route.driver_id,
        vehicle_plate=route.vehicle_plate,
        capacity=route.capacity,
        status=route.status.upper()
    )
    db.add(new_route)
    await db.commit()
    await db.refresh(new_route)
    
    return success_response({
        "id": str(new_route.id),
        "route_name": new_route.route_name,
        "status": new_route.status,
        "created_at": new_route.created_at.isoformat()
    })


@router.put("/routes/{route_id}")
async def update_bus_route(
    route_id: UUID,
    route: BusRouteCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("bus.write"))
):
    """Update a bus route"""
    from app.domain.entities.bus import BusRoute
    
    result = await db.execute(
        select(BusRoute).where(BusRoute.id == route_id)
    )
    existing_route = result.scalar_one_or_none()
    
    if not existing_route:
        raise HTTPException(status_code=404, detail="Route not found")
    
    existing_route.branch_id = route.branch_id
    existing_route.route_name = route.route_name
    existing_route.route_number = route.route_number
    existing_route.description = route.description
    existing_route.driver_id = route.driver_id
    existing_route.vehicle_plate = route.vehicle_plate
    existing_route.capacity = route.capacity
    existing_route.status = route.status.upper()
    
    await db.commit()
    
    return success_response({
        "id": str(existing_route.id),
        "updated_at": existing_route.updated_at.isoformat()
    })


# ==================== Bus Stops Endpoints ====================

@router.get("/stops")
async def get_bus_stops(
    route_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("bus.read"))
):
    """Get bus stops"""
    from app.domain.entities.bus import BusStop
    
    query = select(BusStop)
    
    if route_id:
        query = query.where(BusStop.route_id == route_id)
    
    query = query.order_by(BusStop.stop_order)
    
    result = await db.execute(query)
    stops = result.scalars().all()
    
    enriched_stops = []
    for stop in stops:
        enriched_stops.append({
            "id": str(stop.id),
            "route_id": str(stop.route_id),
            "stop_name": stop.stop_name,
            "stop_order": stop.stop_order,
            "latitude": float(stop.latitude) if stop.latitude else None,
            "longitude": float(stop.longitude) if stop.longitude else None,
            "estimated_arrival": stop.estimated_arrival.strftime("%H:%M") if stop.estimated_arrival else None,
            "created_at": stop.created_at.isoformat()
        })
    
    return success_response(enriched_stops)


@router.post("/stops")
async def create_bus_stop(
    stop: BusStopCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("bus.write"))
):
    """Create a new bus stop"""
    from app.domain.entities.bus import BusStop
    
    new_stop = BusStop(
        route_id=stop.route_id,
        stop_name=stop.stop_name,
        stop_order=stop.stop_order,
        latitude=stop.latitude,
        longitude=stop.longitude,
        estimated_arrival=stop.estimated_arrival
    )
    db.add(new_stop)
    await db.commit()
    await db.refresh(new_stop)
    
    return success_response({
        "id": str(new_stop.id),
        "stop_name": new_stop.stop_name,
        "stop_order": new_stop.stop_order,
        "created_at": new_stop.created_at.isoformat()
    })


# ==================== Telemetry Endpoints ====================

@router.post("/telemetry")
async def submit_telemetry(
    telemetry: TelemetryLogCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("bus.write"))
):
    """Submit bus telemetry data"""
    from app.domain.entities.bus import BusTelemetryLog
    
    new_log = BusTelemetryLog(
        route_id=telemetry.route_id,
        latitude=telemetry.latitude,
        longitude=telemetry.longitude,
        speed=telemetry.speed,
        heading=telemetry.heading,
        ignition_status=telemetry.ignition_status
    )
    db.add(new_log)
    await db.commit()
    await db.refresh(new_log)
    
    # TODO: Check geofence and trigger parent notifications if needed
    
    return success_response({
        "id": str(new_log.id),
        "recorded_at": new_log.recorded_at.isoformat()
    })


@router.get("/telemetry/{route_id}/latest")
async def get_latest_telemetry(
    route_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("bus.read"))
):
    """Get latest telemetry for a route"""
    from app.domain.entities.bus import BusTelemetryLog
    
    result = await db.execute(
        select(BusTelemetryLog).where(
            BusTelemetryLog.route_id == route_id
        ).order_by(BusTelemetryLog.recorded_at.desc()).limit(1)
    )
    telemetry = result.scalar_one_or_none()
    
    if not telemetry:
        raise HTTPException(status_code=404, detail="No telemetry data found")
    
    return success_response({
        "id": str(telemetry.id),
        "route_id": str(telemetry.route_id),
        "latitude": float(telemetry.latitude) if telemetry.latitude else None,
        "longitude": float(telemetry.longitude) if telemetry.longitude else None,
        "speed": float(telemetry.speed) if telemetry.speed else None,
        "heading": float(telemetry.heading) if telemetry.heading else None,
        "ignition_status": telemetry.ignition_status,
        "recorded_at": telemetry.recorded_at.isoformat()
    })


@router.get("/telemetry/{route_id}/history")
async def get_telemetry_history(
    route_id: UUID,
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("bus.read"))
):
    """Get telemetry history for a route"""
    from app.domain.entities.bus import BusTelemetryLog
    
    query = select(BusTelemetryLog).where(BusTelemetryLog.route_id == route_id)
    
    conditions = []
    if start_time:
        conditions.append(BusTelemetryLog.recorded_at >= start_time)
    if end_time:
        conditions.append(BusTelemetryLog.recorded_at <= end_time)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(BusTelemetryLog.recorded_at.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    telemetry_logs = result.scalars().all()
    
    history = []
    for log in telemetry_logs:
        history.append({
            "id": str(log.id),
            "route_id": str(log.route_id),
            "latitude": float(log.latitude) if log.latitude else None,
            "longitude": float(log.longitude) if log.longitude else None,
            "speed": float(log.speed) if log.speed else None,
            "heading": float(log.heading) if log.heading else None,
            "ignition_status": log.ignition_status,
            "recorded_at": log.recorded_at.isoformat()
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
    db: AsyncSession = Depends(get_db),
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
    
    query = query.order_by(BusAttendance.date.desc(), BusAttendance.pickup_time).limit(limit).offset(offset)
    
    result = await db.execute(query)
    attendance_records = result.scalars().all()
    
    enriched_records = []
    for record in attendance_records:
        # Get student name
        student_name = None
        if record.student_id:
            student_result = await db.execute(
                select(Student).where(Student.id == record.student_id)
            )
            student = student_result.scalar_one_or_none()
            if student:
                student_name = f"{student.first_name} {student.last_name}"
        
        enriched_records.append({
            "id": str(record.id),
            "route_id": str(record.route_id),
            "student_id": str(record.student_id),
            "student_name": student_name,
            "stop_id": str(record.stop_id) if record.stop_id else None,
            "date": record.date.isoformat(),
            "pickup_time": record.pickup_time.strftime("%H:%M") if record.pickup_time else None,
            "dropoff_time": record.dropoff_time.strftime("%H:%M") if record.dropoff_time else None,
            "status": record.status,
            "notes": record.notes,
            "created_at": record.created_at.isoformat()
        })
    
    return success_response(enriched_records)


@router.post("/attendance")
async def create_bus_attendance(
    attendance: BusAttendanceCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("bus.write"))
):
    """Create bus attendance record"""
    from app.domain.entities.bus import BusAttendance
    
    # Check if record already exists for this student, route, and date
    existing_result = await db.execute(
        select(BusAttendance).where(
            and_(
                BusAttendance.route_id == attendance.route_id,
                BusAttendance.student_id == attendance.student_id,
                BusAttendance.date == attendance.attendance_date
            )
        )
    )
    existing = existing_result.scalar_one_or_none()
    
    if existing:
        existing.stop_id = attendance.stop_id
        existing.pickup_time = attendance.pickup_time
        existing.dropoff_time = attendance.dropoff_time
        existing.status = attendance.status
        existing.notes = attendance.notes
    else:
        new_attendance = BusAttendance(
            route_id=attendance.route_id,
            student_id=attendance.student_id,
            stop_id=attendance.stop_id,
            date=attendance.attendance_date,
            pickup_time=attendance.pickup_time,
            dropoff_time=attendance.dropoff_time,
            status=attendance.status,
            notes=attendance.notes
        )
        db.add(new_attendance)
    
    await db.commit()
    
    return success_response({
        "message": "Bus attendance recorded successfully",
        "date": attendance.attendance_date.isoformat(),
        "status": attendance.status
    })


@router.get("/routes/{route_id}/students")
async def get_route_students(
    route_id: UUID,
    attendance_date: date = Query(..., description="Date to get students for"),
    db: AsyncSession = Depends(get_db),
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
async def transport_check_in(
    check_in: TransportCheckInCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("bus.write"))
):
    """Process transport check-in (BOARDED/DROPPED) for student"""
    from app.domain.entities.bus import BusAttendance
    from app.domain.entities import Student

    # Verify student exists
    student_result = await db.execute(
        select(Student).where(Student.id == check_in.student_id)
    )
    student = student_result.scalar_one_or_none()

    if not student:
        raise HTTPException(status_code=404, detail="Öğrenci bulunamadı")

    # Get or create attendance record for today
    today = check_in.timestamp.date()
    attendance_result = await db.execute(
        select(BusAttendance).where(
            and_(
                BusAttendance.route_id == check_in.route_id,
                BusAttendance.student_id == check_in.student_id,
                BusAttendance.date == today
            )
        )
    )
    attendance = attendance_result.scalar_one_or_none()

    if not attendance:
        # Create new attendance record
        attendance = BusAttendance(
            route_id=check_in.route_id,
            student_id=check_in.student_id,
            date=today,
            status="PRESENT"
        )
        db.add(attendance)

    # Update based on event type
    if check_in.event.upper() == "BOARDED":
        attendance.pickup_time = check_in.timestamp.time()
        attendance.status = "PRESENT"
    elif check_in.event.upper() == "DROPPED":
        attendance.dropoff_time = check_in.timestamp.time()
    else:
        raise HTTPException(status_code=400, detail="Geçersiz olay türü. BOARDED veya DROPPED olmalı")

    await db.commit()
    await db.refresh(attendance)

    return success_response({
        "route_id": str(attendance.route_id),
        "student_id": str(attendance.student_id),
        "event": check_in.event.upper(),
        "timestamp": check_in.timestamp.isoformat(),
        "pickup_time": attendance.pickup_time.strftime("%H:%M:%S") if attendance.pickup_time else None,
        "dropoff_time": attendance.dropoff_time.strftime("%H:%M:%S") if attendance.dropoff_time else None,
        "status": attendance.status
    }, f"Öğrenci {check_in.event.upper()} olarak işaretlendi")
