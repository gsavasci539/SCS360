from datetime import date
import asyncio
from uuid import UUID

import pytest
from sqlalchemy import func, select

from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.domain.entities.bus import BusRoute, BusStop, BusAttendance
from app.infrastructure.models.models import Permission, Role, User


@pytest.fixture
async def bus_client(materials_client):
    client, sessions, data = materials_client
    async with sessions() as db:
        permissions = [Permission(code=f"bus.{action}", name=action, module="bus") for action in ("read", "write")]
        writer = User(email="bus@test.invalid", password_hash="unused", first_name="Bus", last_name="Desk",
            organization_id=data["org"].id, branches=[data["branch"]], roles=[Role(name="Bus", slug="bus_desk", organization_id=data["org"].id, permissions=permissions)])
        foreign_driver = User(email="foreign-driver@test.invalid", password_hash="unused", first_name="Other", last_name="Driver", organization_id=data["stranger"].organization_id)
        root = User(email="bus-root@test.invalid", password_hash="unused", first_name="Root", last_name="Test", is_super_admin=True)
        routes = [BusRoute(branch_id=branch.id, route_name=name, vehicle_plate="34 SCS 360", capacity=24) for branch, name in ((data["branch"], "Own"), (data["branch"], "Other route"), (data["other_branch"], "Foreign"))]
        db.add_all([writer, foreign_driver, root, *routes]); await db.flush()
        stops = [BusStop(route_id=route.id, stop_name="Stop", stop_order=1) for route in routes]
        db.add_all(stops); await db.commit()
    return client, sessions, {**data, "writer": writer, "foreign_driver": foreign_driver, "root": root, "routes": routes, "stops": stops}


async def test_bus_writes_require_accessible_route_and_stop_from_same_route(bus_client):
    client, sessions, data = bus_client
    auth = headers(data["writer"])
    foreign = str(data["routes"][2].id); child = str(data["children"][0].id)
    for path, body in (("stops", {"route_id": foreign, "stop_name": "Forged", "stop_order": 2}),
        ("telemetry", {"route_id": foreign}), ("attendance", {"route_id": foreign, "student_id": child}),
        ("check-in", {"route_id": foreign, "student_id": child, "event": "BOARDED"})):
        reply = await client.post("/api/bus/" + path, headers=auth, json=body)
        assert reply.status_code == 404, (path, reply.text)
    body = {"route_id": str(data["routes"][0].id), "student_id": child, "stop_id": str(data["stops"][1].id)}
    mismatch = await client.post("/api/bus/attendance", headers=auth, json=body)
    assert mismatch.status_code == 403, mismatch.text
    async with sessions() as db:
        assert (await db.execute(select(func.count(BusAttendance.id)))).scalar() == 0
    valid = await client.post("/api/bus/attendance", headers=auth, json={**body, "stop_id": str(data["stops"][0].id)})
    assert valid.status_code == 200, valid.text
    listing = await client.get(f'/api/bus/routes/{body["route_id"]}/students', headers=auth, params={"attendance_date": date.today().isoformat()})
    assert listing.status_code == 200, listing.text
    assert (await client.post("/api/bus/check-in", headers=auth, json={"route_id": body["route_id"], "student_id": child, "event": "BOARDED", "timestamp": None})).status_code == 422


async def test_bus_driver_must_belong_to_route_organization_even_for_root(bus_client):
    client, sessions, data = bus_client
    body = {"branch_id": str(data["branch"].id), "route_name": "Driver check", "driver_id": str(data["foreign_driver"].id)}
    for actor in (data["writer"], data["root"]):
        reply = await client.post("/api/bus/routes", headers=headers(actor), json=body)
        assert reply.status_code == 403, reply.text
    valid = await client.post("/api/bus/routes", headers=headers(data["writer"]), json={**body, "driver_id": str(data["writer"].id)})
    assert valid.status_code == 200, valid.text
    changed = await client.put(f'/api/bus/routes/{valid.json()["data"]["id"]}', headers=headers(data["root"]), json=body)
    assert changed.status_code == 403, changed.text
    for invalid in ({"capacity": 2147483648}, {"description": "x" * 1001}, {"status": "x" * 21}):
        response = await client.post("/api/bus/routes", headers=headers(data["writer"]), json={**body, "driver_id": None, **invalid})
        assert response.status_code == 422, response.text


async def test_transport_summary_counts_scoped_records_and_requires_bus_read(bus_client):
    client, sessions, data = bus_client
    async with sessions() as db:
        db.add_all([BusAttendance(route_id=data["routes"][0].id, student_id=data["children"][0].id, date=date(2026, 11, 3), status="PRESENT"),
            BusAttendance(route_id=data["routes"][2].id, student_id=data["stranger"].id, date=date(2026, 11, 3), status="PRESENT")])
        await db.commit()
    denied = await client.get("/api/ai/transport-analysis", headers=headers(data["teacher"]))
    assert denied.status_code == 403, denied.text
    response = await client.get("/api/ai/transport-analysis", headers=headers(data["writer"]))
    assert response.status_code == 200, response.text
    result = response.json()["data"]
    assert result["total_routes"] == 2 and result["active_routes"] == 2 and result["total_capacity"] == 48
    assert result["total_students"] == 1 and result["attendance_rate"] == 100
    assert result["attendance_basis"] == "RECORDED_ATTENDANCE" and result["recommendations"] == []


async def test_bus_attendance_serializes_first_record_and_preserves_ambiguous_history(bus_client):
    client, sessions, data = bus_client
    auth = headers(data["writer"])
    child = data["children"][0].id; route_id = data["routes"][0].id
    body = {"route_id": str(route_id), "student_id": str(child), "attendance_date": "2026-11-03"}
    replies = await asyncio.gather(*[client.post("/api/bus/attendance", headers=auth, json=body) for _ in range(2)])
    assert all(reply.status_code == 200 for reply in replies), [reply.text for reply in replies]
    async with sessions() as db:
        assert (await db.execute(select(func.count(BusAttendance.id)))).scalar() == 1
        db.add(BusAttendance(route_id=route_id, student_id=child, date=date(2026, 11, 3), notes="Legacy duplicate"))
        await db.commit()
    ambiguous = await client.post("/api/bus/attendance", headers=auth, json=body)
    assert ambiguous.status_code == 409, ambiguous.text
    check_in = await client.post("/api/bus/check-in", headers=auth, json={"route_id": str(route_id), "student_id": str(child), "event": "BOARDED", "timestamp": "2026-11-03T09:00:00"})
    assert check_in.status_code == 409, check_in.text
    async with sessions() as db:
        assert (await db.execute(select(func.count(BusAttendance.id)))).scalar() == 2
        assert (await db.execute(select(BusAttendance.notes).where(BusAttendance.notes == "Legacy duplicate"))).scalar_one() == "Legacy duplicate"


async def test_bus_check_in_uses_school_day_for_offset_timestamp(bus_client, monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "BUSINESS_TIMEZONE", "Europe/Istanbul")
    client, sessions, data = bus_client
    response = await client.post("/api/bus/check-in", headers=headers(data["writer"]), json={
        "route_id": str(data["routes"][0].id), "student_id": str(data["children"][0].id),
        "event": "BOARDED", "timestamp": "2026-11-02T22:30:00Z"})
    assert response.status_code == 200, response.text
    async with sessions() as db:
        row = (await db.execute(select(BusAttendance))).scalar_one()
        assert row.date == date(2026, 11, 3)
        assert row.pickup_time.hour == 1 and row.pickup_time.minute == 30


async def test_assigned_driver_name_and_edit_do_not_require_global_staff_access(bus_client):
    client, sessions, data = bus_client
    async with sessions() as db:
        driver = User(email="assigned-driver@test.invalid", password_hash="unused", first_name="Assigned", last_name="Driver", organization_id=data["org"].id)
        unassigned = User(email="unassigned-driver@test.invalid", password_hash="unused", first_name="Unassigned", last_name="Driver", organization_id=data["org"].id)
        db.add_all([driver, unassigned]); await db.flush()
        own = await db.get(BusRoute, data["routes"][0].id); own.driver_id = driver.id
        corrupt = await db.get(BusRoute, data["routes"][1].id); corrupt.driver_id = data["foreign_driver"].id
        await db.commit()
    auth = headers(data["writer"])
    listing = await client.get("/api/bus/routes", headers=auth)
    assert listing.status_code == 200, listing.text
    routes = {row["id"]: row for row in listing.json()["data"]}
    assert routes[str(own.id)]["driver_name"] == "Assigned Driver"
    assert routes[str(corrupt.id)]["driver_name"] is None
    assert (await client.get("/api/users", headers=auth)).status_code == 403
    payload = {"branch_id": str(data["branch"].id), "route_name": own.route_name + " updated", "driver_id": str(driver.id), "capacity": 24}
    edited = await client.put(f"/api/bus/routes/{own.id}", headers=auth, json=payload)
    assert edited.status_code == 200, edited.text
    denied = await client.post("/api/bus/routes", headers=auth, json={**payload, "driver_id": str(unassigned.id)})
    assert denied.status_code == 403, denied.text


async def test_bus_route_edit_returns_committed_timestamp_and_real_actor(bus_client):
    client, sessions, data = bus_client
    auth = headers(data["writer"])
    body = {"branch_id": str(data["branch"].id), "route_name": "First route", "driver_id": str(data["writer"].id)}
    created = await client.post("/api/bus/routes", headers=auth, json=body)
    assert created.status_code == 200, created.text
    route_id = created.json()["data"]["id"]
    edited = await client.put(f"/api/bus/routes/{route_id}", headers=auth, json={**body, "route_name": "Updated route"})
    assert edited.status_code == 200, edited.text
    assert edited.json()["data"]["updated_at"]
    async with sessions() as db:
        row = await db.get(BusRoute, UUID(route_id))
        assert row.route_name == "Updated route" and row.updated_by == data["writer"].id
