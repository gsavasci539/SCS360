"""Canonical staff payloads used by the Kotlin native client persist on the API."""
from uuid import uuid4

from sqlalchemy import func, select
from test_material_files import materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.core.security import create_access_token
from app.infrastructure.models.models import NotificationJob, Payment, Permission, Role, User


async def test_staff_leave_create_review_and_readback(materials_client):
    client, sessions, data = materials_client
    async with sessions() as db:
        role = Role(name="Staff acceptance", slug="staff_" + uuid4().hex,
            organization_id=data["org"].id,
            permissions=[Permission(code=code, name=code, module="users") for code in ("user.read", "user.write")])
        user = User(email=f"{uuid4().hex}@example.com", password_hash="unused",
            first_name="Server", last_name="Actor", organization_id=data["org"].id, roles=[role])
        db.add(user)
        await db.commit()
        auth = {"Authorization": "Bearer " + create_access_token(user.id)}
        user_id = str(user.id)
    payload = dict(staff_id=user_id, staff_name="Ignored display value", leave_type="Annual",
        start_date="2027-01-01", end_date="2027-01-03", days_count=99, reason="Recorded reason")
    response = await client.post("/api/staff/leave-requests", headers=auth, json=payload)
    assert response.status_code == 200, response.text
    saved = response.json()["data"]
    assert saved["staff_name"] == "Server Actor" and saved["days_count"] == 3 and saved["status"] == "PENDING"
    listing = (await client.get("/api/staff/leave-requests", headers=auth)).json()["data"]
    assert saved in listing
    response = await client.put(f'/api/staff/leave-requests/{saved["id"]}/review', headers=auth,
        json={"status": "APPROVED", "admin_comment": ""})
    assert response.status_code == 200, response.text
    approved = response.json()["data"]
    assert approved["status"] == "APPROVED" and approved["admin_comment"] == ""
    assert approved in (await client.get("/api/staff/leave-requests", headers=auth)).json()["data"]
    assert (await client.get("/api/staff/duty-rosters", headers=auth)).json()["data"] == []
    async with sessions() as db:
        for model in (NotificationJob, Payment):
            assert (await db.execute(select(func.count()).select_from(model))).scalar_one() == 0
