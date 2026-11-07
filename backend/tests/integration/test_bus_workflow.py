import asyncio
from datetime import date
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from test_bus_scope import bus_client  # noqa: F401
from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.domain.entities.bus import BusRoute, BusStop, BusTelemetryLog, BusAttendance
from app.infrastructure.models.models import Branch, AuditLog


async def test_bus_options_summary_and_empty_location_are_scoped(bus_client):
    client, sessions, data = bus_client
    auth = headers(data["writer"]); route = str(data["routes"][0].id)
    choices = await client.get("/api/bus/options", headers=auth, params={"branch_id": str(data["branch"].id)})
    assert choices.status_code == 200, choices.text
    assert {row["id"] for row in choices.json()["data"]["branches"]} == {str(data["branch"].id)}
    assert str(data["stranger"].id) not in {row["id"] for row in choices.json()["data"]["students"]}
    assert str(data["foreign_driver"].id) not in {row["id"] for row in choices.json()["data"]["drivers"]}
    empty = await client.get(f"/api/bus/telemetry/{route}/latest", headers=auth)
    assert empty.status_code == 200 and empty.json()["data"] is None, empty.text
    async with sessions() as db:
        db.add_all([BusAttendance(route_id=data["routes"][0].id, student_id=data["children"][0].id, date=date(2026, 11, 3), status="PRESENT"),
            BusAttendance(route_id=data["routes"][0].id, student_id=data["children"][1].id, date=date(2026, 11, 2), status="ABSENT")])
        await db.commit()
    summary = await client.get("/api/bus/summary", headers=auth, params={"route_id": route, "attendance_date": "2026-11-03"})
    assert summary.status_code == 200, summary.text
    assert summary.json()["data"]["attendance_records"] == 1 and summary.json()["data"]["attendance_rate"] == 100
    rows = await client.get("/api/bus/attendance", headers=auth, params={"route_id": route, "attendance_date": "2026-11-03"})
    assert rows.status_code == 200 and rows.json()["data"][0]["route_name"] == "Own", rows.text


async def test_bus_creates_retry_once_and_preserve_zero_coordinates(bus_client):
    client, sessions, data = bus_client
    auth = headers(data["writer"])
    nonce = str(uuid4())
    body = {"branch_id": str(data["branch"].id), "route_name": "Retry route", "request_id": nonce}
    replies = await asyncio.gather(*[client.post("/api/bus/routes", headers=auth, json=body) for _ in range(2)])
    assert all(row.status_code == 200 for row in replies), [row.text for row in replies]
    assert replies[0].json()["data"]["id"] == replies[1].json()["data"]["id"]
    assert replies[0].json()["data"]["created_at"] == replies[1].json()["data"]["created_at"]
    assert (await client.post("/api/bus/routes", headers=auth, json={**body, "route_name": "Different"})).status_code == 409
    assert (await client.post("/api/bus/routes", headers=headers(data["root"]), json=body)).status_code == 409
    route = replies[0].json()["data"]["id"]
    for endpoint, payload in (("stops", {"route_id": route, "stop_name": "Zero stop", "stop_order": 1, "latitude": 0, "longitude": 0}),
        ("telemetry", {"route_id": route, "latitude": 0, "longitude": 0, "speed": 0, "heading": 0, "ignition_status": False})):
        payload["request_id"] = str(uuid4())
        first = await client.post("/api/bus/" + endpoint, headers=auth, json=payload)
        repeated = await client.post("/api/bus/" + endpoint, headers=auth, json=payload)
        assert first.status_code == repeated.status_code == 200, (first.text, repeated.text)
        assert first.json()["data"]["id"] == repeated.json()["data"]["id"]
    latest = await client.get(f"/api/bus/telemetry/{route}/latest", headers=auth)
    assert latest.status_code == 200, latest.text
    assert all(latest.json()["data"][key] == 0 for key in ("latitude", "longitude", "speed", "heading"))
    assert latest.json()["data"]["ignition_status"] is False
    async with sessions() as db:
        assert (await db.execute(select(func.count(BusRoute.id)).where(BusRoute.id == UUID(route)))).scalar() == 1
        assert (await db.execute(select(func.count(BusStop.id)).where(BusStop.route_id == UUID(route)))).scalar() == 1
        assert (await db.execute(select(func.count(BusTelemetryLog.id)))).scalar() == 1
        audits = (await db.execute(select(AuditLog).where(AuditLog.entity_type.like("bus_%")))).scalars().all()
        assert len(audits) == 3 and all(row.user_id == data["writer"].id for row in audits)


async def test_route_ownership_cannot_move_history_and_stop_edit_keeps_route(bus_client):
    client, sessions, data = bus_client
    root = headers(data["root"]); auth = headers(data["writer"])
    route = data["routes"][0]; stop = data["stops"][0]
    foreign = await client.put(f"/api/bus/routes/{route.id}", headers=root, json={"branch_id": str(data["other_branch"].id), "route_name": "Moved"})
    assert foreign.status_code == 403, foreign.text
    async with sessions() as db:
        other = Branch(name="Another owned branch", organization_id=data["org"].id)
        db.add(other); await db.commit()
    moved = await client.put(f"/api/bus/routes/{route.id}", headers=root, json={"branch_id": str(other.id), "route_name": "Moved"})
    assert moved.status_code == 409, moved.text
    body = {"route_id": str(route.id), "stop_name": "Updated stop", "stop_order": 3, "latitude": 0, "longitude": 0}
    edited = await client.put(f"/api/bus/stops/{stop.id}", headers=auth, json=body)
    assert edited.status_code == 200, edited.text
    assert (await client.put(f"/api/bus/stops/{stop.id}", headers=auth, json={**body, "route_id": str(data["routes"][1].id)})).status_code == 409
    async with sessions() as db:
        row = await db.get(BusRoute, route.id); saved = await db.get(BusStop, stop.id)
        assert row.branch_id == data["branch"].id and saved.route_id == route.id and saved.stop_name == "Updated stop"


async def test_checkin_retry_keeps_first_clock_and_status_edit_preserves_boarding(bus_client):
    client, sessions, data = bus_client
    auth = headers(data["writer"]); route = str(data["routes"][0].id); child = str(data["children"][0].id)
    body = {"route_id": route, "student_id": child, "event": "BOARDED", "request_id": str(uuid4())}
    first = await client.post("/api/bus/check-in", headers=auth, json=body)
    again = await client.post("/api/bus/check-in", headers=auth, json=body)
    assert first.status_code == again.status_code == 200, (first.text, again.text)
    assert first.json()["data"] == again.json()["data"]
    assert (await client.post("/api/bus/check-in", headers=auth, json={**body, "event": "DROPPED"})).status_code == 409
    changed = await client.post("/api/bus/attendance", headers=auth, json={"route_id": route, "student_id": child, "notes": "Updated note"})
    assert changed.status_code == 200, changed.text
    async with sessions() as db:
        saved = (await db.execute(select(BusAttendance))).scalar_one()
        assert saved.pickup_time is not None and saved.notes == "Updated note"
