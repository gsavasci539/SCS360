import asyncio
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import select
from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.core.dates import school_today
from app.domain.entities.pickup import PickupAuthorization, PickupLog
from app.infrastructure.models.models import Permission, Role, User


async def test_pickup_checks_identity_actor_scope_dates_and_retry_without_duplicate_log(materials_client):
    client, sessions, data = materials_client
    async with sessions() as db:
        actor = User(email="pickup@acceptance.invalid", password_hash="unused", organization_id=data["org"].id,
            first_name="Pickup", last_name="Officer", branches=[data["branch"]],
            roles=[Role(name="Pickup desk", slug="security", organization_id=data["org"].id,
                permissions=[Permission(code=code, name=code, module="dismissal") for code in ("dismissal.read", "dismissal.write")])])
        db.add(actor); await db.commit()
    auth = headers(actor)
    child = str(data["children"][0].id)
    body = {"student_id": child, "authorized_person_name": "Authorized Adult", "authorized_person_id": "TEST-ID-1", "valid_from": str(school_today()), "valid_until": str(school_today() + timedelta(days=1))}
    created = await client.post("/api/dismissal/authorizations", headers=auth, json=body)
    assert created.status_code == 200, created.text
    identifier = created.json()["data"]["id"]
    rows = (await client.get("/api/dismissal/authorizations", headers=auth)).json()["data"]
    assert rows[0]["created_by"] == str(actor.id)
    spoof = await client.post("/api/dismissal/verify-pickup", headers=auth, json={"student_id": child, "pickup_person_name": "Authorized Adult", "pickup_person_id": "WRONG-ID"})
    assert spoof.status_code == 200 and spoof.json()["data"]["authorized"] is False, spoof.text
    payload = {"student_id": child, "pickup_person_name": "Client cannot change registered name", "pickup_person_id": "TEST-ID-1", "request_id": str(uuid4()), "verified_by": str(data["teacher"].id)}
    replies = await asyncio.gather(*[client.post("/api/dismissal/verify-pickup", headers=auth, json=payload) for _ in range(2)])
    assert all(response.status_code == 200 for response in replies), [response.text for response in replies]
    assert replies[0].json()["data"]["pickup_log_id"] == replies[1].json()["data"]["pickup_log_id"]
    assert replies[0].json()["data"]["pickup_time"] == replies[1].json()["data"]["pickup_time"]
    async with sessions() as db:
        logs = (await db.execute(select(PickupLog))).scalars().all()
        assert len(logs) == 1 and logs[0].verified_by == actor.id and logs[0].pickup_person_name == "Authorized Adult"
    bounded = await client.get("/api/dismissal/logs", headers=auth, params={"start_date": str(school_today()), "end_date": str(school_today())})
    assert bounded.status_code == 200 and len(bounded.json()["data"]) == 1, bounded.text
    denied = await client.post("/api/dismissal/authorizations", headers=auth, json={**body, "student_id": str(data["stranger"].id)})
    assert denied.status_code in {403, 404}, denied.text
    assert (await client.delete("/api/dismissal/authorizations/" + identifier, headers=auth)).status_code == 200
    revoked = await client.post("/api/dismissal/verify-pickup", headers=auth, json={**payload, "request_id": str(uuid4())})
    assert revoked.status_code == 200 and revoked.json()["data"]["authorized"] is False
    invalid = await client.post("/api/dismissal/authorizations", headers=auth, json={**body, "valid_until": str(school_today() - timedelta(days=1))})
    assert invalid.status_code == 422
