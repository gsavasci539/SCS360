import asyncio
from datetime import date
from uuid import UUID

import pytest
from sqlalchemy import select

from test_material_files import materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.core.security import create_access_token
from app.domain.entities.inventory import AssetAssignment, InventoryItem, InventoryLocation, MaintenanceRequest
from app.infrastructure.models.models import Permission, Role, User


def auth(user):
    return {"Authorization": "Bearer " + create_access_token(user.id)}


@pytest.fixture
async def inventory_client(materials_client):
    client, sessions, data = materials_client
    async with sessions() as db:
        permissions = [Permission(code=code, name=code, module="inventory") for code in ("inventory.read", "inventory.write")]
        role = Role(name="Inventory", slug="org_admin", organization_id=data["org"].id, permissions=permissions)
        manager = User(organization_id=data["org"].id, email="inventory@test.example.com", first_name="Inventory", last_name="Manager", password_hash="unused", roles=[role])
        foreign_user = User(organization_id=data["stranger"].organization_id, email="foreign@inventory.example.com", first_name="Foreign", last_name="Staff", password_hash="unused")
        foreign_item = InventoryItem(branch_id=data["other_branch"].id, item_code="FOREIGN", item_name="Private foreign item")
        foreign_location = InventoryLocation(branch_id=data["other_branch"].id, location_name="Foreign room")
        db.add_all([manager, foreign_user, foreign_item, foreign_location])
        await db.flush()
        db.add(AssetAssignment(item_id=foreign_item.id, assigned_to=foreign_user.id, assigned_date=date(2026, 1, 1), notes="Private foreign assignment"))
        db.add(MaintenanceRequest(item_id=foreign_item.id, reported_by=foreign_user.id, issue_description="Private foreign issue"))
        await db.commit()
    yield client, sessions, {**data, "manager": manager, "foreign_user": foreign_user, "foreign_item": foreign_item, "foreign_location": foreign_location}


async def create_item(client, data, code="OWN"):
    body = {"branch_id": str(data["branch"].id), "item_code": code, "item_name": "Öğretmen bilgisayarı"}
    response = await client.post("/api/inventory/items", headers=auth(data["manager"]), json=body)
    assert response.status_code == 200, response.text
    return response.json()["data"], body


async def test_inventory_assignment_and_maintenance_lists_stay_inside_the_institution(inventory_client):
    client, sessions, data = inventory_client
    headers = auth(data["manager"])
    for path in ("/api/inventory/assignments", "/api/inventory/maintenance-requests"):
        response = await client.get(path, headers=headers)
        assert response.status_code == 200 and response.json()["data"] == [], response.text
    response = await client.post("/api/inventory/assignments", headers=headers,
        json={"item_id": str(data["foreign_item"].id), "assigned_to": str(data["teacher"].id)})
    assert response.status_code == 404
    own, body = await create_item(client, data)
    metadata = await client.get("/api/inventory/options", headers=headers, params={"branch_id": str(data["branch"].id)})
    assert metadata.status_code == 200
    assert {row["id"] for row in metadata.json()["data"]["items"]} == {own["id"]}
    response = await client.put('/api/inventory/items/' + own["id"], headers=headers,
        json={**body, "location_id": str(data["foreign_location"].id)})
    assert response.status_code == 404
    response = await client.post("/api/inventory/assignments", headers=headers,
        json={"item_id": own["id"], "assigned_to": str(data["foreign_user"].id)})
    assert response.status_code == 404
    response = await client.post("/api/inventory/maintenance-requests", headers=headers,
        json={"item_id": str(data["foreign_item"].id), "issue_description": "Unauthorized"})
    assert response.status_code == 404


async def test_inventory_return_and_maintenance_are_persistent_idempotent_and_have_a_reporter(inventory_client):
    client, sessions, data = inventory_client
    headers = auth(data["manager"])
    item, body = await create_item(client, data)
    updated = await client.put('/api/inventory/items/' + item["id"], headers=headers, json={**body, "item_name": "Güncellenmiş bilgisayar"})
    assert updated.status_code == 200 and updated.json()["data"]["updated_at"], updated.text
    assigned = await client.post("/api/inventory/assignments", headers=headers,
        json={"item_id": item["id"], "assigned_to": str(data["teacher"].id), "notes": "Korunacak zimmet notu"})
    assert assigned.status_code == 200, assigned.text
    identifier = assigned.json()["data"]["id"]
    returned = await client.post(f"/api/inventory/assignments/{identifier}/return", headers=headers)
    assert returned.status_code == 200, returned.text
    again = await client.post(f"/api/inventory/assignments/{identifier}/return", headers=headers)
    assert again.json()["data"] == returned.json()["data"]
    maintenance = await client.post("/api/inventory/maintenance-requests", headers=headers,
        json={"item_id": item["id"], "issue_description": "Kontrol talebi", "priority": "high", "assigned_to": str(data["teacher"].id)})
    assert maintenance.status_code == 200, maintenance.text
    request_id = maintenance.json()["data"]["id"]
    resolved = await client.post(f"/api/inventory/maintenance-requests/{request_id}/resolve", headers=headers, params={"resolution_notes": "Kontrol tamamlandı"})
    assert resolved.status_code == 200
    again = await client.post(f"/api/inventory/maintenance-requests/{request_id}/resolve", headers=headers)
    assert again.json()["data"] == resolved.json()["data"]
    async with sessions() as db:
        assignment = await db.get(AssetAssignment, UUID(identifier))
        request = await db.get(MaintenanceRequest, UUID(request_id))
        assert assignment.notes == "Korunacak zimmet notu" and assignment.status == "RETURNED"
        assert request.reported_by == data["manager"].id and request.priority == "HIGH"
        assert request.resolution_notes == "Kontrol tamamlandı"
    statistics = (await client.get("/api/ai/inventory-analysis", headers=headers)).json()["data"]
    assert statistics["total_items"] == 1 and statistics["assigned_count"] == 0
    assert statistics["available_count"] == 1 and statistics["pending_maintenance"] == 0


async def test_parallel_assignment_and_duplicate_item_code_cannot_create_invalid_records(inventory_client):
    client, sessions, data = inventory_client
    headers = auth(data["manager"])
    item, body = await create_item(client, data)
    responses = await asyncio.gather(*[client.post("/api/inventory/assignments", headers=headers,
        json={"item_id": item["id"], "assigned_to": str(user.id)}) for user in (data["teacher"], data["manager"])])
    assert sorted(row.status_code for row in responses) == [200, 409], [row.text for row in responses]
    async with sessions() as db:
        assert len((await db.execute(select(AssetAssignment).where(AssetAssignment.item_id == UUID(item["id"]), AssetAssignment.status == "ASSIGNED"))).scalars().all()) == 1
    responses = await asyncio.gather(*[client.post("/api/inventory/items", headers=headers,
        json={**body, "item_code": "CONCURRENT"}) for _ in range(2)])
    assert sorted(row.status_code for row in responses) == [200, 409], [row.text for row in responses]


async def test_inventory_pages_use_bounded_queries_for_many_related_records(inventory_client):
    from sqlalchemy import event
    client, sessions, data = inventory_client
    async with sessions() as db:
        items = [InventoryItem(branch_id=data["branch"].id, item_code=f"LOAD-{index}", item_name=f"Tablet {index}") for index in range(25)]
        db.add_all(items)
        await db.flush()
        db.add_all([AssetAssignment(item_id=row.id, assigned_to=data["teacher"].id, assigned_date=date(2026, 11, 3)) for row in items])
        db.add_all([MaintenanceRequest(item_id=row.id, reported_by=data["manager"].id, assigned_to=data["teacher"].id, issue_description="Test kontrolü") for row in items])
        await db.commit()
    statements = []
    def record(connection, cursor, statement, parameters, context, many):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)
    engine = sessions.kw["bind"].sync_engine
    event.listen(engine, "before_cursor_execute", record)
    try:
        for path in ("/api/inventory/items", "/api/inventory/assignments", "/api/inventory/maintenance-requests"):
            statements.clear()
            response = await client.get(path, headers=auth(data["manager"]), params={"limit": 25})
            assert response.status_code == 200 and len(response.json()["data"]) == 25, response.text
            assert len(statements) < 25, (path, len(statements))
    finally:
        event.remove(engine, "before_cursor_execute", record)
