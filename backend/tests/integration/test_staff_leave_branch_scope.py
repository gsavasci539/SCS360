from uuid import UUID, uuid4

from sqlalchemy import func, select
from test_material_files import materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from test_staff_review_comment import actor

from app.infrastructure.models.models import Branch, OperationalRecord, UserBranch


async def test_staff_leave_replay_and_review_respect_branch_assignments(materials_client):
    client, sessions, data = materials_client
    org_id = data["org"].id
    reader_id, reader = await actor(sessions, org_id, False)
    writer_id, writer = await actor(sessions, org_id, True)
    remote_id, remote = await actor(sessions, org_id, False)
    async with sessions() as db:
        other = Branch(name="Other branch", organization_id=org_id)
        db.add(other)
        await db.flush()
        db.add_all([
            UserBranch(user_id=UUID(reader_id), branch_id=data["branch"].id),
            UserBranch(user_id=UUID(writer_id), branch_id=data["branch"].id),
            UserBranch(user_id=UUID(remote_id), branch_id=other.id),
        ])
        await db.commit()

    path = "/api/staff/leave-requests"
    payload = dict(staff_id=reader_id, staff_name="Ignored", leave_type="Annual",
        start_date="2027-01-01", end_date="2027-01-03", days_count=99, reason="Same branch",
        request_id=str(uuid4()))
    created = await client.post(path, headers=reader, json=payload)
    assert created.status_code == 200, created.text
    own = created.json()["data"]
    assert own["id"] == payload["request_id"] and own["days_count"] == 3
    replay = await client.post(path, headers=reader, json=payload)
    assert replay.status_code == 200 and replay.json()["data"] == own
    assert (await client.post(path, headers=reader, json={**payload, "reason": "Different"})).status_code == 409

    remote_payload = {**payload, "staff_id": remote_id, "request_id": str(uuid4())}
    assert (await client.post(path, headers=writer, json=remote_payload)).status_code == 404
    created = await client.post(path, headers=remote, json=remote_payload)
    assert created.status_code == 200, created.text
    assert (await client.get(path, headers=writer)).json()["data"] == [own]
    assert (await client.get(path, headers=reader)).json()["data"] == [own]
    decision = {"status": "APPROVED", "admin_comment": "Plan doğrulandı."}
    assert (await client.put(f'{path}/{remote_payload["request_id"]}/review', headers=writer, json=decision)).status_code == 404
    reviewed = await client.put(f'{path}/{own["id"]}/review', headers=writer, json=decision)
    assert reviewed.status_code == 200 and reviewed.json()["data"]["admin_comment"] == decision["admin_comment"]
    assert (await client.get(path, headers=reader)).json()["data"] == [reviewed.json()["data"]]
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(OperationalRecord)) == 2
