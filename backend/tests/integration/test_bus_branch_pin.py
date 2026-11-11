from test_bus_scope import bus_client  # noqa: F401
from test_material_files import headers, materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401

from app.domain.entities.bus import BusRoute
from app.infrastructure.models.models import Branch


async def test_branch_beyond_first_thousand_is_pinned_only_inside_its_authorized_scope(bus_client):  # noqa: F811
    client, sessions, data = bus_client
    async with sessions() as db:
        db.add_all([Branch(name=f"A{index:04}", organization_id=data["org"].id) for index in range(1001)])
        branch = Branch(name="Z current branch", organization_id=data["org"].id)
        db.add(branch)
        await db.flush()
        route = BusRoute(branch_id=branch.id, route_name="Late branch route")
        db.add(route)
        await db.commit()
    auth = {**headers(data["root"]), "X-SCS360-Organization-Id": str(data["org"].id)}
    result = await client.get("/api/bus/options", headers=auth, params={"route_id": str(route.id)})
    assert result.status_code == 200, result.text
    choices = result.json()["data"]
    assert len(choices["branches"]) == 1001 and choices["more_branches"] is True
    assert {"id": str(branch.id), "name": branch.name, "organization_id": str(data["org"].id)} in choices["branches"]
    assert (await client.get("/api/bus/options", headers=headers(data["writer"]), params={"route_id": str(route.id)})).status_code == 404
    visible = await client.get("/api/bus/options", headers=headers(data["writer"]))
    assert {row["id"] for row in visible.json()["data"]["branches"]} == {str(data["branch"].id)}
