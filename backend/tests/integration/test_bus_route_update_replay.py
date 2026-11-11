"""Route PUT replay after lost responses, stale versions, and atomic nonce races."""
import asyncio
from uuid import UUID, uuid4

from sqlalchemy import func, select
from test_bus_scope import bus_client  # noqa: F401
from test_material_files import headers, materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401

from app.domain.entities.bus import BusRoute
from app.infrastructure.models.models import AuditAction, AuditLog


async def test_committed_update_replay_preserves_first_response_and_never_overwrites_later_edits(bus_client):  # noqa: F811
    client, sessions, data = bus_client
    auth = headers(data["writer"])
    path = "/api/bus/routes/" + str(data["routes"][0].id)
    original = (await client.get(path, headers=auth)).json()["data"]
    request_id = str(uuid4())
    body = {"branch_id": str(data["branch"].id), "route_name": "First edit", "request_id": request_id,
        "expected_updated_at": original["updated_at"]}
    first = await client.put(path, headers=auth, json=body)
    assert first.status_code == 200, first.text
    replay = await client.put(path, headers=auth, json=body)
    assert replay.status_code == 200 and replay.json()["data"] == first.json()["data"], replay.text
    assert (await client.put(path, headers=auth, json={**body, "route_name": "Changed nonce payload"})).status_code == 409
    assert (await client.put(path, headers=auth, json={**body, "request_id": str(uuid4())})).status_code == 409
    second = await client.put(path, headers=auth, json={**body, "route_name": "Later edit", "request_id": str(uuid4()),
        "expected_updated_at": first.json()["data"]["updated_at"]})
    assert second.status_code == 200, second.text
    assert (await client.put(path, headers=auth, json=body)).json()["data"] == first.json()["data"]
    other = "/api/bus/routes/" + str(data["routes"][1].id)
    assert (await client.put(other, headers=auth, json=body)).status_code == 409
    root = {**headers(data["root"]), "X-SCS360-Organization-Id": str(data["org"].id)}
    assert (await client.put(path, headers=root, json=body)).status_code == 409
    async with sessions() as db:
        assert (await db.get(BusRoute, data["routes"][0].id)).route_name == "Later edit"
        audit = await db.get(AuditLog, UUID(request_id))
        assert audit.action == AuditAction.UPDATE and audit.entity_id == data["routes"][0].id
        assert audit.new_values["response"] == first.json()["data"]
        assert (await db.execute(select(func.count()).select_from(AuditLog).where(AuditLog.id == UUID(request_id)))).scalar_one() == 1


async def test_unchanged_route_update_also_consumes_its_nonce_once(bus_client):  # noqa: F811
    client, sessions, data = bus_client
    auth = headers(data["writer"])
    path = "/api/bus/routes/" + str(data["routes"][0].id)
    original = (await client.get(path, headers=auth)).json()["data"]
    body = {**{name: original[name] for name in ("branch_id", "route_name", "route_number", "description", "driver_id", "vehicle_plate", "capacity", "status")},
        "request_id": str(uuid4()), "expected_updated_at": original["updated_at"]}
    replies = [await client.put(path, headers=auth, json=body) for _ in range(2)]
    assert all(reply.status_code == 200 for reply in replies), [reply.text for reply in replies]
    assert replies[0].json()["data"] == replies[1].json()["data"] == {"id": original["id"], "updated_at": original["updated_at"]}
    async with sessions() as db:
        assert (await db.get(BusRoute, data["routes"][0].id)).updated_by is None
        assert (await db.execute(select(func.count()).select_from(AuditLog).where(AuditLog.id == UUID(body["request_id"])))).scalar_one() == 1


async def test_cross_route_nonce_race_rolls_back_the_entire_losing_update(bus_client):  # noqa: F811
    client, sessions, data = bus_client
    auth = headers(data["writer"])
    body = {"branch_id": str(data["branch"].id), "route_name": "Nonce race winner", "request_id": str(uuid4())}
    paths = ["/api/bus/routes/" + str(row.id) for row in data["routes"][:2]]
    replies = await asyncio.gather(*[client.put(path, headers=auth, json=body) for path in paths])
    assert sorted(reply.status_code for reply in replies) == [200, 409], [reply.text for reply in replies]
    winner = next(index for index, reply in enumerate(replies) if reply.status_code == 200)
    async with sessions() as db:
        for index, row in enumerate(data["routes"][:2]):
            actual = await db.get(BusRoute, row.id)
            assert actual.route_name == ("Nonce race winner" if index == winner else row.route_name)
            assert actual.updated_by == (data["writer"].id if index == winner else None)
        audit = await db.get(AuditLog, UUID(body["request_id"]))
        assert audit.entity_id == data["routes"][winner].id
