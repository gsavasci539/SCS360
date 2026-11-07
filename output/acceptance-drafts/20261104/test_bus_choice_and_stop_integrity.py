"""Large driver choices and conflict-safe, idempotent stop edits."""
import asyncio
from uuid import uuid4

from sqlalchemy import func, select

from app.domain.entities.bus import BusRoute, BusStop
from app.infrastructure.models.models import AuditAction, AuditLog, Branch, User
from test_bus_scope import bus_client  # noqa: F401
from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401


async def test_driver_choices_search_page_and_pin_beyond_first_hundred_without_user_read(bus_client):
    client, sessions, data = bus_client
    async with sessions() as db:
        drivers = [User(email=f"driver-{index}@bus.invalid", password_hash="unused", first_name=f"Driver{index:03}",
            last_name="Choice", organization_id=data["org"].id, branches=[data["branch"]]) for index in range(105)]
        db.add_all(drivers); await db.commit()
    auth = headers(data["writer"])
    base = {"branch_id": str(data["branch"].id), "driver_page_size": 10}
    first = await client.get("/api/bus/options", headers=auth, params=base)
    second = await client.get("/api/bus/options", headers=auth, params={**base, "driver_page": 2})
    assert first.status_code == second.status_code == 200, (first.text, second.text)
    a, b = first.json()["data"], second.json()["data"]
    assert len(a["drivers"]) == len(b["drivers"]) == 10
    assert a["driver_total"] >= 105 and a["driver_total_pages"] >= 11
    assert not ({row["id"] for row in a["drivers"]} & {row["id"] for row in b["drivers"]})
    found = await client.get("/api/bus/options", headers=auth, params={**base, "driver_search": "Driver104"})
    assert found.status_code == 200
    assert found.json()["data"]["drivers"] == [{"id": str(drivers[-1].id), "name": "Driver104 Choice"}]
    pinned = await client.get("/api/bus/options", headers=auth, params={**base, "driver_search": "Driver000", "selected_driver_id": str(drivers[-1].id)})
    assert pinned.status_code == 200, pinned.text
    values = pinned.json()["data"]
    assert {row["id"] for row in values["drivers"]} == {str(drivers[0].id), str(drivers[-1].id)}
    assert values["driver_total"] == 1
    assert (await client.get("/api/users", headers=auth)).status_code == 403


async def test_driver_purpose_keeps_assigned_name_but_rejects_foreign_and_hidden_unassigned(bus_client):
    client, sessions, data = bus_client
    async with sessions() as db:
        other = Branch(name="Other own branch", organization_id=data["org"].id)
        db.add(other); await db.flush()
        assigned = User(email="assigned-purpose@bus.invalid", password_hash="unused", first_name="Special", last_name="Assigned", organization_id=data["org"].id)
        hidden = User(email="hidden-purpose@bus.invalid", password_hash="unused", first_name="Special", last_name="Hidden", organization_id=data["org"].id, branches=[other])
        db.add_all([assigned, hidden]); await db.flush()
        selected = await db.get(BusRoute, data["routes"][0].id); selected.driver_id = assigned.id
        await db.commit()
    auth = headers(data["writer"])
    base = {"route_id": str(selected.id), "driver_search": "Special", "selected_driver_id": str(data["foreign_driver"].id)}
    choices = await client.get("/api/bus/options", headers=auth, params=base)
    assert choices.status_code == 200, choices.text
    assert choices.json()["data"]["drivers"] == [{"id": str(assigned.id), "name": "Special Assigned"}]
    hidden_pin = await client.get("/api/bus/options", headers=auth, params={**base, "selected_driver_id": str(hidden.id)})
    assert hidden_pin.status_code == 200 and str(hidden.id) not in hidden_pin.text
    for field, value in (("driver_page", 0), ("driver_page_size", 101), ("driver_search", "x" * 101)):
        invalid = await client.get("/api/bus/options", headers=auth, params={**base, field: value})
        assert invalid.status_code == 422, invalid.text


async def stop_version(client, actor, route_id, stop_id):
    reply = await client.get("/api/bus/stops", headers=headers(actor), params={"route_id": str(route_id)})
    assert reply.status_code == 200, reply.text
    return next(row["version"] for row in reply.json()["data"] if row["id"] == str(stop_id))


def change(data, **values):
    return {"route_id": str(data["routes"][0].id), "stop_name": "First edit", "stop_order": 1,
        "latitude": 0, "longitude": 0, "estimated_arrival": "08:20", "request_id": str(uuid4()), **values}


async def test_stale_stop_edit_cannot_overwrite_committed_changes_and_retry_replays_once(bus_client):
    client, sessions, data = bus_client
    identifier = data["stops"][0].id
    version = await stop_version(client, data["writer"], data["routes"][0].id, identifier)
    body = change(data, expected_version=version)
    first = await client.put(f"/api/bus/stops/{identifier}", headers=headers(data["writer"]), json=body)
    assert first.status_code == 200 and first.json()["data"]["version"] != version, first.text
    stale = await client.put(f"/api/bus/stops/{identifier}", headers=headers(data["writer"]), json={**body, "request_id": str(uuid4()), "stop_name": "Stale overwrite"})
    assert stale.status_code == 409, stale.text
    replay = await client.put(f"/api/bus/stops/{identifier}", headers=headers(data["writer"]), json=body)
    assert replay.status_code == 200 and replay.json()["data"] == first.json()["data"], replay.text
    async with sessions() as db:
        assert (await db.get(BusStop, identifier)).stop_name == "First edit"
        audits = (await db.execute(select(AuditLog).where(AuditLog.entity_type == "bus_stops", AuditLog.entity_id == identifier))).scalars().all()
        assert len(audits) == 1 and audits[0].action == AuditAction.UPDATE


async def test_stop_update_nonce_is_bound_to_url_actor_and_body(bus_client):
    client, sessions, data = bus_client
    async with sessions() as db:
        other = BusStop(route_id=data["routes"][0].id, stop_name="Other stop", stop_order=2)
        db.add(other); await db.commit()
    identifier = data["stops"][0].id
    body = change(data)
    first = await client.put(f"/api/bus/stops/{identifier}", headers=headers(data["writer"]), json=body)
    assert first.status_code == 200, first.text
    for actor, target, payload in ((data["writer"], other.id, body),
        (data["writer"], identifier, {**body, "stop_name": "Different body"}), (data["root"], identifier, body)):
        reply = await client.put(f"/api/bus/stops/{target}", headers=headers(actor), json=payload)
        assert reply.status_code == 409, reply.text
    async with sessions() as db:
        assert (await db.get(BusStop, other.id)).stop_name == "Other stop"
        assert await db.scalar(select(func.count(AuditLog.id)).where(AuditLog.entity_type == "bus_stops")) == 1


async def test_concurrent_stop_version_writers_have_one_winner_without_history_loss(bus_client):
    client, sessions, data = bus_client
    identifier = data["stops"][0].id
    version = await stop_version(client, data["writer"], data["routes"][0].id, identifier)
    bodies = [change(data, expected_version=version, stop_name=name) for name in ("Writer A", "Writer B")]
    replies = await asyncio.gather(*[client.put(f"/api/bus/stops/{identifier}", headers=headers(data["writer"]), json=body) for body in bodies])
    assert sorted(reply.status_code for reply in replies) == [200, 409], [reply.text for reply in replies]
    async with sessions() as db:
        assert (await db.get(BusStop, identifier)).stop_name in {"Writer A", "Writer B"}
        assert await db.scalar(select(func.count(AuditLog.id)).where(AuditLog.entity_id == identifier)) == 1


async def test_stop_version_changes_even_when_fields_are_changed_back(bus_client):
    client, _, data = bus_client
    identifier = data["stops"][0].id
    original = await stop_version(client, data["writer"], data["routes"][0].id, identifier)
    a = await client.put(f"/api/bus/stops/{identifier}", headers=headers(data["writer"]), json=change(data, expected_version=original))
    assert a.status_code == 200, a.text
    b = await client.put(f"/api/bus/stops/{identifier}", headers=headers(data["writer"]), json=change(data, expected_version=a.json()["data"]["version"], stop_name="Stop", latitude=None, longitude=None, estimated_arrival=None))
    assert b.status_code == 200, b.text
    assert await stop_version(client, data["writer"], data["routes"][0].id, identifier) != original
