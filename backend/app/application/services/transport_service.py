from app.core.dates import school_today
from datetime import date, datetime

from sqlalchemy import select

from app.application.services.operations_service import identifier
from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.student_access import require_student_access
from app.domain.entities.bus import BusRoute, BusTelemetryLog, BusAttendance
from app.infrastructure.models.models import Branch, Student
from app.infrastructure.repositories.base import BaseRepository


def query(tenant):
    repo = BaseRepository(None, tenant)
    return repo._branch_filter(repo._org_filter(select(BusRoute).join(Branch, Branch.id == BusRoute.branch_id), Branch), BusRoute)


async def get(db, tenant, route_id):
    row = (await db.execute(query(tenant).where(BusRoute.id == identifier(route_id)))).scalar_one_or_none()
    if row is None:
        raise NotFoundException("Güzergah bulunamadı")
    return row


async def serialize(db, row):
    telemetry = (await db.execute(select(BusTelemetryLog).where(BusTelemetryLog.route_id == row.id)
        .order_by(BusTelemetryLog.recorded_at.desc()).limit(1))).scalar_one_or_none()
    entries = (await db.execute(select(BusAttendance, Student).join(Student, Student.id == BusAttendance.student_id)
        .where(BusAttendance.route_id == row.id, BusAttendance.date == school_today()))).all()
    return {"id": str(row.id), "route_id": str(row.id), "branch_id": str(row.branch_id), "route_name": row.route_name,
        "plate_number": row.vehicle_plate, "vehicle_plate": row.vehicle_plate, "driver_name": row.driver_name,
        "driver_phone": row.driver_phone, "hostess_name": row.hostess_name, "hostess_phone": row.hostess_phone,
        "capacity": row.capacity, "status": row.status,
        "current_lat": float(telemetry.latitude) if telemetry and telemetry.latitude is not None else None,
        "current_lng": float(telemetry.longitude) if telemetry and telemetry.longitude is not None else None,
        "speed_kmh": float(telemetry.speed) if telemetry and telemetry.speed is not None else None,
        "students": [{"student_id": str(student.id), "student_name": f"{student.first_name} {student.last_name}",
            "is_morning_boarded": attendance.pickup_time is not None, "is_evening_boarded": attendance.dropoff_time is not None}
            for attendance, student in entries]}


async def records(db, tenant, branch_id=None):
    statement = query(tenant)
    if branch_id:
        statement = statement.where(BusRoute.branch_id == identifier(branch_id))
    return [await serialize(db, row) for row in (await db.execute(statement)).scalars()]


async def create(db, tenant, body):
    branch = await BaseRepository(db, tenant).get_by_id(identifier(body.branch_id), Branch)
    route = BusRoute(branch_id=branch.id, route_name=body.route_name, vehicle_plate=body.plate_number,
        driver_name=body.driver_name, driver_phone=body.driver_phone, hostess_name=body.hostess_name,
        hostess_phone=body.hostess_phone)
    db.add(route); await db.flush()
    return await serialize(db, route)


async def telemetry(db, tenant, route_id, body):
    route = await get(db, tenant, route_id)
    from app.core.exceptions import ValidationException
    if not -90 <= body.current_lat <= 90 or not -180 <= body.current_lng <= 180 or body.speed_kmh < 0:
        raise ValidationException("Telemetri koordinatları veya hız değeri geçersiz")
    db.add(BusTelemetryLog(route_id=route.id, latitude=body.current_lat, longitude=body.current_lng, speed=body.speed_kmh))
    await db.flush()
    return await serialize(db, route)


async def checkin(db, tenant, route_id, student_id, is_morning=True, is_boarded=True, timestamp=None):
    route = await get(db, tenant, route_id)
    student = await BaseRepository(db, tenant).get_by_id(identifier(student_id), Student)
    await require_student_access(db, tenant, student.id)
    if student.branch_id != route.branch_id:
        raise ForbiddenException("Öğrenci güzergahın şubesine ait değil")
    now = timestamp or datetime.now()
    row = (await db.execute(select(BusAttendance).where(BusAttendance.route_id == route.id,
        BusAttendance.student_id == student.id, BusAttendance.date == now.date()))).scalars().first()
    if row is None:
        row = BusAttendance(route_id=route.id, student_id=student.id, date=now.date())
        db.add(row)
    setattr(row, "pickup_time" if is_morning else "dropoff_time", now.time() if is_boarded else None)
    await db.flush()
    return {"id": str(row.id), "attendance_id": str(row.id), "student_id": str(student.id), "route_id": str(route.id),
        "event": "BOARDED" if is_morning else "DROPPED", "timestamp": now.isoformat()}
