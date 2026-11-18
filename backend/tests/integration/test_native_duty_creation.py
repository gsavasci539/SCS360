from uuid import UUID, uuid4

from sqlalchemy import func, select
from test_material_files import materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from test_staff_review_comment import actor

from app.infrastructure.models.models import Branch, NotificationJob, OperationalRecord, Payment, UserBranch


async def test_duty_options_and_persistence_follow_teacher_branch_and_writer_scope(materials_client):
    client, sessions, data = materials_client
    org, branch, teacher = data["org"], data["branch"], data["teacher"]
    writer_id, writer = await actor(sessions, org.id, True)
    _, reader = await actor(sessions, org.id, False)
    async with sessions() as db:
        other = Branch(organization_id=org.id, name="Other branch")
        db.add(other)
        await db.flush()
        other_id = str(other.id)
        db.add_all([UserBranch(user_id=UUID(writer_id), branch_id=branch.id),
                    UserBranch(user_id=teacher.id, branch_id=branch.id)])
        await db.commit()
    path = "/api/staff/duty-rosters"
    options = path + "/options"
    result = await client.get(options, headers=writer)
    assert result.status_code == 200, result.text
    assert result.json()["data"]["items"] == [{"id": str(branch.id), "name": branch.name}]
    result = await client.get(options, params={"branch_id": str(branch.id)}, headers=writer)
    assert result.status_code == 200, result.text
    assert result.json()["data"]["items"] == [{"id": str(teacher.id), "name": "Teacher Test"}]
    assert (await client.get(options, params={"branch_id": other_id}, headers=writer)).status_code == 404
    assert (await client.get(options, params={"branch_id": str(data["other_branch"].id)}, headers=writer)).status_code == 404
    assert (await client.get(options, headers=reader)).status_code == 403

    key = str(uuid4())
    payload = dict(branch_id=str(branch.id), teacher_id=str(teacher.id), teacher_name="Ignored",
        day_of_week="MONDAY", duty_location="GARDEN", start_time="08:00", end_time="15:30", request_id=key)
    assert (await client.post(path, headers=reader, json=payload)).status_code == 403
    assert (await client.post(path, headers=writer, json={**payload, "branch_id": other_id})).status_code == 404
    assert (await client.post(path, headers=writer, json={**payload, "teacher_id": str(data["user"].id)})).status_code == 422
    assert (await client.post(path, headers=writer, json={**payload, "end_time": "07:30"})).status_code == 422
    response = await client.post(path, headers=writer, json=payload)
    assert response.status_code == 200, response.text
    saved = response.json()["data"]
    assert saved["id"] == key and saved["teacher_name"] == "Teacher Test" and saved["status"] == "ACTIVE"
    replay = await client.post(path, headers=writer, json=payload)
    assert replay.status_code == 200 and replay.json()["data"] == saved
    assert (await client.post(path, headers=writer, json={**payload, "end_time": "16:00"})).status_code == 409
    listed = await client.get(path, params={"branch_id": str(branch.id)}, headers=writer)
    assert listed.status_code == 200 and listed.json()["data"] == [saved]
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(OperationalRecord)) == 1
        for model in (NotificationJob, Payment):
            assert await db.scalar(select(func.count()).select_from(model)) == 0
