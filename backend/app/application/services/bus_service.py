"""Validate transport references before writing and summarize scoped records."""
from datetime import UTC, datetime
import hashlib
import json
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError

from app.core.dates import school_datetime
from app.domain.entities.bus import BusRoute, BusStop, BusTelemetryLog, BusAttendance
from app.infrastructure.models.models import AuditAction, AuditLog, Branch, Student, User


async def route(db, route_id):
    row = (await db.execute(select(BusRoute).where(BusRoute.id == route_id))).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "Servis rotası bulunamadı")
    return row


async def route_owner(db, branch_id, driver_id):
    branch = (await db.execute(select(Branch).where(Branch.id == branch_id, Branch.deleted_at.is_(None)))).scalar_one_or_none()
    if branch is None:
        raise HTTPException(404, "Şube bulunamadı")
    if driver_id is not None:
        # Compare ownership even for root. Core avoids hiding a corrupt foreign link.
        table = User.__table__
        driver = (await db.execute(select(table.c.organization_id, table.c.status, table.c.deleted_at).where(table.c.id == driver_id))).first()
        if driver is None or driver.organization_id != branch.organization_id or driver.status != "ACTIVE" or driver.deleted_at is not None:
            raise HTTPException(403, "Sürücü rota kurumuna ait aktif bir hesap olmalı")
        visible = (await db.execute(select(User.id).where(User.id == driver_id))).scalar_one_or_none()
        if visible is None:
            assigned = (await db.execute(select(BusRoute.id).join(Branch, Branch.id == BusRoute.branch_id).where(
                BusRoute.driver_id == driver_id, Branch.organization_id == branch.organization_id).limit(1))).scalar_one_or_none()
            if assigned is None:
                raise HTTPException(403, "Sürücü erişim kapsamı dışında")
    return branch


async def route_rows(db, routes):
    if not routes:
        return []
    branches = {row.id: row for row in (await db.execute(select(Branch).where(Branch.id.in_({route.branch_id for route in routes})))).scalars()}
    table = User.__table__
    ids = {route.driver_id for route in routes if route.driver_id is not None}
    drivers = {row.id: row for row in (await db.execute(select(table.c.id, table.c.organization_id, table.c.first_name,
        table.c.last_name, table.c.deleted_at).where(table.c.id.in_(ids)))).all()} if ids else {}
    result = []
    for route in routes:
        branch = branches.get(route.branch_id)
        driver = drivers.get(route.driver_id)
        # A route assignment permits this minimal name, not global staff/payroll
        # access. Never expose a corrupt link to a foreign institution's user.
        name = f"{driver.first_name} {driver.last_name}" if driver and branch and driver.organization_id == branch.organization_id and driver.deleted_at is None else None
        result.append({"id": str(route.id), "branch_id": str(route.branch_id), "branch_name": branch.name if branch else None,
            "route_name": route.route_name, "route_number": route.route_number, "description": route.description,
            "driver_id": str(route.driver_id) if route.driver_id else None, "driver_name": name,
            "vehicle_plate": route.vehicle_plate, "capacity": route.capacity, "status": route.status,
            "created_at": iso(route.created_at), "updated_at": iso(route.updated_at)})
    return result


async def attendance_references(db, route_id, student_id, stop_id=None):
    selected = await lock_route(db, route_id)
    branch = await route_owner(db, selected.branch_id, None)
    child = (await db.execute(select(Student).where(Student.id == student_id, Student.deleted_at.is_(None)))).scalar_one_or_none()
    if child is None:
        raise HTTPException(404, "Öğrenci bulunamadı")
    if child.organization_id != branch.organization_id:
        raise HTTPException(403, "Öğrenci ve rota aynı kuruma ait olmalı")
    if stop_id is not None:
        stop = (await db.execute(select(BusStop).where(BusStop.id == stop_id, BusStop.route_id == selected.id))).scalar_one_or_none()
        if stop is None:
            raise HTTPException(403, "Durak seçilen rotaya ait değil")
    # Lock an already authorized child before the first attendance lookup. This
    # serializes first inserts on SQLite and PostgreSQL without changing history.
    table = Student.__table__
    await db.execute(table.update().where(table.c.id == child.id).values(updated_at=table.c.updated_at))


async def summary(db, route_id=None, attendance_date=None):
    routes = select(func.count(BusRoute.id), func.sum(case((BusRoute.status == "ACTIVE", 1), else_=0)), func.sum(BusRoute.capacity))
    attendance = select(func.count(BusAttendance.id), func.count(func.distinct(BusAttendance.student_id)),
        func.sum(case((BusAttendance.status.in_(["PRESENT", "LATE"]), 1), else_=0)))
    if route_id:
        await route(db, route_id)
        routes = routes.where(BusRoute.id == route_id)
        attendance = attendance.where(BusAttendance.route_id == route_id)
    if attendance_date:
        attendance = attendance.where(BusAttendance.date == attendance_date)
    total, active, capacity = (await db.execute(routes)).one()
    records, students, present = (await db.execute(attendance)).one()
    return {"total_routes": total, "active_routes": active or 0, "total_capacity": capacity or 0,
        "total_students": students, "attendance_records": records,
        "attendance_rate": round(present * 100 / records, 2) if records else None,
        "attendance_basis": "RECORDED_ATTENDANCE", "recommendations": []}


def utc(value):
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def iso(value):
    return utc(value).isoformat() if value else None


async def lock_route(db, identifier):
    await route(db, identifier)
    table = BusRoute.__table__
    await db.execute(table.update().where(table.c.id == identifier).values(updated_at=table.c.updated_at))
    selected = (await db.execute(select(BusRoute).where(BusRoute.id == identifier).execution_options(populate_existing=True))).scalar_one_or_none()
    if selected is None:
        raise HTTPException(404, "Servis rotası bulunamadı")
    return selected


def fingerprint(body):
    values = body.model_dump(mode="json", exclude={"request_id"})
    if values.get("expected_version") is None:
        values.pop("expected_version", None)
    if "timestamp" in values and "timestamp" not in body.model_fields_set:
        values.pop("timestamp")
    return hashlib.sha256(json.dumps(values, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


async def cached(db, tenant, body, event, *, entity_id=None):
    previous = (await db.execute(select(AuditLog).where(AuditLog.id == body.request_id))).scalar_one_or_none()
    if previous:
        values = previous.new_values or {}
        if previous.user_id != tenant.user_id or values.get("event") != event or values.get("payload_hash") != fingerprint(body) or (entity_id is not None and previous.entity_id != entity_id):
            raise HTTPException(409, "İstek kimliği başka bir işlemde kullanılmış")
        return values["response"]
    table = AuditLog.__table__
    if (await db.execute(select(table.c.id).where(table.c.id == body.request_id))).first():
        raise HTTPException(409, "İstek kimliği kullanılamıyor")
    return None


def audit(db, tenant, branch, entity_type, identifier, event, values, body=None):
    db.add(AuditLog(id=body.request_id if body else uuid4(), organization_id=branch.organization_id, branch_id=branch.id,
        user_id=tenant.user_id, action=AuditAction.CREATE if body else AuditAction.UPDATE,
        entity_type=entity_type, entity_id=identifier,
        new_values={"event": event, **({"payload_hash": fingerprint(body), "response": values} if body else values)}))


async def commit(db):
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "İstek kimliği kullanılmış; yeni işlem başlatın") from None


async def insert(db, tenant, branch, model, body, event, values, response):
    old = await cached(db, tenant, body, event)
    if old is not None:
        return old
    table = model.__table__
    if (await db.execute(select(table.c.id).where(table.c.id == body.request_id))).first():
        raise HTTPException(409, "İstek kimliği kullanılamıyor")
    row = model(id=body.request_id, **values)
    db.add(row)
    try:
        await db.flush()
        await db.refresh(row)
        result = response(row)
        audit(db, tenant, branch, model.__tablename__, row.id, event, result, body)
        await commit(db)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "İstek kimliği kullanılmış; yeni işlem başlatın") from None
    return result


async def create_route(db, tenant, body):
    branch = await route_owner(db, body.branch_id, body.driver_id)
    table = Branch.__table__
    await db.execute(table.update().where(table.c.id == branch.id).values(updated_at=table.c.updated_at))
    return await insert(db, tenant, branch, BusRoute, body, "BUS_ROUTE_CREATED",
        {**body.model_dump(exclude={"request_id", "expected_updated_at"}), "updated_by": tenant.user_id},
        lambda row: {"id": str(row.id), "route_name": row.route_name, "status": row.status, "created_at": iso(row.created_at)})


async def update_route(db, tenant, identifier, body):
    selected = await lock_route(db, identifier)
    branch = await route_owner(db, body.branch_id, body.driver_id)
    original_branch = await route_owner(db, selected.branch_id, None)
    if original_branch.organization_id != branch.organization_id:
        raise HTTPException(403, "Rota başka kuruma taşınamaz")
    previous = await cached(db, tenant, body, "BUS_ROUTE_UPDATED", entity_id=selected.id)
    if previous is not None:
        return previous
    if branch.id != original_branch.id:
        for model in (BusStop, BusTelemetryLog, BusAttendance):
            if (await db.execute(select(model.id).where(model.route_id == selected.id).limit(1))).first():
                raise HTTPException(409, "Geçmişi olan rota başka şubeye taşınamaz")
    if body.expected_updated_at is not None and utc(body.expected_updated_at) != utc(selected.updated_at):
        raise HTTPException(409, "Rota başka bir işlemle değişti; güncel kaydı yükleyin")
    values = body.model_dump(exclude={"request_id", "expected_updated_at"})
    if any(getattr(selected, key) != value for key, value in values.items()):
        for key, value in values.items():
            setattr(selected, key, value)
        selected.updated_by = tenant.user_id
        selected.updated_at = datetime.now(UTC)
        await db.flush()
    response = {"id": str(selected.id), "updated_at": iso(selected.updated_at)}
    db.add(AuditLog(id=body.request_id, organization_id=branch.organization_id, branch_id=branch.id,
        user_id=tenant.user_id, action=AuditAction.UPDATE, entity_type="bus_routes", entity_id=selected.id,
        new_values={"event": "BUS_ROUTE_UPDATED", "fields": list(values),
            "payload_hash": fingerprint(body), "response": response}))
    await commit(db)
    return response


async def create_stop(db, tenant, body):
    selected = await lock_route(db, body.route_id)
    branch = await route_owner(db, selected.branch_id, None)
    return await insert(db, tenant, branch, BusStop, body, "BUS_STOP_CREATED", body.model_dump(exclude={"request_id", "expected_version"}),
        lambda row: {"id": str(row.id), "stop_name": row.stop_name, "stop_order": row.stop_order, "created_at": iso(row.created_at)})


def stop_version(row):
    values = [str(row.id), str(row.route_id), row.stop_name, row.stop_order,
        str(row.latitude) if row.latitude is not None else None, str(row.longitude) if row.longitude is not None else None,
        row.estimated_arrival.isoformat() if row.estimated_arrival else None, iso(row.created_at)]
    return hashlib.sha256(json.dumps(values, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


async def update_stop(db, tenant, identifier, body):
    selected = (await db.execute(select(BusStop).where(BusStop.id == identifier))).scalar_one_or_none()
    if selected is None:
        raise HTTPException(404, "Durak bulunamadı")
    if selected.route_id != body.route_id:
        raise HTTPException(409, "Durak farklı rotaya taşınamaz")
    selected_route = await lock_route(db, selected.route_id)
    branch = await route_owner(db, selected_route.branch_id, None)
    selected = (await db.execute(select(BusStop).where(BusStop.id == identifier).execution_options(populate_existing=True))).scalar_one_or_none()
    if selected is None:
        raise HTTPException(404, "Durak bulunamadı")
    if selected.route_id != body.route_id:
        raise HTTPException(409, "Durak farklı rotaya taşınamaz")
    previous = await cached(db, tenant, body, "BUS_STOP_UPDATED", entity_id=selected.id)
    if previous is not None:
        return previous
    if body.expected_version is not None and body.expected_version != stop_version(selected):
        raise HTTPException(409, "Durak başka bir işlemle değişti; güncel durağı listeden yeniden seçin")
    values = body.model_dump(exclude={"request_id", "route_id", "expected_version"})
    for key, value in values.items():
        setattr(selected, key, value)
    await db.flush()
    await db.refresh(selected)
    response = {"id": str(selected.id), "version": stop_version(selected)}
    db.add(AuditLog(id=body.request_id, organization_id=branch.organization_id, branch_id=branch.id,
        user_id=tenant.user_id, action=AuditAction.UPDATE, entity_type="bus_stops", entity_id=selected.id,
        new_values={"event": "BUS_STOP_UPDATED", "route_id": str(selected.route_id), "fields": list(values),
            "payload_hash": fingerprint(body), "response": response}))
    await commit(db)
    return response


async def create_telemetry(db, tenant, body):
    selected = await lock_route(db, body.route_id)
    branch = await route_owner(db, selected.branch_id, None)
    return await insert(db, tenant, branch, BusTelemetryLog, body, "BUS_TELEMETRY_RECORDED", body.model_dump(exclude={"request_id"}),
        lambda row: {"id": str(row.id), "recorded_at": iso(row.recorded_at)})


async def options(db, branch_id=None, route_id=None, student_id=None, search="", driver_search="", driver_id=None):
    from app.application.services.student_choices import options as student_options
    branches = (await db.execute(select(Branch).where(Branch.deleted_at.is_(None)).order_by(Branch.name, Branch.id).limit(1001))).scalars().all()
    selected = await route(db, route_id) if route_id else None
    branch_id = branch_id or (selected.branch_id if selected else None)
    branch_choices = branches[:1000]
    drivers, more_drivers = [], False
    if branch_id:
        branch = await route_owner(db, branch_id, None)
        if not any(row.id == branch.id for row in branch_choices):
            branch_choices.append(branch)
        base = select(User).where(User.status == "ACTIVE", User.deleted_at.is_(None), User.organization_id == branch.organization_id)
        query = base.where((User.first_name + " " + User.last_name).ilike(f"%{driver_search}%")) if driver_search else base
        matches = (await db.execute(query.order_by(User.first_name, User.last_name, User.id).limit(101))).scalars().all()
        more_drivers = len(matches) > 100
        rows = {row.id: row for row in matches[:100]}
        pinned_id = driver_id or (selected.driver_id if selected and selected.branch_id == branch.id else None)
        if pinned_id and pinned_id not in rows:
            pinned = (await db.execute(base.where(User.id == pinned_id))).scalar_one_or_none()
            if pinned is None:
                # A current branch assignment permits its minimal name, never global user access.
                assigned = (await db.execute(select(BusRoute.id).where(BusRoute.branch_id == branch.id,
                    BusRoute.driver_id == pinned_id).limit(1))).scalar_one_or_none()
                if assigned:
                    table = User.__table__
                    pinned = (await db.execute(select(table.c.id, table.c.first_name, table.c.last_name).where(
                        table.c.id == pinned_id, table.c.organization_id == branch.organization_id,
                        table.c.status == "ACTIVE", table.c.deleted_at.is_(None)))).first()
            if pinned is not None:
                rows[pinned.id] = pinned
            elif driver_id:
                raise HTTPException(403, "Sürücü erişim kapsamı dışında")
        drivers = [{"id": str(row.id), "name": f"{row.first_name} {row.last_name}"} for row in rows.values()]
    children = await student_options(db, student_id, search)
    stops = (await db.execute(select(BusStop).where(BusStop.route_id == selected.id).order_by(BusStop.stop_order, BusStop.id).limit(1001))).scalars().all() if selected else []
    return {**children, "branches": [{"id": str(row.id), "name": row.name, "organization_id": str(row.organization_id)} for row in branch_choices],
        "more_branches": len(branches) > 1000, "drivers": drivers, "more_drivers": more_drivers, "branch_id": str(branch_id) if branch_id else None,
        "stops": [{"id": str(row.id), "name": row.stop_name} for row in stops[:1000]], "more_stops": len(stops) > 1000}


async def existing_attendance(db, route_id, student_id, day):
    rows = (await db.execute(select(BusAttendance).where(BusAttendance.route_id == route_id,
        BusAttendance.student_id == student_id, BusAttendance.date == day).limit(2))).scalars().all()
    if len(rows) > 1:
        raise HTTPException(409, "Aynı gün için eski çift katılım kaydı var; inceleme gerekiyor")
    return rows[0] if rows else None


async def record_attendance(db, tenant, body):
    await attendance_references(db, body.route_id, body.student_id, body.stop_id)
    selected = await existing_attendance(db, body.route_id, body.student_id, body.attendance_date)
    values = body.model_dump(exclude={"route_id", "student_id", "attendance_date"})
    new = selected is None
    if new:
        selected = BusAttendance(route_id=body.route_id, student_id=body.student_id, date=body.attendance_date, **values)
        db.add(selected)
    else:
        values = {key: value for key, value in values.items() if key in body.model_fields_set}
    changed = new or any(getattr(selected, key) != value for key, value in values.items())
    if not new:
        for key, value in values.items():
            setattr(selected, key, value)
    if changed:
        await db.flush()
        selected_route = await route(db, body.route_id)
        branch = await route_owner(db, selected_route.branch_id, None)
        audit(db, tenant, branch, "bus_attendance", selected.id, "BUS_ATTENDANCE_RECORDED", {"fields": list(values), "date": body.attendance_date.isoformat()})
        await commit(db)
    return {"id": str(selected.id), "message": "Servis katılımı kaydedildi", "date": body.attendance_date.isoformat(), "status": selected.status}


async def check_in(db, tenant, body):
    await attendance_references(db, body.route_id, body.student_id)
    previous = await cached(db, tenant, body, "BUS_CHECK_IN")
    if previous is not None:
        return previous
    local = school_datetime(body.timestamp) if body.timestamp.tzinfo else body.timestamp
    selected = await existing_attendance(db, body.route_id, body.student_id, local.date())
    if selected is None:
        selected = BusAttendance(route_id=body.route_id, student_id=body.student_id, date=local.date(), status="PRESENT")
        db.add(selected)
    if body.event == "BOARDED":
        selected.pickup_time = local.time()
        selected.status = "PRESENT"
    else:
        selected.dropoff_time = local.time()
    await db.flush()
    response = {"id": str(selected.id), "route_id": str(body.route_id), "student_id": str(body.student_id), "event": body.event,
        "timestamp": local.isoformat(), "pickup_time": selected.pickup_time.strftime("%H:%M:%S") if selected.pickup_time else None,
        "dropoff_time": selected.dropoff_time.strftime("%H:%M:%S") if selected.dropoff_time else None, "status": selected.status}
    selected_route = await route(db, body.route_id)
    branch = await route_owner(db, selected_route.branch_id, None)
    audit(db, tenant, branch, "bus_attendance", selected.id, "BUS_CHECK_IN", response, body)
    await commit(db)
    return response


async def attendance_rows(db, rows):
    if not rows:
        return []
    children = {row.id: row for row in (await db.execute(select(Student).where(Student.id.in_({record.student_id for record in rows})))).scalars()}
    routes = {row.id: row for row in (await db.execute(select(BusRoute).where(BusRoute.id.in_({record.route_id for record in rows})))).scalars()}
    stops = {row.id: row for row in (await db.execute(select(BusStop).where(BusStop.id.in_({record.stop_id for record in rows if record.stop_id})))).scalars()}
    result = []
    for row in rows:
        child, selected, stop = children.get(row.student_id), routes.get(row.route_id), stops.get(row.stop_id)
        result.append({"id": str(row.id), "route_id": str(row.route_id), "route_name": selected.route_name if selected else None,
            "student_id": str(row.student_id), "student_name": f"{child.first_name} {child.last_name}" if child else None,
            "stop_id": str(row.stop_id) if row.stop_id else None, "stop_name": stop.stop_name if stop and stop.route_id == row.route_id else None,
            "date": row.date.isoformat(), "pickup_time": row.pickup_time.strftime("%H:%M") if row.pickup_time else None,
            "dropoff_time": row.dropoff_time.strftime("%H:%M") if row.dropoff_time else None, "status": row.status,
            "notes": row.notes, "created_at": iso(row.created_at)})
    return result
