"""Real HTTP driver search beyond the first page, with tenant/branch and current-choice scope."""
from uuid import uuid4

from test_bus_scope import bus_client  # noqa: F401
from test_material_files import headers, materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401

from app.domain.entities.bus import BusRoute
from app.infrastructure.models.models import Branch, User


async def test_driver_search_finds_later_rows_pins_selected_and_saves_real_assignment(bus_client):  # noqa: F811
    client, sessions, data = bus_client
    async with sessions() as db:
        branch = await db.get(Branch, data["branch"].id)
        db.add_all([User(email=f"bus-choice-{index}@test.invalid", password_hash="unused", first_name=f"A{index:03}",
            last_name="Aday", organization_id=data["org"].id, branches=[branch]) for index in range(105)])
        target = User(email="later-driver@test.invalid", password_hash="unused", first_name="Zeynep", last_name="Taşcı",
            organization_id=data["org"].id, branches=[branch])
        db.add(target)
        await db.commit()
        target_id = str(target.id)
    auth = headers(data["writer"])
    params = {"branch_id": str(data["branch"].id)}
    first = await client.get("/api/bus/options", headers=auth, params=params)
    assert first.status_code == 200, first.text
    result = first.json()["data"]
    assert len(result["drivers"]) == 100 and result["more_drivers"] is True
    assert target_id not in {row["id"] for row in result["drivers"]}
    found = await client.get("/api/bus/options", headers=auth, params={**params, "driver_search": "  Zeynep Taşcı  "})
    assert found.status_code == 200, found.text
    assert found.json()["data"]["drivers"] == [{"id": target_id, "name": "Zeynep Taşcı"}]
    assert found.json()["data"]["more_drivers"] is False
    pinned = await client.get("/api/bus/options", headers=auth,
        params={**params, "driver_search": "Aday", "driver_id": target_id})
    assert pinned.status_code == 200, pinned.text
    choices = pinned.json()["data"]["drivers"]
    assert len(choices) == 101 and {row["id"] for row in choices} >= {target_id}
    assert all(set(row) == {"id", "name"} for row in choices)
    route_id = str(data["routes"][0].id)
    detail = await client.get("/api/bus/routes/" + route_id, headers=auth)
    saved = await client.put("/api/bus/routes/" + route_id, headers=auth, json={**params,
        "route_name": "Own", "driver_id": target_id, "request_id": str(uuid4()),
        "expected_updated_at": detail.json()["data"]["updated_at"]})
    assert saved.status_code == 200, saved.text
    async with sessions() as db:
        assert str((await db.get(BusRoute, data["routes"][0].id)).driver_id) == target_id


async def test_driver_pins_do_not_bypass_institution_branch_or_active_account_scope(bus_client):  # noqa: F811
    client, sessions, data = bus_client
    async with sessions() as db:
        hidden_branch = Branch(organization_id=data["org"].id, name="Other own branch")
        hidden = User(email="hidden-driver@test.invalid", password_hash="unused", first_name="Hidden", last_name="Driver",
            organization_id=data["org"].id, branches=[hidden_branch])
        current = User(email="assigned-driver@test.invalid", password_hash="unused", first_name="Current", last_name="Driver",
            organization_id=data["org"].id)
        inactive = User(email="inactive-driver@test.invalid", password_hash="unused", first_name="Inactive", last_name="Driver",
            organization_id=data["org"].id, status="PASSIVE")
        db.add_all([hidden, current, inactive])
        await db.flush()
        (await db.get(BusRoute, data["routes"][0].id)).driver_id = current.id
        await db.commit()
        hidden_id, current_id, inactive_id = str(hidden.id), str(current.id), str(inactive.id)
    auth = headers(data["writer"])
    params = {"branch_id": str(data["branch"].id), "route_id": str(data["routes"][0].id), "driver_search": "No results"}
    pinned = await client.get("/api/bus/options", headers=auth, params=params)
    assert pinned.status_code == 200, pinned.text
    assert pinned.json()["data"]["drivers"] == [{"id": current_id, "name": "Current Driver"}]
    for forbidden in (hidden_id, inactive_id, str(data["foreign_driver"].id), str(uuid4())):
        result = await client.get("/api/bus/options", headers=auth, params={**params, "driver_id": forbidden})
        assert result.status_code == 403, result.text
    assert (await client.get("/api/bus/options", headers=headers(data["user"]), params=params)).status_code == 403
    assert (await client.get("/api/bus/options", headers=auth, params={**params, "driver_search": "x" * 101})).status_code == 422
    assert (await client.get("/api/bus/options", headers=auth, params={**params, "driver_id": "invalid"})).status_code == 422
