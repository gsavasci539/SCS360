"""Stop edits: stale versions, lost-response replay, precision, and concurrent writers."""
import asyncio
from datetime import time
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import func, select
from test_bus_scope import bus_client  # noqa: F401
from test_material_files import headers, materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401

from app.domain.entities.bus import BusStop
from app.infrastructure.models.models import AuditLog


async def snapshot(client, auth, route_id, stop_id):
    response = await client.get("/api/bus/stops", headers=auth, params={"route_id": str(route_id)})
    assert response.status_code == 200, response.text
    return next(row for row in response.json()["data"] if row["id"] == str(stop_id))


async def test_stop_version_replay_and_later_edits_preserve_exact_clock_and_coordinates(bus_client):  # noqa: F811
    client, sessions, data = bus_client
    auth = headers(data["writer"])
    route_id, stop_id = data["routes"][0].id, data["stops"][0].id
    async with sessions() as db:
        row = await db.get(BusStop, stop_id)
        row.estimated_arrival, row.latitude, row.longitude = time(8, 30, 45, 123000), Decimal("0"), Decimal("1.12345678")
        sibling = BusStop(route_id=route_id, stop_name="Sibling", stop_order=20)
        db.add(sibling)
        await db.commit()
        sibling_id = sibling.id
    original = await snapshot(client, auth, route_id, stop_id)
    assert original["estimated_arrival"] == "08:30:45.123000" and len(original["version"]) == 64
    path = "/api/bus/stops/" + str(stop_id)
    body = {"route_id": str(route_id), "stop_name": "First edit", "stop_order": 2,
        "latitude": 0, "longitude": "1.12345678", "estimated_arrival": original["estimated_arrival"],
        "expected_version": original["version"], "request_id": str(uuid4())}
    first = await client.put(path, headers=auth, json=body)
    assert first.status_code == 200, first.text
    assert (await client.put(path, headers=auth, json=body)).json()["data"] == first.json()["data"]
    latest = await snapshot(client, auth, route_id, stop_id)
    assert latest["version"] == first.json()["data"]["version"] != original["version"]
    assert (await client.put(path, headers=auth, json={**body, "request_id": str(uuid4())})).status_code == 409
    assert (await client.put(path, headers=auth, json={**body, "stop_name": "Nonce altered"})).status_code == 409
    second = await client.put(path, headers=auth, json={**body, "stop_name": "Later edit", "request_id": str(uuid4()),
        "expected_version": latest["version"]})
    assert second.status_code == 200, second.text
    assert (await client.put(path, headers=auth, json=body)).json()["data"] == first.json()["data"]
    other = await client.put("/api/bus/stops/" + str(sibling_id), headers=auth, json=body)
    assert other.status_code == 409, other.text
    async with sessions() as db:
        row = await db.get(BusStop, stop_id)
        assert row.stop_name == "Later edit" and row.latitude == 0 and row.longitude == Decimal("1.12345678")
        assert row.estimated_arrival == time(8, 30, 45, 123000)
        assert (await db.get(AuditLog, UUID(body["request_id"]))).entity_id == stop_id


async def test_concurrent_stop_versions_allow_one_writer_and_return_one_original_snapshot(bus_client):  # noqa: F811
    client, sessions, data = bus_client
    auth = headers(data["writer"])
    route_id, stop_id = data["routes"][0].id, data["stops"][0].id
    original = await snapshot(client, auth, route_id, stop_id)
    bodies = [{"route_id": str(route_id), "stop_name": label, "stop_order": 3,
        "request_id": str(uuid4()), "expected_version": original["version"]} for label in ("Writer A", "Writer B")]
    replies = await asyncio.gather(*[client.put("/api/bus/stops/" + str(stop_id), headers=auth, json=body) for body in bodies])
    assert sorted(row.status_code for row in replies) == [200, 409], [row.text for row in replies]
    winner = next(index for index, row in enumerate(replies) if row.status_code == 200)
    async with sessions() as db:
        assert (await db.get(BusStop, stop_id)).stop_name == bodies[winner]["stop_name"]
        assert (await db.execute(select(func.count()).select_from(AuditLog).where(AuditLog.id.in_([UUID(body["request_id"]) for body in bodies])))).scalar_one() == 1


async def test_stop_version_rejects_invalid_values_and_keeps_legacy_creation_hash(bus_client):  # noqa: F811
    import hashlib
    import json

    from app.application.services.bus_service import fingerprint
    from app.routers.bus import BusStopCreate

    client, _, data = bus_client
    auth = headers(data["writer"])
    body = {"route_id": str(data["routes"][0].id), "stop_name": "Compatible creation", "stop_order": 5, "request_id": str(uuid4())}
    model = BusStopCreate(**body)
    old = model.model_dump(mode="json", exclude={"request_id", "expected_version"})
    assert fingerprint(model) == hashlib.sha256(json.dumps(old, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    for version in ("bad", "A" * 64):
        assert (await client.put("/api/bus/stops/" + str(data["stops"][0].id), headers=auth, json={**body, "expected_version": version})).status_code == 422
