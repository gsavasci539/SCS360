"""Explicit native review notes persist only for authorized institution writers."""
from uuid import uuid4

from sqlalchemy import func, select
from test_material_files import materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401

from app.core.security import create_access_token
from app.infrastructure.models.models import NotificationJob, Payment, Permission, Role, User


async def actor(sessions, organization_id, write):
    async with sessions() as db:
        codes = ["user.read"] + (["user.write"] if write else [])
        existing = {row.code: row for row in (await db.execute(select(Permission))).scalars()}
        role = Role(name="Review acceptance", slug="review_" + uuid4().hex, organization_id=organization_id,
            permissions=[existing[code] if code in existing else Permission(code=code, name=code, module="users") for code in codes])
        user = User(email=f"{uuid4().hex}@example.com", password_hash="unused",
            first_name="Recorded", last_name="Staff", organization_id=organization_id, roles=[role])
        db.add(user)
        await db.commit()
        return str(user.id), {"Authorization": "Bearer " + create_access_token(user.id)}


async def test_review_note_requires_writer_scope_and_is_read_back_verbatim(materials_client):
    client, sessions, data = materials_client
    staff_id, reader = await actor(sessions, data["org"].id, False)
    _, writer = await actor(sessions, data["org"].id, True)
    _, foreign = await actor(sessions, data["stranger"].organization_id, True)
    created = await client.post("/api/staff/leave-requests", headers=reader, json={
        "staff_id": staff_id, "staff_name": "Ignored", "leave_type": "Annual",
        "start_date": "2027-01-01", "end_date": "2027-01-03", "days_count": 3, "reason": "Recorded reason"})
    assert created.status_code == 200, created.text
    saved = created.json()["data"]
    path = f'/api/staff/leave-requests/{saved["id"]}/review'
    body = {"status": "REJECTED", "admin_comment": "Gerekçeli değerlendirme\nİkinci satır."}
    assert (await client.put(path, headers=reader, json=body)).status_code == 403
    assert (await client.put(path, headers=foreign, json=body)).status_code == 404
    unchanged = (await client.get("/api/staff/leave-requests", headers=reader)).json()["data"]
    assert unchanged == [saved]
    response = await client.put(path, headers=writer, json=body)
    assert response.status_code == 200, response.text
    reviewed = response.json()["data"]
    assert reviewed["admin_comment"] == body["admin_comment"] and reviewed["status"] == "REJECTED"
    assert (await client.get("/api/staff/leave-requests", headers=reader)).json()["data"] == [reviewed]
    async with sessions() as db:
        for model in (NotificationJob, Payment):
            assert (await db.execute(select(func.count()).select_from(model))).scalar_one() == 0
