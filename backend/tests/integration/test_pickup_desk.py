import asyncio
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.core.dates import school_today
from app.domain.entities.pickup import PickupAuthorization, PickupLog
from app.infrastructure.models.models import Permission, Role, User, Student, StudentStatus


@pytest.fixture
async def pickup_client(materials_client):
    client, sessions, data = materials_client
    async with sessions() as db:
        read, write = [Permission(code=code, name=code, module="dismissal") for code in ("dismissal.read", "dismissal.write")]
        actor = User(email="pickup-desk@test.invalid", password_hash="unused", first_name="Pickup", last_name="Desk",
            organization_id=data["org"].id, branches=[data["branch"]], roles=[Role(name="Desk", slug="security", organization_id=data["org"].id, permissions=[read, write])])
        reader = User(email="pickup-reader@test.invalid", password_hash="unused", first_name="Pickup", last_name="Reader",
            organization_id=data["org"].id, branches=[data["branch"]], roles=[Role(name="Desk reader", slug="security_reader", organization_id=data["org"].id, permissions=[read])])
        db.add_all([actor, reader]); await db.commit()
    return client, sessions, {**data, "actor": actor, "reader": reader}


def body(data, **extra):
    return {"student_id": str(data["children"][0].id), "authorized_person_name": "Authorized adult", "authorized_person_id": "TEST-DOC-001",
        "valid_from": str(school_today()), "valid_until": str(school_today() + timedelta(days=1)), "photo_url": "/private/legacy-photo.svg", **extra}


async def test_pickup_authorization_update_returns_generated_timestamp_and_keeps_delivery_snapshot(pickup_client):
    client, _, data = pickup_client
    auth = headers(data["actor"])
    created = await client.post("/api/dismissal/authorizations", headers=auth, json=body(data))
    assert created.status_code == 200, created.text
    identifier = created.json()["data"]["id"]
    edited = await client.put("/api/dismissal/authorizations/" + identifier, headers=auth, json=body(data, phone="05000000000"))
    assert edited.status_code == 200 and edited.json()["data"]["updated_at"], edited.text
    delivered = await client.post("/api/dismissal/verify-pickup", headers=auth, json={"student_id": str(data["children"][0].id),
        "pickup_person_id": "TEST-DOC-001", "request_id": str(uuid4())})
    assert delivered.status_code == 200 and delivered.json()["data"]["authorized"] is True, delivered.text
    edited = await client.put("/api/dismissal/authorizations/" + identifier, headers=auth,
        json=body(data, authorized_person_name="Updated adult", phone="05000000000"))
    assert edited.status_code == 200
    logs = await client.get("/api/dismissal/logs", headers=auth)
    assert logs.json()["data"][0]["pickup_person_name"] == "Authorized adult"
    records = await client.get("/api/dismissal/authorizations", headers=auth)
    assert records.json()["data"][0]["photo_url"] == "/private/legacy-photo.svg"


async def test_pickup_create_retries_overlap_checks_and_legacy_duplicate_summary(pickup_client):
    client, sessions, data = pickup_client
    auth = headers(data["actor"]); payload = body(data, request_id=str(uuid4()))
    replies = await asyncio.gather(*[client.post("/api/dismissal/authorizations", headers=auth, json=payload) for _ in range(2)])
    assert all(reply.status_code == 200 for reply in replies), [reply.text for reply in replies]
    assert replies[0].json()["data"]["id"] == replies[1].json()["data"]["id"]
    duplicate = await client.post("/api/dismissal/authorizations", headers=auth, json={**payload, "request_id": str(uuid4())})
    assert duplicate.status_code == 409
    future = await client.post("/api/dismissal/authorizations", headers=auth, json=body(data, valid_from=str(school_today() + timedelta(days=2)), valid_until=None))
    assert future.status_code == 200, future.text
    async with sessions() as db:
        legacy = PickupAuthorization(student_id=data["children"][0].id, authorized_person_name="Legacy duplicate",
            authorized_person_id="TEST-DOC-001", valid_from=school_today())
        db.add(legacy); await db.commit()
    summary = await client.get("/api/dismissal/summary", headers=auth)
    assert summary.status_code == 200 and summary.json()["data"]["duplicate_identity_groups"] == 1, summary.text
    assert summary.json()["data"]["total_authorizations"] == 3
    records = await client.get("/api/dismissal/authorizations", headers=auth)
    assert {row["effective_status"] for row in records.json()["data"]} == {"ACTIVE", "FUTURE"}
    async with sessions() as db:
        assert (await db.execute(select(func.count(PickupAuthorization.id)))).scalar() == 3


async def test_pickup_desk_options_scope_read_only_and_inactive_student(pickup_client):
    client, sessions, data = pickup_client
    auth = headers(data["actor"])
    choices = await client.get("/api/dismissal/options", headers=headers(data["reader"]))
    assert choices.status_code == 200, choices.text
    assert str(data["stranger"].id) not in {row["id"] for row in choices.json()["data"]["students"]}
    assert (await client.post("/api/dismissal/authorizations", headers=headers(data["reader"]), json=body(data))).status_code == 403
    forbidden = await client.post("/api/dismissal/authorizations", headers=auth, json=body(data, student_id=str(data["stranger"].id)))
    assert forbidden.status_code in {403, 404}
    assert (await client.post("/api/dismissal/authorizations", headers=auth, json=body(data))).status_code == 200
    async with sessions() as db:
        child = await db.get(Student, data["children"][0].id); child.status = StudentStatus.PASSIVE
        await db.commit()
    denied = await client.post("/api/dismissal/verify-pickup", headers=auth,
        json={"student_id": str(data["children"][0].id), "pickup_person_id": "TEST-DOC-001", "request_id": str(uuid4())})
    assert denied.status_code == 409, denied.text
    summary = await client.get("/api/dismissal/summary", headers=auth)
    assert summary.json()["data"]["valid_authorizations"] == 0 and summary.json()["data"]["total_pickups"] == 0
    async with sessions() as db:
        assert (await db.execute(select(func.count(PickupLog.id)))).scalar() == 0


async def test_pickup_authorization_request_uuid_collision_between_students_is_conflict(pickup_client):
    client, _, data = pickup_client
    auth = headers(data["actor"]); shared = str(uuid4())
    replies = await asyncio.gather(*[client.post("/api/dismissal/authorizations", headers=auth,
        json=body(data, student_id=str(child.id), request_id=shared)) for child in data["children"]])
    assert sorted(reply.status_code for reply in replies) == [200, 409], [reply.text for reply in replies]
